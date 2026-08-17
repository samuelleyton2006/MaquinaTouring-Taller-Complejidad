# Máquinas de Turing para procesamiento discreto de señales

Implementación de un pipeline de **Máquinas de Turing (TM)** para generar una señal cosenoidal discreta, multiplicarla muestra a muestra y aplicar un filtrado pasabajos simplificado mediante promedios sobre ventanas de un ciclo completo.

El proyecto usa una **cinta potencialmente infinita representada con un diccionario de Python (`dict[int, str]`)**, por lo que la estructura permite acceder tanto a posiciones positivas como negativas sin reservar una cinta de tamaño fijo.

## Objetivo

Construir y conectar varias máquinas de Turing que representen, de forma discreta, el siguiente procesamiento:

```text
                 ┌───────────────┐
                 │ TM Oscilador  │
                 │   cos(t)      │
                 └───────┬───────┘
                         │
                         ▼
x(t) ───────────────► [TM Multiplicador] ───► x(t)·cos(t)
                         │
                 cos(t)  │
                         ▼
                   [TM Multiplicador] ───► x(t)·cos²(t)
                         │
                         ▼
                      [TM Filtro] ──────► salida filtrada
```

El archivo `HARNESS/run_pipeline.py` automatiza las cinco ejecuciones necesarias del pipeline:

1. Generación de `cos(t)` con una instancia del oscilador.
2. Multiplicación `x(t) · cos(t)`.
3. Generación de una segunda copia de `cos(t)` con el oscilador.
4. Multiplicación `x(t) · cos(t) · cos(t) = x(t) · cos²(t)`.
5. Filtrado por ventanas de cuatro muestras.

## Estructura del proyecto

```text
MaquinaTouring-Taller-Complejidad/
├── DEMOS/
│   └── DEMO_CINTA_BIDIRECCIONAL.py
├── OSCILADOR/
│   ├── OSCILADORUNO.py
│   ├── index.txt
│   └── salida.txt
├── MULTIPLICADOR/
│   ├── MULTIPLICADORUNO.py
│   ├── entrada_x.txt
│   ├── entrada_cos.txt
│   └── salida.txt
├── FILTRO/
│   ├── FILTROUNO.py
│   ├── index.txt
│   └── salida.txt
├── HARNESS/
│   └── run_pipeline.py
└── README.md
```

## Requisitos

- Python 3.
- No se requieren librerías externas: el proyecto utiliza únicamente la biblioteca estándar de Python.

## Cómo ejecutar el proyecto completo

Desde la carpeta raíz del repositorio:

```bash
python3 HARNESS/run_pipeline.py
```

El `harness` ejecuta cada máquina desde su propia carpeta porque los programas leen y escriben archivos relativos como `index.txt`, `entrada_x.txt`, `entrada_cos.txt` y `salida.txt`.

Una ejecución correcta muestra, entre otros datos, una salida similar a:

```text
x(t)                : [4, 4, 4, -4, -4, -4, -4, 4]
cos(t) [osc 1]      : [1, 0, -1, 0, 1, 0, -1, 0]
x(t)*cos(t)        : [4, 0, -4, 0, -4, 0, 4, 0]
cos(t) [osc 2]      : [1, 0, -1, 0, 1, 0, -1, 0]
x(t)*cos^2(t)     : [4, 0, 4, 0, -4, 0, -4, 0]
salida filtrada    : [2, -2]
```

Además, el `harness` verifica que cada salida del filtro coincida con el promedio entero del bloque correspondiente de cuatro muestras.

## Representación de datos

Las señales se almacenan como bloques de bits de **8 bits en complemento a dos**, separados por `#`.

Ejemplo:

```text
00000100#00000100#00000100#11111100#
```

Representa:

```text
4, 4, 4, -4
```

La conversión corresponde a complemento a dos de ancho fijo. En las operaciones de multiplicación, los resultados se almacenan nuevamente en 8 bits; por tanto, valores que excedan el rango representable presentan el comportamiento de aritmética de ancho fijo (wrap-around).

## 1. TM Oscilador

Archivo:

```text
OSCILADOR/OSCILADORUNO.py
```

