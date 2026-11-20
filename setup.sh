#!/usr/bin/env bash
# Instalación completa de Open6009 (este fork) en Linux.
# Uso:  ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/4 Entorno de Python y aplicación"
./install.sh

echo "== 2/4 matplotlib (para daq.plot)"
.venv/bin/pip install -q matplotlib

echo "== 3/4 Permisos USB (regla udev, pide contraseña de sudo)"
sudo install -Dm644 packaging/70-open6009.rules /etc/udev/rules.d/70-open6009.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=usb

echo "== 4/4 Buscando la DAQ"
if .venv/bin/open6009 devices | grep -q 717b; then
  echo "OK: USB-6009 encontrada. Prueba:  .venv/bin/python -i tools/daq.py"
else
  echo "No se encontró la USB-6009. Desconéctala, vuelve a conectarla y corre:"
  echo "  .venv/bin/open6009 devices"
fi
