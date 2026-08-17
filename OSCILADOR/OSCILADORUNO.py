"""
TM-Oscilador  (nodos 1 y 4 del diagrama)
=========================================
Maquina de Turing DETERMINISTA de UNA cinta, formalmente:

    M = (Q, Sigma, Gamma, delta, q0, B, F)

- Q      : conjunto finito de estados (ver TRANSICIONES abajo)
- Sigma  : alfabeto de entrada  {'1'}                (el contador N en unario)
- Gamma  : alfabeto de cinta    {'0','1','X','$','#','B'}
- delta  : funcion de transicion parcial, IMPLEMENTADA como diccionario:
               (estado, simbolo_leido) -> (nuevo_estado, simbolo_escrito, movimiento)
           Cada entrada de ese diccionario es literalmente una "tarjeta":
           el programa NO decide con ifs sobre el contenido semantico de la señal,
           solo hace tape.get(head) -> busca la tarjeta -> aplica -> avanza.
- q0     : ('VOLVER_FRONTERA', 0)
- B      : 'B' (blanco, no ocupa memoria en el dict)
- F      : {'q_halt'}

Que hace la maquina
--------------------
Recibe SOLO un numero N (multiplo de 4, igual al numero de lineas de input.txt).
No lee ninguna senal. Escribe en su propia cinta N muestras de 8 bits
(complemento a 2) que aproximan cos(t) con un ciclo de 4 valores:

    +1 -> 00000001
     0 -> 00000000
    -1 -> 11111111
     0 -> 00000000

repetido N/4 veces, separadas por '#'.

Layout de la cinta ANTES de correr
-----------------------------------
posiciones 0..N-1  : 'N unos'  -> contador en UNARIO (cuantas muestras faltan)
posicion  N        : '$'       -> frontera fija entre zona-contador y zona-salida
posicion  N+1 ...   : blanco    -> aqui se va escribiendo cos(t)

Por que el cabezal puede "ir y volver" sin perder el lugar
-------------------------------------------------------------
Es la tecnica clasica de TM de una cinta: en vez de "recordar" una posicion
en una variable, la maquina vuelve a ESCANEAR desde un punto de referencia
fijo ('$' o el primer blanco) hasta encontrar lo que busca. Esto es lo que
hacen los estados VOLVER_FRONTERA / IR_A_CONTADOR / BUSCAR_TICK.
"""

from typing import Dict, Tuple

BLANK = 'B'
# ciclo de 4 valores de cos(t), 8 bits, complemento a 2
PATTERNS = ["00000001", "00000000", "11111111", "00000000"]