Genera una señal discreta periódica a partir de cuatro patrones de 8 bits definidos en:

```text
OSCILADOR/index.txt
```

Con la configuración actual:

```text
00000001#00000000#11111111#00000000#
```

los valores generados son:

```text
1, 0, -1, 0, 1, 0, -1, 0, ...
```

Esto corresponde a una aproximación discreta de `cos(t)` con período de cuatro muestras.

### Restricción

`N` debe ser un entero positivo múltiplo de 4.

Ejemplo:

```bash
cd OSCILADOR
python3 OSCILADORUNO.py 8
```

La salida se escribe en:

```text
OSCILADOR/salida.txt
```

## 2. TM Multiplicador

Archivo:

```text
MULTIPLICADOR/MULTIPLICADORUNO.py
```

Recibe dos señales de igual longitud:

```text
MULTIPLICADOR/entrada_x.txt
MULTIPLICADOR/entrada_cos.txt
```

y produce el producto **muestra a muestra**:

```text
salida[i] = entrada_x[i] · entrada_cos[i]
```

Por ejemplo:

```text
4 · 1  = 4
4 · 0  = 0
4 · -1 = -4
```

La salida se guarda en:

```text
MULTIPLICADOR/salida.txt
```

### Nota de implementación

La operación aritmética de cada par de muestras se calcula en Python al construir la tabla de transiciones (`delta`). La Máquina de Turing ejecuta después la secuencia de estados que escribe cada resultado bit a bit en su cinta.

Esto significa que este módulo modela la **ejecución de la TM y su manejo de la cinta**, pero no implementa un algoritmo de multiplicación binaria `shift-and-add` dentro de la ejecución de estados.

## 3. TM Filtro

Archivo:

```text
FILTRO/FILTROUNO.py
```

Lee una señal desde:

```text
FILTRO/index.txt
```

y procesa bloques **no solapados de cuatro muestras**.

Para cada bloque:

```text
[a, b, c, d]
```

calcula conceptualmente:

```text
(a + b + c + d) / 4
```

Como la ventana tiene tamaño 4, la implementación aprovecha que dividir por 4 equivale a un desplazamiento aritmético de 2 bits:

```text
suma >> 2
```

El resultado se representa nuevamente en 8 bits con complemento a dos.

### ¿Por qué una ventana de cuatro?

El oscilador utilizado tiene un período de cuatro muestras:

```text
[1, 0, -1, 0]
```

Por eso cada ventana del filtro cubre exactamente un ciclo del oscilador.

El filtro es una **simplificación didáctica de un pasabajos**: realiza promedios de ventanas fijas de cuatro muestras y no pretende ser un filtro ideal general.

La salida se guarda en:

```text
FILTRO/salida.txt
```

## 4. Cinta potencialmente infinita y bidireccional

Cada TM utiliza una estructura como:

```python
self.tape: Dict[int, str] = {}
```

La posición del cabezal es un entero:

```python
self.head: int = 0
```

y los movimientos se implementan como:

```python
self.head += 1   # derecha
self.head -= 1   # izquierda
```

No existe una lista de tamaño fijo ni un límite incorporado al índice. Por ello, conceptualmente, la cinta puede extenderse en ambas direcciones.

### Demostración formal

La carpeta `DEMOS/` contiene una TM independiente:

```text
DEMOS/DEMO_CINTA_BIDIRECCIONAL.py
```

Esta máquina realiza el siguiente recorrido:

```text
... ← -5 ← -4 ← -3 ← -2 ← -1 ← 0 → 1 → 2 → 3 → 4 → 5 → ...
```

Escribe símbolos en posiciones negativas, cruza nuevamente el origen y continúa hacia posiciones positivas.

Ejecutarla con:

```bash
python3 DEMOS/DEMO_CINTA_BIDIRECCIONAL.py
```

debe terminar mostrando:

```text
Posiciones negativas escritas: [-5, -4, -3, -2, -1]
Posiciones positivas escritas: [1, 2, 3, 4]
CONFIRMA cinta bidireccional infinita: True
```

