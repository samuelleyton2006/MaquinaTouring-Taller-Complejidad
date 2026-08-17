from typing import Dict, Tuple

BLANK = 'B'

# Se lee el patron/coeficiente de multiplicacion desde index.txt
# Ejemplo contenido index.txt: 00000010#
with open("index.txt", "r") as f:
    contenido = f.read().strip()
    PATTERNS = [p for p in contenido.split("#") if p]


class TMMultiplicador:
    def __init__(self, N: int):
        if N <= 0:
            raise ValueError("N debe ser un entero positivo")
        self.N = N
        self.patron = PATTERNS[0]  # Coeficiente/Patron a multiplicar (e.g. 8 bits)
        self.longitud_patron = len(self.patron)
        self.tape: Dict[int, str] = {}
        self.head: int = 0
        self.state = ('BUSCAR_TICK', 0)
        self.trace = []
        self.step_count = 0
        self.halted = False
        self._construir_cinta_inicial()
        self._construir_tabla_transiciones()

    # ---------- Primitivas de cinta ----------
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

    # ---------- Cinta inicial ----------
    def _construir_cinta_inicial(self):
        # 1. Zona contador (N unos)
        for i in range(self.N):
            self.tape[i] = '1'
        self.tape[self.N] = '$'  # Frontera 1
        
        # 2. Zona escalar (se escribe el patron a multiplicar)
        offset = self.N + 1
        for i, char in enumerate(self.patron):
            self.tape[offset + i] = char
        
        # 3. Frontera 2 (delimita la entrada/patron de la salida)
        self.tape[offset + self.longitud_patron] = '$'
        self.head = 0

    # ---------- Tabla de transiciones delta ----------
    def _construir_tabla_transiciones(self):
        d: Dict[Tuple, Tuple] = {}
        L = self.longitud_patron

        # --- Escribir bit a bit el patron ---
        for i in range(L):
            estado = ('WRITE', 0, i)
            bit = self.patron[i]
            siguiente_estado = ('WRITE', 0, i + 1) if i < L - 1 else ('WRITE_HASH', 0)
            
            for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
                d[(estado, simbolo_leido)] = (siguiente_estado, bit, 'R')

        # --- Escribir el separador '#' al final de la muestra multiplicada ---
        estado_hash = ('WRITE_HASH', 0)
        for simbolo_leido in ('0', '1', '#', '$', 'X', BLANK):
            d[(estado_hash, simbolo_leido)] = (('IR_A_CONTADOR', 0), '#', 'R')

        # --- Volver a la izquierda cruzando la salida e ignorando el primer '$' ---
        estado_ir = ('IR_A_CONTADOR', 0)
        for simbolo_leido in ('0', '1', '#', BLANK):
            d[(estado_ir, simbolo_leido)] = (estado_ir, simbolo_leido, 'L')
        
        # Al cruzar el '$' de la frontera de salida, pasa a buscar la frontera del contador
        d[(estado_ir, '$')] = (('BUSCAR_FRONTERA_CONTADOR', 0), '$', 'L')

        estado_buscar_f1 = ('BUSCAR_FRONTERA_CONTADOR', 0)
        for simbolo_leido in ('0', '1', 'X'):
            d[(estado_buscar_f1, simbolo_leido)] = (estado_buscar_f1, simbolo_leido, 'L')
        d[(estado_buscar_f1, '$')] = (('BUSCAR_TICK', 0), '$', 'L')

        # --- Zona contador: consumir un '1' activo ---
        estado_buscar = ('BUSCAR_TICK', 0)
        d[(estado_buscar, 'X')] = (estado_buscar, 'X', 'L')
        d[(estado_buscar, '1')] = (('VOLVER_FRONTERA', 0), 'X', 'R')
        d[(estado_buscar, BLANK)] = ('q_halt', BLANK, 'N')

        # --- Volver a la derecha hasta el primer BLANK disponible en la salida ---
        estado_volver = ('VOLVER_FRONTERA', 0)
        for simbolo_leido in ('1', 'X', '$', '0', '#'):
            d[(estado_volver, simbolo_leido)] = (estado_volver, simbolo_leido, 'R')
        d[(estado_volver, BLANK)] = (('WRITE', 0, 0), BLANK, 'R')

        self.delta = d

    # ---------- Ejecución paso a paso ----------
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

        # Manejo de borde al posicionarse en el BLANK de salida
        if self.state[0] == 'VOLVER_FRONTERA' and simbolo == BLANK:
            self.escribir(self.head, self.patron[0])
            self.trace.append((self.step_count, self.state, simbolo, ('WRITE', 0, 1), self.patron[0], 'R'))
            self.state = ('WRITE', 0, 1)
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
            raise RuntimeError("La maquina no llego a q_halt")
        return self.leer_salida()

    # ---------- Leer el resultado de la salida ----------
    def leer_salida(self) -> str:
        # La salida empieza despues del segundo '$'
        pos = self.N + 1 + self.longitud_patron + 1
        out = []
        while pos in self.tape:
            out.append(self.tape[pos])
            pos += 1
        return ''.join(out)


# --------------------------- Prueba ---------------------------
if __name__ == "__main__":
    N = 4  # N muestras a multiplicar
    m = TMMultiplicador(N)
    salida = m.correr()

    print(f"N = {N}")
    print(f"Patrón a multiplicar (desde index.txt): {m.patron}")
    print(f"Pasos ejecutados: {m.step_count}")
    print(f"Resultado en la cinta de salida:\n{salida}")