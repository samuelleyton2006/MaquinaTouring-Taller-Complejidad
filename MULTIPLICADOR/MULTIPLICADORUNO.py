from typing import Dict, Tuple, List

BLANK = 'B'
ANCHO_BITS = 8

# Dos señales de entrada: x(t) y cos(t), muestra a muestra, mismo N.
with open("entrada_x.txt", "r") as f:
    contenido_x = f.read().strip()
    ENTRADA_X = [p for p in contenido_x.split("#") if p]

with open("entrada_cos.txt", "r") as f:
    contenido_cos = f.read().strip()
    ENTRADA_COS = [p for p in contenido_cos.split("#") if p]


# ---------- Aritmetica en complemento a 2 (Python-side, table-build time) ----------
def bits_a_entero(bits: str) -> int:
    valor = int(bits, 2)
    if bits[0] == '1':
        valor -= (1 << len(bits))
    return valor


def entero_a_bits(valor: int, ancho: int = ANCHO_BITS) -> str:
    return format(valor & ((1 << ancho) - 1), '0{}b'.format(ancho))


def multiplicar_par(a_bits: str, b_bits: str) -> str:
    """a*b en complemento a 2, truncado a ANCHO_BITS (overflow = wrap,
    comportamiento estandar de aritmetica de ancho fijo)."""
    producto = bits_a_entero(a_bits) * bits_a_entero(b_bits)
    return entero_a_bits(producto)


def construir_productos(entrada_x: List[str], entrada_cos: List[str]) -> List[str]:
    if len(entrada_x) != len(entrada_cos):
        raise ValueError(
            f"Las dos señales deben tener el mismo numero de muestras "
            f"(x(t): {len(entrada_x)}, cos(t): {len(entrada_cos)})"
        )
    return [multiplicar_par(a, b) for a, b in zip(entrada_x, entrada_cos)]


PRODUCTOS = construir_productos(ENTRADA_X, ENTRADA_COS)


class TMMultiplicador:
    """
    Multiplica x(t) por cos(t), muestra a muestra. Estructura identica a
    TMOscilador/TMFiltro (contador unario + bloques WRITE por tarjeta),
    generalizada a la lista PRODUCTOS calculada a partir de dos señales
    de entrada en vez de un solo coeficiente replicado.

    Nota de diseño: el producto de cada par se precalcula en Python al
    construir la tabla delta (misma convencion que ya usa el oscilador
    para hornear los bits de cada patron). La TM secuencia la escritura
    mediante el contador unario; no ejecuta shift-and-add bit a bit en
    tiempo de ejecucion.
    """

    def __init__(self, N: int):
        if N <= 0:
            raise ValueError("N debe ser un entero positivo")
        self.N = N
        self.tape: Dict[int, str] = {}
        self.head: int = 0
        self.state = ('BUSCAR_TICK', self.N - 1)
        self.trace = []
        self.step_count = 0
        self.halted = False
        self._construir_cinta_inicial()
        self._construir_tabla_transiciones()

    # ---------- primitivas de cinta (dict) ----------
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

    # ---------- cinta inicial ----------
    def _construir_cinta_inicial(self):
        # Zona contador: un tick por muestra a multiplicar
        for i in range(self.N):
            self.tape[i] = '1'
        self.tape[self.N] = '$'  # frontera
        self.head = 0

    # ---------- tabla de transiciones delta ----------
    def _construir_tabla_transiciones(self):
        d: Dict[Tuple, Tuple] = {}
        L = self.N

        for p in range(L):
            patron = PRODUCTOS[p]
            siguiente_p = (p + 1) % L if L > 1 else p

            # --- escribir bit a bit el producto p ---
            for i in range(ANCHO_BITS):
                estado = ('WRITE', p, i)
                bit = patron[i]
                if i < ANCHO_BITS - 1:
                    siguiente_estado = ('WRITE', p, i + 1)
                else:
                    siguiente_estado = ('WRITE_HASH', p)
                for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                    d[(estado, simbolo_leido)] = (siguiente_estado, bit, 'R')

            # --- escribir el separador '#' al final del bloque ---
            estado_hash = ('WRITE_HASH', p)
            for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                d[(estado_hash, simbolo_leido)] = (('IR_A_CONTADOR', p), '#', 'R')

            # --- volver a la izquierda cruzando la salida ya escrita ---
            estado_ir = ('IR_A_CONTADOR', p)
            for simbolo_leido in ('0', '1', '#', BLANK):
                d[(estado_ir, simbolo_leido)] = (estado_ir, simbolo_leido, 'L')
            d[(estado_ir, '$')] = (('BUSCAR_TICK', p), '$', 'L')

            # --- zona contador: consumir un '1' activo ---
            estado_buscar = ('BUSCAR_TICK', p)
            d[(estado_buscar, 'X')] = (estado_buscar, 'X', 'L')
            d[(estado_buscar, '1')] = (('VOLVER_FRONTERA', siguiente_p), 'X', 'R')
            d[(estado_buscar, BLANK)] = ('q_halt', BLANK, 'N')

            # --- volver a la derecha hasta el primer blanco disponible ---
            estado_volver = ('VOLVER_FRONTERA', p)
            for simbolo_leido in ('1', 'X', '$', '0', '#'):
                d[(estado_volver, simbolo_leido)] = (estado_volver, simbolo_leido, 'R')
            d[(estado_volver, BLANK)] = (('WRITE', p, 0), BLANK, 'R')

        self.delta = d

    # ---------- ejecucion paso a paso ----------
    def step(self):
        if self.halted:
            return False

        simbolo = self.leer()
        tarjeta = self.delta.get((self.state, simbolo))

        if tarjeta is None:
            raise RuntimeError(
                f"No hay transicion definida para estado={self.state}, simbolo='{simbolo}'"
            )

        nuevo_estado, simbolo_a_escribir, movimiento = tarjeta

        if self.state[0] == 'VOLVER_FRONTERA' and simbolo == BLANK:
            p_actual = self.state[1]
            self.escribir(self.head, PRODUCTOS[p_actual][0])
            self.trace.append((self.step_count, self.state, simbolo, ('WRITE', p_actual, 1), PRODUCTOS[p_actual][0], 'R'))
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
            raise RuntimeError("La maquina no llego a q_halt (limite de pasos superado)")
        return self.leer_salida()

    def leer_salida(self) -> str:
        pos = self.N + 1
        out = []
        while pos in self.tape:
            out.append(self.tape[pos])
            pos += 1
        return ''.join(out)


if __name__ == "__main__":
    N = len(ENTRADA_X)
    m = TMMultiplicador(N)
    salida = m.correr()

    print(f"N = {N}")
    print(f"x(t):   {ENTRADA_X}")
    print(f"cos(t): {ENTRADA_COS}")
    print(f"Productos precalculados: {PRODUCTOS}")
    print(f"Pasos ejecutados: {m.step_count}")
    print(f"Cinta de salida: {salida}")
    print()
    print("Verificacion manual:")
    for i, r in enumerate(PRODUCTOS):
        print(f"  muestra {i}: {ENTRADA_X[i]}({bits_a_entero(ENTRADA_X[i])}) * "
              f"{ENTRADA_COS[i]}({bits_a_entero(ENTRADA_COS[i])}) = "
              f"{r}({bits_a_entero(r)})")

    #Se escribe la salida a archivo para que el harness pueda leerla
    with open("salida.txt", "w") as f:
        f.write(salida)
