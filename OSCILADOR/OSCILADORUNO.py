from typing import Dict, Tuple

BLANK = 'B'

with open("index.txt", "r") as f:
    contenido = f.read().strip()
    PATTERNS = [p for p in contenido.split("#") if p]


class TMOscilador:
    def __init__(self, N: int):
        if N <= 0 or N % 4 != 0:
            raise ValueError("N debe ser multiplo positivo de 4")
        self.N = N
        self.tape: Dict[int, str] = {}
        self.head: int = 0
        self.state = ('BUSCAR_TICK', 3)
        self.trace = []
        self.step_count = 0
        self.halted = False
        self._construir_cinta_inicial()
        self._construir_tabla_transiciones()

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

    def _construir_cinta_inicial(self):
        for i in range(self.N):
            self.tape[i] = '1'
        self.tape[self.N] = '$'
        self.head = 0

    def _construir_tabla_transiciones(self):
        d: Dict[Tuple, Tuple] = {}

        for p in range(4):
            patron = PATTERNS[p]
            siguiente_p = (p + 1) % 4

            for i in range(8):
                estado = ('WRITE', p, i)
                bit = patron[i]
                if i < 7:
                    siguiente_estado = ('WRITE', p, i + 1)
                else:
                    siguiente_estado = ('WRITE_HASH', p)
                for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                    d[(estado, simbolo_leido)] = (siguiente_estado, bit, 'R')

            estado_hash = ('WRITE_HASH', p)
            for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                d[(estado_hash, simbolo_leido)] = (('IR_A_CONTADOR', p), '#', 'R')

            estado_ir = ('IR_A_CONTADOR', p)
            for simbolo_leido in ('0', '1', '#', BLANK):
                d[(estado_ir, simbolo_leido)] = (estado_ir, simbolo_leido, 'L')
            d[(estado_ir, '$')] = (('BUSCAR_TICK', p), '$', 'L')

            estado_buscar = ('BUSCAR_TICK', p)
            d[(estado_buscar, 'X')] = (estado_buscar, 'X', 'L')
            d[(estado_buscar, '1')] = (('VOLVER_FRONTERA', siguiente_p), 'X', 'R')
            d[(estado_buscar, BLANK)] = ('q_halt', BLANK, 'N')

            estado_volver = ('VOLVER_FRONTERA', p)
            for simbolo_leido in ('1', 'X', '$', '0', '#'):
                d[(estado_volver, simbolo_leido)] = (estado_volver, simbolo_leido, 'R')
            d[(estado_volver, BLANK)] = (('WRITE', p, 0), BLANK, 'R')

        self.delta = d

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
        while (pos in self.tape):
            out.append(self.tape[pos])
            pos += 1
        return ''.join(out)


if __name__ == "__main__":
    N = 4
    m = TMOscilador(N)
    salida = m.correr()

    print(f"N = {N}")
    print(f"Pasos totales ejecutados: {m.step_count}")
    print(f"Cinta de salida: {salida}")

    #Se escribe la salida a archivo para que el harness pueda leerla
    with open("salida.txt", "w") as f:
        f.write(salida)
