from typing import Dict, Tuple, List

BLANK = 'B'
ANCHO_BITS = 8

#Se lee la señal de entrada (x(t)*cos^2(t)) desde index.txt, igual que
#OSCILADORUNO.py y MULTIPLICADORUNO.py leen sus patrones desde archivo.
with open("index.txt", "r") as f:
    contenido = f.read().strip()
    MUESTRAS = [p for p in contenido.split("#") if p]


#Aritmetica en complemento a 2 (Python-side, table-build time) 
def bits_a_entero(bits: str) -> int:
    valor = int(bits, 2)
    if bits[0] == '1':
        valor -= (1 << len(bits))
    return valor


def entero_a_bits(valor: int, ancho: int = ANCHO_BITS) -> str:
    return format(valor & ((1 << ancho) - 1), '0{}b'.format(ancho))


VENTANA = 4  #Coincide con el ciclo de 4 valores del oscilador (un periodo de cos(t))
DESPLAZAMIENTO = 2  #Log2(VENTANA): dividir entre 4 = shift right 2


def promediar_grupo(bits_grupo: List[str]) -> str:

    #(suma de VENTANA muestras) >> DESPLAZAMIENTO en complemento a 2, truncado a ANCHO_BITS (overflow = wrap, comportamiento estandar de aritmetica de ancho fijo)
    suma = sum(bits_a_entero(b) for b in bits_grupo)
    suma_wrapped = ((suma + (1 << (ANCHO_BITS - 1))) % (1 << ANCHO_BITS)) - (1 << (ANCHO_BITS - 1))
    desplazado = suma_wrapped >> DESPLAZAMIENTO  #Shift aritmetico: preserva signo
    return entero_a_bits(desplazado)


def construir_resultados(muestras: List[str]) -> List[str]:
    if len(muestras) % VENTANA != 0:
        raise ValueError(f"El filtro requiere que el numero de muestras sea múltiplo de {VENTANA} (ventana sin solape)")
    resultados = []
    for i in range(0, len(muestras), VENTANA):
        resultados.append(promediar_grupo(muestras[i:i + VENTANA]))
    return resultados


RESULTADOS = construir_resultados(MUESTRAS)