La demostración está separada del pipeline porque los algoritmos específicos de oscilación, multiplicación y filtrado no necesitan cruzar la posición 0 durante su cálculo. La prueba demuestra que **la estructura de cinta sí soporta movimiento en ambas direcciones**.

## 5. Harness de integración

Archivo:

```text
HARNESS/run_pipeline.py
```

Es el punto de entrada recomendado para probar todo el sistema.

El `harness`:

- genera la señal cosenoidal con el oscilador;
- escribe las señales de entrada del multiplicador;
- ejecuta dos multiplicaciones;
- pasa el resultado al filtro;
- convierte las salidas de 8 bits a enteros con signo para mostrarlas;
- comprueba automáticamente el resultado del filtrado.

### Caso de prueba incluido

El caso de prueba usa:

```text
x(t) = [4, 4, 4, -4, -4, -4, -4, 4]
```

y obtiene:

```text
x(t) · cos²(t) = [4, 0, 4, 0, -4, 0, -4, 0]
```

Después de agrupar de cuatro en cuatro:

```text
[4, 0, 4, 0]   →  8 / 4  =  2
[-4, 0, -4, 0] → -8 / 4  = -2
```

Por tanto, la salida esperada es:

```text
[2, -2]
```

## Formato de los archivos de entrada

### Oscilador

`OSCILADOR/index.txt` contiene exactamente cuatro patrones de 8 bits, separados por `#`.

### Multiplicador

`MULTIPLICADOR/entrada_x.txt` y `MULTIPLICADOR/entrada_cos.txt` deben contener el mismo número de muestras. Cada muestra debe ser un bloque de 8 bits.

### Filtro

`FILTRO/index.txt` debe contener un número de muestras múltiplo de 4.

## Ejecución individual

También es posible ejecutar cada módulo por separado.

### Oscilador

```bash
cd OSCILADOR
python3 OSCILADORUNO.py 8
```

### Multiplicador

Primero deben existir `entrada_x.txt` y `entrada_cos.txt` en la carpeta `MULTIPLICADOR`:

```bash
cd MULTIPLICADOR
python3 MULTIPLICADORUNO.py
```

### Filtro

Debe existir `index.txt` en la carpeta `FILTRO`:

```bash
cd FILTRO
python3 FILTROUNO.py
```

## Conceptos de Máquinas de Turing utilizados

Cada implementación comparte los elementos fundamentales de una Máquina de Turing:

- **Cinta:** diccionario indexado por posiciones enteras.
- **Cabezal:** entero `head` que identifica la posición actual.
- **Símbolo blanco:** `B`.
- **Estado actual:** almacenado en `self.state`.
- **Función de transición:** almacenada en `self.delta`.
- **Movimiento:** `L`, `R` o `N` según la máquina.
- **Estado de parada:** `q_halt`.
- **Ejecución:** mediante pasos sucesivos con `step()` hasta alcanzar `q_halt`.

Además, las máquinas mantienen un registro `trace` y un contador `step_count`, lo que permite inspeccionar la ejecución y verificar que alcanzan el estado de parada.

## Verificación actual

El pipeline completo fue probado con el caso incluido y alcanza correctamente:

```text
salida filtrada: [2, -2]
```

La verificación automática del `harness` comprueba que cada salida coincide con el promedio entero calculado sobre su ventana correspondiente.

La demo de cinta bidireccional también fue ejecutada correctamente y confirmó la escritura en posiciones negativas y positivas.

## Consideraciones y limitaciones

1. El procesamiento utiliza aritmética de **8 bits en complemento a dos**. Los resultados se almacenan de nuevo en ese ancho.
2. El oscilador requiere `N` múltiplo de 4 porque su patrón tiene período 4.
3. El filtro trabaja con ventanas no solapadas de 4 muestras.
4. El filtro es una simplificación de un pasabajos mediante promedio por bloques; no es un filtro ideal de frecuencia general.
5. En el multiplicador y en el filtro, ciertos resultados numéricos se calculan en Python durante la construcción de la tabla de transiciones. La TM se encarga de secuenciar la escritura y el recorrido de la cinta.
6. Los archivos de entrada y salida son deliberadamente sencillos para facilitar la inspección y la demostración del funcionamiento.
