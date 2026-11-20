# Open6009: guía rápida en español

Driver para usar la **NI USB-6009** en Linux sin NI-DAQmx ni Windows.
Todo lo de abajo se copia y pega en la terminal.

## 1. Instalar (una sola vez)

```bash
git clone https://github.com/IKGB105/Open6009.git
cd Open6009
./setup.sh
```

Te pedirá tu contraseña de `sudo` (solo para dar permiso de USB a tu usuario).
Al final debe decir `OK: USB-6009 encontrada`. Si no, desconecta y reconecta la DAQ y corre:

```bash
.venv/bin/open6009 devices
```

Debe aparecer `"pid": "717b"`.

> Requisitos: Python 3.11 o más nuevo y `libusb`. En Arch/CachyOS/Manjaro:
> `sudo pacman -S --needed python libusb`

## 2. Usarla desde Python (consola)

```bash
cd ~/Open6009        # o donde lo hayas clonado
.venv/bin/python -i tools/daq.py
```

Dentro de la consola:

```python
ai(0)                              # voltaje promedio en AI0
ai([0, 1])                         # AI0 y AI1
v = ai(0, rate=1000, n=500, raw=True)   # lista de muestras
plot(ai([0, 1], rate=2000, n=1000, raw=True), rate=2000)
ao(0, 2.5)                         # AO0 a 2.5 V (0 a 5 V)
di(0)                              # lee puerto digital P0 (0-255)
sweep(ao_ch=0, ai_ch=0)            # prueba AO0->AI0 (cable de terminal 14 a 2)
trace(True)                        # imprime cada paquete USB
```

Para salir: `Ctrl+D`.

## 3. Depurar con breakpoints (tipo Keil / CubeIDE)

```bash
code .
```

1. Instala las extensiones **Python** y **Python Debugger** de Microsoft si VS Code las pide.
2. Abre `examples/debug_demo.py`.
3. Clic a la izquierda del número de línea para poner un breakpoint.
4. **F5** → elige **"Debug: archivo actual (DAQ)"**.

| Keil / CubeIDE | VS Code |
|---|---|
| Step Over | F10 |
| Step Into | F11 |
| Run | F5 |
| Live Expressions | Panel WATCH (ej. `max(muestras)`) |

Con el programa detenido puedes escribir `daq.ai(0)` o `daq.ao(0, 3.3)` en la **Debug Console**.
La opción **"entrar al driver Open6009"** te deja hacer F11 hasta los paquetes USB.

## 4. Usarla desde LabVIEW

Arranca el servidor (déjalo corriendo en una terminal):

```bash
.venv/bin/python tools/labview_bridge.py
```

En LabVIEW:

1. **TCP Open Connection**: dirección `localhost`, puerto `6009`.
2. **TCP Write**: el comando + constante **Line Feed**, por ejemplo `AI 0 1000 100`.
3. **TCP Read**: modo **CRLF**, bytes to read `1000000`, timeout `5000`.
4. Quita el `OK n m ` del inicio y pasa el resto por **Spreadsheet String To Array**
   con delimitador `,` y formato **`%.;%f`** (obligatorio si tu sistema usa coma decimal).
5. Al terminar: **TCP Write** `QUIT` y **TCP Close Connection**.

| Comando | Respuesta |
|---|---|
| `AI 0 1000 100` | `OK 100 1 v,v,v,...` (100 muestras de AI0 a 1 kS/s) |
| `AI 0,1 1000 100` | `OK 100 2 a,b,a,b,...` (canales intercalados) |
| `AI 0 1000 100 DIFF 2` | diferencial, rango ±2 V |
| `ASTART 0,1 1000` / `AREAD 100` / `ASTOP` | adquisición continua |
| `AO 0 2.5` | `OK <código DAC>` |
| `DI 0` | `OK <0-255>` |
| `DO 0 255` | `OK` (sin probar en hardware) |
| `CSTART` / `CREAD` / `CSTOP` | contador |

Probar sin LabVIEW: `nc localhost 6009` y escribe `AI 0 1000 10`.

Mientras el servidor esté corriendo, la interfaz gráfica y `daq.py` no pueden usar la DAQ (solo un programa a la vez).

## 5. Interfaz gráfica

```bash
./run-open6009
```

**Connect** → activa canales → **Analog Scope** → **Start**.

## Terminales del bloque analógico (1–16)

```
 1 GND    2 AI0    3 AI4    4 GND
 5 AI1    6 AI5    7 GND    8 AI2
 9 AI6   10 GND   11 AI3   12 AI7
13 GND   14 AO0   15 AO1   16 GND
```

Una entrada sin nada conectado marca **~1.39 V**: es normal.
Si las lecturas brincan, aprieta los tornillos (mejor cable sólido 22–24 AWG).

## Si no funciona

- **`cannot claim interface ... BUSY`**: otro programa tiene la DAQ (la interfaz, el servidor de LabVIEW u otra consola). Ciérralo.
- **`unexpected EP1 reply at captured frame 0`**: tu DAQ tiene otra versión de firmware. Corre esto y manda el resultado:

  ```bash
  .venv/bin/python -c "
  import sys; sys.path.insert(0, 'tools'); import daq
  daq.trace(True)
  try: daq.di(0)
  except Exception as e: print(e)"
  ```

- **No aparece en `open6009 devices`**: revisa `lsusb | grep 3923` y que hayas corrido `./setup.sh`.