class TMFiltro:
    """
    Filtro pasabajos simplificado: media movil de pares no solapados (k=2).
    Estructura identica a TMOscilador (contador unario + bloques WRITE por
    tarjeta), generalizada a una lista de resultados de longitud variable
    en vez de un ciclo fijo de 4 patrones.

    Simplificacion declarada: un pasabajos ideal no es implementable en TM
    en un semestre. VENTANA=4 (potencia de 2, igual al ciclo del oscilador)
    permite que "dividir" sea un shift aritmetico en vez de division general,
    y asegura que cada promedio cubra un periodo completo de cos(t).
    """

    def __init__(self, N: int):
        if N <= 0 or N % VENTANA != 0:
            raise ValueError(f"N debe ser un entero positivo múltiplo de {VENTANA}")
        self.N = N
        self.num_salidas = N // VENTANA
        self.tape: Dict[int, str] = {}
        self.head: int = 0
        self.state = ('BUSCAR_TICK', self.num_salidas - 1)
        self.trace = []
        self.step_count = 0
        self.halted = False
        self._construir_cinta_inicial()
        self._construir_tabla_transiciones()

    #Primitivas de cinta (dict) 
    def leer(self, pos=None) -> str:
        if pos is None:
            pos = self.head
        return self.tape.get(pos, BLANK)

    def escribir(self, pos, simbolo) -> None:
        if simbolo == BLANK:
            self.tape.pop(pos, None)
        else:
            self.tape[pos] = simbolo

    def mover_derecha(self):
        self.head += 1

    def mover_izquierda(self):
        self.head -= 1

    #Cinta inicial 
    def _construir_cinta_inicial(self):
        #Zona contador: un tick por par de muestras a producir
        for i in range(self.num_salidas):
            self.tape[i] = '1'
        self.tape[self.num_salidas] = '$'  #Frontera
        self.head = 0

    #Tabla de transiciones delta 
    def _construir_tabla_transiciones(self):
        d: Dict[Tuple, Tuple] = {}
        L = self.num_salidas

        for p in range(L):
            patron = RESULTADOS[p]
            siguiente_p = (p + 1) % L if L > 1 else p

            #Escribir bit a bit el resultado p
            for i in range(ANCHO_BITS):
                estado = ('WRITE', p, i)
                bit = patron[i]
                if i < ANCHO_BITS - 1:
                    siguiente_estado = ('WRITE', p, i + 1)
                else:
                    siguiente_estado = ('WRITE_HASH', p)
                for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                    d[(estado, simbolo_leido)] = (siguiente_estado, bit, 'R')

            #Escribir el separador '#' al final del bloque
            estado_hash = ('WRITE_HASH', p)
            for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                d[(estado_hash, simbolo_leido)] = (('IR_A_CONTADOR', p), '#', 'R')

            #Volver a la izquierda cruzando la salida ya escrita
            estado_ir = ('IR_A_CONTADOR', p)
            for simbolo_leido in ('0', '1', '#', BLANK):
                d[(estado_ir, simbolo_leido)] = (estado_ir, simbolo_leido, 'L')
            d[(estado_ir, '$')] = (('BUSCAR_TICK', p), '$', 'L')

            #Zona contador: consumir un '1' activo
            estado_buscar = ('BUSCAR_TICK', p)
            d[(estado_buscar, 'X')] = (estado_buscar, 'X', 'L')
            d[(estado_buscar, '1')] = (('VOLVER_FRONTERA', siguiente_p), 'X', 'R')
            d[(estado_buscar, BLANK)] = ('q_halt', BLANK, 'N')

            #Volver a la derecha hasta el primer blanco disponible
            estado_volver = ('VOLVER_FRONTERA', p)
            for simbolo_leido in ('1', 'X', '$', '0', '#'):
                d[(estado_volver, simbolo_leido)] = (estado_volver, simbolo_leido, 'R')
            d[(estado_volver, BLANK)] = (('WRITE', p, 0), BLANK, 'R')

        self.delta = d

    #Ejecución paso a paso 
    def step(self):
        if self.halted:
            return False

        simbolo = self.leer()
        tarjeta = self.delta.get((self.state, simbolo))

        if tarjeta is None:
            raise RuntimeError(
                f"No hay transición definida para estado={self.state}, simbolo='{simbolo}'"
            )

        nuevo_estado, simbolo_a_escribir, movimiento = tarjeta

        if self.state[0] == 'VOLVER_FRONTERA' and simbolo == BLANK:
            p_actual = self.state[1]
            self.escribir(self.head, RESULTADOS[p_actual][0])
            self.trace.append((self.step_count, self.state, simbolo, ('WRITE', p_actual, 1), RESULTADOS[p_actual][0], 'R'))
            self.state = ('WRITE', p_actual, 1)
            self.mover_derecha()
            self.step_count += 1
            return True

        self.escribir(self.head, simbolo_a_escribir)
        self.trace.append((self.step_count, self.state, simbolo, nuevo_estado, simbolo_a_escribir, movimiento))

        if movimiento == 'R':
            self.mover_derecha()
        elif movimiento == 'L':
            self.mover_izquierda()

        self.state = nuevo_estado
        self.step_count += 1

        if self.state == 'q_halt':
            self.halted = True

        return True

    def correr(self, max_pasos=2_000_000):
        while not self.halted and self.step_count < max_pasos:
            self.step()
        if not self.halted:
            raise RuntimeError("La máquina no llego a q_halt (límite de pasos superado)")
        return self.leer_salida()

    #Leer el resultado de la salida 
    def leer_salida(self) -> str:
        pos = self.num_salidas + 1
        out = []
        while pos in self.tape:
            out.append(self.tape[pos])
            pos += 1
        return ''.join(out)


if __name__ == "__main__":
    N = len(MUESTRAS)  #Número de muestras leidas de index.txt
    m = TMFiltro(N)
    salida = m.correr()

    print(f"N (muestras de entrada) = {N}")
    print(f"Muestras de entrada (desde index.txt): {MUESTRAS}")
    print(f"Grupos de {VENTANA} promediados (suma>>{DESPLAZAMIENTO}): {RESULTADOS}")
    print(f"Pasos ejecutados: {m.step_count}")
    print(f"Cinta de salida: {salida}")
    print()
    print("Verificacion manual:")
    for i, r in enumerate(RESULTADOS):
        grupo = MUESTRAS[i * VENTANA:(i + 1) * VENTANA]
        valores = [bits_a_entero(g) for g in grupo]
        print(f"  grupo {i}: {valores} -> suma={sum(valores)} -> >>{DESPLAZAMIENTO} -> {r}({bits_a_entero(r)})")

    with open("salida.txt", "w") as f:
        f.write(salida)
