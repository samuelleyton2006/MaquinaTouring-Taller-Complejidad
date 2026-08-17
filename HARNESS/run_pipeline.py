import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OSC_DIR = BASE_DIR / "OSCILADOR"
MULT_DIR = BASE_DIR / "MULTIPLICADOR"
FILTRO_DIR = BASE_DIR / "FILTRO"


def correr_script(carpeta: Path, script: str) -> str:
    #Ejecuta un script de una TM en su propia carpeta y lee su salida.txt
    resultado = subprocess.run(
        [sys.executable, script],
        cwd=carpeta,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        print(resultado.stdout)
        print(resultado.stderr)
        raise RuntimeError(f"Fallo al ejecutar {script} en {carpeta}")
    return (carpeta / "salida.txt").read_text().strip()


def escribir_senal(path: Path, muestras) -> None:
    path.write_text("#".join(muestras) + "#")


def parsear_senal(cinta: str):
    return [m for m in cinta.split("#") if m]


def bits_a_entero(bits: str) -> int:
    valor = int(bits, 2)
    if bits[0] == '1':
        valor -= (1 << len(bits))
    return valor


def run_pipeline(x_muestras):
    N = len(x_muestras)
    if N % 4 != 0:
        raise ValueError("El oscilador requiere N multiplo de 4")
    if N % 2 != 0:
        raise ValueError("El filtro requiere N par")

    #Etapa 1: generar cos(t) — primera instancia (nodo 1)
    cos1 = parsear_senal(correr_script(OSC_DIR, "OSCILADORUNO.py"))

    #Etapa 2: x(t) * cos(t) — primera multiplicación (nodo 2)
    escribir_senal(MULT_DIR / "entrada_x.txt", x_muestras)
    escribir_senal(MULT_DIR / "entrada_cos.txt", cos1)
    mod1 = parsear_senal(correr_script(MULT_DIR, "MULTIPLICADORUNO.py"))

    #Etapa 3: generar cos(t) — segunda instancia (nodo 4)
    cos2 = parsear_senal(correr_script(OSC_DIR, "OSCILADORUNO.py"))

    #Etapa 4: x(t)*cos(t) * cos(t) = x(t)*cos^2(t) — segunda multiplicación (nodo 3)
    escribir_senal(MULT_DIR / "entrada_x.txt", mod1)
    escribir_senal(MULT_DIR / "entrada_cos.txt", cos2)
    mod2 = parsear_senal(correr_script(MULT_DIR, "MULTIPLICADORUNO.py"))

    #Etapa 5: filtro pasabajos (nodo 5)
    escribir_senal(FILTRO_DIR / "index.txt", mod2)
    filtrado = parsear_senal(correr_script(FILTRO_DIR, "FILTROUNO.py"))

    return {
        "x(t)": x_muestras,
        "cos(t) [osc 1]": cos1,
        "x(t)*cos(t)": mod1,
        "cos(t) [osc 2]": cos2,
        "x(t)*cos^2(t)": mod2,
        "salida filtrada": filtrado,
    }


if __name__ == "__main__":
    x_ejemplo = ["00000001", "11111111", "11111111", "00000001"]  #x(t) = [1,-1,-1,1]

    resultado = run_pipeline(x_ejemplo)

    print("Pipeline completo (valores decimales) \n")
    for etapa, muestras in resultado.items():
        valores = [bits_a_entero(m) for m in muestras]
        print(f"{etapa:20s}: {valores}")

    print("\nVerificación")
    x_dec = [bits_a_entero(m) for m in x_ejemplo]
    salida_dec = [bits_a_entero(m) for m in resultado["salida filtrada"]]

    #El filtro promedia pares no solapados: la salida tiene N/2 muestras.
    #Cada muestra de salida corresponde al promedio de x(t) en ese par de
    #instantes, escalado por el efecto de cos^2 (promedio ~0.5 en el ciclo).
    print("El filtro reduce N muestras a N/2 (ventana no solapada).")
    print(f"x(t) original ({len(x_dec)} muestras): {x_dec}")
    print(f"Salida filtrada ({len(salida_dec)} muestras): {salida_dec}")
    print("Compara cada muestra de salida contra el promedio del par de x(t) correspondiente / 2.")
    for i, val in enumerate(salida_dec):
        par = x_dec[2 * i], x_dec[2 * i + 1]
        promedio_esperado = sum(par) / 2 / 2  #Promedio del par, atenuado por el factor 1/2 de la demodulación
        print(f"  salida[{i}]={val}   par x(t)={par}   referencia aproximada={promedio_esperado}")
