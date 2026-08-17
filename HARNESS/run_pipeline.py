import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OSC_DIR = BASE_DIR / "OSCILADOR"
MULT_DIR = BASE_DIR / "MULTIPLICADOR"
FILTRO_DIR = BASE_DIR / "FILTRO"


def correr_script(carpeta: Path, script: str, argumentos=None) -> str:
    #Ejecuta un script de una TM en su propia carpeta y lee su salida.txt.
    argumentos = argumentos or []
    resultado = subprocess.run(
        [sys.executable, script, *argumentos],
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
        raise ValueError("El oscilador y el filtro requieren N multiplo de 4")

    #Etapa 1: generar cos(t) — primera instancia (nodo 1)
    cos1 = parsear_senal(correr_script(OSC_DIR, "OSCILADORUNO.py", [str(N)]))

    #Etapa 2: x(t) * cos(t) — primera multiplicación (nodo 2)
    escribir_senal(MULT_DIR / "entrada_x.txt", x_muestras)
    escribir_senal(MULT_DIR / "entrada_cos.txt", cos1)
    mod1 = parsear_senal(correr_script(MULT_DIR, "MULTIPLICADORUNO.py"))

    #Etapa 3: generar cos(t) — segunda instancia (nodo 4)
    cos2 = parsear_senal(correr_script(OSC_DIR, "OSCILADORUNO.py", [str(N)]))

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
    #x(t) con amplitud mayor para que el filtro produzca salidas no triviales con amplitud 1 la división entera trunca a 0 y no demuestra nada)
    x_ejemplo = [
        "00000100", "00000100", "00000100", "11111100",  # [4,4,4,-4] -> promedio 3
        "11111100", "11111100", "11111100", "00000100",  # [-4,-4,-4,4] -> promedio -2
    ]

    resultado = run_pipeline(x_ejemplo)

    print("=== Pipeline completo (valores decimales) ===\n")
    for etapa, muestras in resultado.items():
        valores = [bits_a_entero(m) for m in muestras]
        print(f"{etapa:20s}: {valores}")

    print("\n=== Verificacion ===")
    x_dec = [bits_a_entero(m) for m in x_ejemplo]
    salida_dec = [bits_a_entero(m) for m in resultado["salida filtrada"]]

    #El filtro promedia grupos de 4 (un ciclo completo del oscilador): la
    #salida tiene N/4 muestras. La referencia correcta es el promedio
    #elemento-a-elemento de x(t)*cos^2(t) en esa ventana (NO x_promedio/2:
    #esa aproximación solo es válida si x es constante dentro de la ventana,
    #y con un oscilador discreto de 4 niveles la mitad de las muestras de
    #cos^2 son exactamente 0, asi que la variacion de x en esos instantes
    #queda fuera del promedio).
    VENTANA = 4
    mod2_dec = [bits_a_entero(m) for m in resultado["x(t)*cos^2(t)"]]
    print(f"El filtro reduce N={len(x_dec)} muestras a N/{VENTANA}={len(salida_dec)} (ventana = 1 ciclo del oscilador).")
    print(f"x(t) original: {x_dec}")
    print(f"Salida filtrada: {salida_dec}")
    print("Referencia correcta = promedio (entero, division hacia -inf) de x(t)*cos^2(t) en la ventana:")
    for i, val in enumerate(salida_dec):
        grupo_mod2 = mod2_dec[i * VENTANA:(i + 1) * VENTANA]
        referencia_entera = sum(grupo_mod2) // VENTANA  #Misma aritmetica que usa el filtro
        print(f"  salida[{i}]={val}   x(t)*cos^2(t) en ventana={grupo_mod2}   "
              f"suma={sum(grupo_mod2)}   referencia (suma//{VENTANA})={referencia_entera}   "
              f"COINCIDE={val == referencia_entera}")
