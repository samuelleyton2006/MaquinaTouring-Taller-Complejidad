"""
Prueba de cinta bidireccional infinita.

Objetivo: demostrar que la estructura de cinta usada en las 3 TM del
pipeline (dict {posición: símbolo}) soporta movimiento del cabezal en
AMBAS direcciones, incluyendo posiciones negativas, sin necesidad de
reservar memoria de antemano ni reindexar nada.

Esto se separa deliberadamente del pipeline de modulación porque ninguno
de los 3 algoritmos (oscilador, multiplicador, filtro) necesita moverse
a la izquierda del origen para su computo — la prueba de que la cinta
LO SOPORTA es independiente de si un algoritmo particular lo usa.

Se implementa como una TM real (estados + tabla de transiciones), no como
un script que solo llama a métodos de cinta directamente, para que siga
siendo una demostración formal y no un atajo.
"""

from typing import Dict, Tuple

BLANK = 'B'


class TMBidireccional:
    """
    TM mínima cuyo unico proposito es recorrer la cinta hacia la izquierda
    cruzando el origen (posición 0) hacia posiciones negativas, escribir
    ahí, y luego regresar hacia la derecha cruzando de nuevo hacia
    posiciones positivas.

    Cinta inicial: un marcador '1' en la posicion 0. El cabezal arranca
    ahí.

    Comportamiento:
      1. Desde el origen, se mueve 5 posiciones a la izquierda (-1..-5),
         escribiendo 'L' en cada una.
      2. Al llegar a -5, invierte dirección y se mueve 5 posiciones a la
         derecha, cruzando el origen, hasta +5, escribiendo 'R' en cada
         celda del camino de vuelta (sin pisar las 'L' ya escritas al ir,
         solo se pisa lo que estaba en blanco a la derecha del origen).
      3. Halt en +5.
    """

    def __init__(self, pasos_izquierda: int = 5, pasos_derecha: int = 5):
        self.pasos_izquierda = pasos_izquierda
        self.pasos_derecha = pasos_derecha
        self.tape: Dict[int, str] = {0: '1'}
        self.head: int = 0
        self.state = ('IR_IZQUIERDA', 0)
        self.trace = []
        self.step_count = 0
        self.halted = False
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

    def mover_izquierda(self):
        self.head -= 1

    def mover_derecha(self):
        self.head += 1

    #Tabla de transiciones
    def _construir_tabla_transiciones(self):
        d: Dict[Tuple, Tuple] = {}

        for i in range(self.pasos_izquierda):
            estado = ('IR_IZQUIERDA', i)
            siguiente = ('IR_IZQUIERDA', i + 1) if i < self.pasos_izquierda - 1 else ('IR_DERECHA', 0)
            for simbolo_leido in ('0', '1', 'L', 'R', BLANK):
                d[(estado, simbolo_leido)] = (siguiente, 'L', 'IZQ')

        for i in range(self.pasos_izquierda + self.pasos_derecha):
            estado = ('IR_DERECHA', i)
            if i < self.pasos_izquierda + self.pasos_derecha - 1:
                siguiente = ('IR_DERECHA', i + 1)
            else:
                siguiente = 'q_halt'
            for simbolo_leido in ('0', '1', 'L', 'R', BLANK):
                #No se pisa el marcador inicial en el origen ni las 'L' ya escritas
                if simbolo_leido in ('1', 'L'):
                    d[(estado, simbolo_leido)] = (siguiente, simbolo_leido, 'DER')
                else:
                    d[(estado, simbolo_leido)] = (siguiente, 'R', 'DER')

        self.delta = d

    #Ejecución
    def step(self):
        if self.halted:
            return False

        simbolo = self.leer()
        tarjeta = self.delta.get((self.state, simbolo))
        if tarjeta is None:
            raise RuntimeError(f"No hay transición para estado={self.state}, símbolo='{simbolo}'")

        nuevo_estado, simbolo_a_escribir, direccion = tarjeta
        self.escribir(self.head, simbolo_a_escribir)
        self.trace.append((self.step_count, self.head, self.state, simbolo, nuevo_estado, simbolo_a_escribir, direccion))

        if direccion == 'IZQ':
            self.mover_izquierda()
        elif direccion == 'DER':
            self.mover_derecha()

        self.state = nuevo_estado
        self.step_count += 1

        if self.state == 'q_halt':
            self.halted = True

        return True

    def correr(self, max_pasos=10_000):
        while not self.halted and self.step_count < max_pasos:
            self.step()
        if not self.halted:
            raise RuntimeError("La máquina no llego a q_halt")
        return self.tape


if __name__ == "__main__":
    m = TMBidireccional(pasos_izquierda=5, pasos_derecha=5)
    tape_final = m.correr()

    print(f"Pasos ejecutados: {m.step_count}")
    print(f"Posición final del cabezal: {m.head}")
    print()
    print("Contenido completo de la cinta (dict), incluyendo posiciones negativas:")
    for pos in sorted(tape_final.keys()):
        print(f"  posicion {pos:+d}: '{tape_final[pos]}'")
    print()

    negativas = [p for p in tape_final if p < 0]
    positivas = [p for p in tape_final if p > 0]
    print(f"Posiciones negativas escritas: {sorted(negativas)}")
    print(f"Posiciones positivas escritas: {sorted(positivas)}")
    print(f"CONFIRMA cinta bidireccional infinita: {len(negativas) > 0 and len(positivas) > 0}")