class TMOscilador:
    def __init__(self, N: int):
        if N <= 0 or N % 4 != 0:
            raise ValueError("N debe ser multiplo positivo de 4")
        self.N = N
        self.tape: Dict[int, str] = {}
        self.head: int = 0
        # q0 = BUSCAR_TICK(3): consume el primer tick de una vez (equivale a
        # decir "el proximo patron a escribir sera el 0", porque (3+1)%4=0).
        # Esto evita el error de "escribir un bloque de mas" (off-by-one).
        self.state = ('BUSCAR_TICK', 3)
        self.trace = []          # aqui se guarda cada "tarjeta" ejecutada
        self.step_count = 0
        self.halted = False
        self._construir_cinta_inicial()
        self._construir_tabla_transiciones()

    # ---------- primitivas de cinta (dict), igual que en el PDF ----------
    def leer(self, pos=None) -> str:
        if pos is None:
            pos = self.head
        return self.tape.get(pos, BLANK)

    def escribir(self, pos, simbolo) -> None:
        if simbolo == BLANK:
            self.tape.pop(pos, None)   # blanco = no ocupar memoria
        else:
            self.tape[pos] = simbolo

    def mover_derecha(self):
        self.head += 1

    def mover_izquierda(self):
        self.head -= 1

    # ---------- cinta inicial ----------
    def _construir_cinta_inicial(self):
        for i in range(self.N):
            self.tape[i] = '1'          # contador unario
        self.tape[self.N] = '$'         # frontera
        self.head = 0

    # ---------- tabla de transiciones delta ----------
    def _construir_tabla_transiciones(self):
        """
        Se GENERA con un bucle porque son 4 patrones x 8 bits, pero cada
        entrada resultante es una tarjeta atomica real:
            (estado, simbolo_leido) -> (estado_nuevo, simbolo_escrito, movimiento)
        Esto no reemplaza a la maquina de estados: esto ES la maquina de
        estados, solo que la tabla (finita) se construye con Python en vez
        de escribirla a mano 47 veces.
        """
        d: Dict[Tuple, Tuple] = {}

        for p in range(4):
            patron = PATTERNS[p]
            siguiente_p = (p + 1) % 4

            # --- escribir bit a bit el patron p ---
            for i in range(8):
                estado = ('WRITE', p, i)
                bit = patron[i]
                if i < 7:
                    siguiente_estado = ('WRITE', p, i + 1)
                else:
                    siguiente_estado = ('WRITE_HASH', p)
                # sin importar que haya en la celda (deberia ser blanco), se escribe el bit
                for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                    d[(estado, simbolo_leido)] = (siguiente_estado, bit, 'R')

            # --- escribir el separador '#' al final del bloque ---
            estado_hash = ('WRITE_HASH', p)
            for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                d[(estado_hash, simbolo_leido)] = (('IR_A_CONTADOR', p), '#', 'R')

            # --- volver hacia la izquierda cruzando la salida ya escrita ---
            estado_ir = ('IR_A_CONTADOR', p)
            for simbolo_leido in ('0', '1', '#', BLANK):
                d[(estado_ir, simbolo_leido)] = (estado_ir, simbolo_leido, 'L')  # no toca, sigue
                # (BLANK aparece la primera vez: el cabezal entra a este estado
                #  parado justo en la celda en blanco que sigue al '#' recien escrito)
            d[(estado_ir, '$')] = (('BUSCAR_TICK', p), '$', 'L')   # cruza la frontera

            # --- ya en la zona contador: busca un '1' activo para consumirlo ---
            estado_buscar = ('BUSCAR_TICK', p)
            d[(estado_buscar, 'X')] = (estado_buscar, 'X', 'L')          # salta ticks ya usados
            d[(estado_buscar, '1')] = (('VOLVER_FRONTERA', siguiente_p), 'X', 'R')  # consume 1 tick
            d[(estado_buscar, BLANK)] = ('q_halt', BLANK, 'N')            # contador agotado -> fin

            # --- volver a la derecha hasta el primer blanco (frontera de salida) ---
            estado_volver = ('VOLVER_FRONTERA', p)
            for simbolo_leido in ('1', 'X', '$', '0', '#'):
                d[(estado_volver, simbolo_leido)] = (estado_volver, simbolo_leido, 'R')
            d[(estado_volver, BLANK)] = (('WRITE', p, 0), BLANK, 'R')
            # ojo: al llegar al blanco, YA empieza a escribir ahi mismo (ver step())

        self.delta = d

    # ---------- ejecucion paso a paso (una tarjeta por llamada) ----------
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

        # Caso especial: el estado VOLVER_FRONTERA, al leer blanco, transiciona
        # a WRITE(p,0) pero la escritura del primer bit ocurre AHI MISMO,
        # sin moverse antes (por eso no usamos 'R' en esa tarjeta particular).
        if self.state[0] == 'VOLVER_FRONTERA' and simbolo == BLANK:
            p_actual = self.state[1]
            self.escribir(self.head, PATTERNS[p_actual][0])
            self.trace.append((self.step_count, self.state, simbolo, ('WRITE', p_actual, 1), PATTERNS[p_actual][0], 'R'))
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
        # 'N' = no mover (solo ocurre al llegar a q_halt)

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

    # ---------- leer la salida final ya ensamblada ----------
    def leer_salida(self) -> str:
        pos = self.N + 1
        out = []
        while (pos in self.tape):
            out.append(self.tape[pos])
            pos += 1
        return ''.join(out)


# --------------------------- demo / prueba ---------------------------
if __name__ == "__main__":
    N = 4   # igual al numero de lineas de input.txt -> x(t) = [1,-1,-1,1]
    m = TMOscilador(N)
    salida = m.correr()

    print(f"N = {N}")
    print(f"Pasos totales ejecutados: {m.step_count}")
    print(f"Estado final: {m.state}  (halted={m.halted})")
    print()
    print("Cinta de salida (cos(t) en bloques de 8 bits separados por #):")
    print(salida)
    print()
    print("Verificacion contra la muestra esperada del PDF:")
    esperado = "00000001#00000000#11111111#00000000#"
    print("esperado:", esperado)
    print("obtenido:", salida)
    print("COINCIDE:", salida == esperado)
    print()
    print("Primeras 15 tarjetas ejecutadas (estado, simbolo_leido -> estado_nuevo, simbolo_escrito, mov):")
    for t in m.trace[:15]:
        step_i, est, sim_l, est2, sim_e, mov = t
        print(f"  paso {step_i:3d}: {est}  lee '{sim_l}'  ->  {est2}, escribe '{sim_e}', mueve {mov}")