"""Ejemplo para depurar la DAQ paso a paso en VS Code (F5).

Pon breakpoints (clic a la izquierda del número de línea) en las líneas marcadas
y usa F10 (paso), F11 (entrar a la función), F5 (continuar). Las variables se ven
en el panel VARIABLES y puedes agregar expresiones en WATCH, p. ej. `max(muestras)`.
"""

import daq

daq.connect()

daq.ao(0, 2.5)                     # <- breakpoint: mide AO0 con el multímetro aquí
muestras = daq.ai(0, rate=1000, n=200, raw=True)   # <- breakpoint: revisa `muestras`
promedio = sum(muestras) / len(muestras)
print(f"AI0 promedio: {promedio:.4f} V")

puerto0 = daq.di(0)                # <- breakpoint: `puerto0` en binario: bin(puerto0)
print(f"P0 = {puerto0:#04x}")

daq.ao(0, 0)
daq.close()
