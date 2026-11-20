#!/usr/bin/env python3
"""TCP bridge so LabVIEW (or anything with sockets) can drive a USB-6009 via Open6009.

Line-based ASCII protocol: one command per line, LF-terminated; one reply line per
command, starting with "OK" or "ERR". Numbers use '.' as the decimal separator.

  PING                              -> OK open6009-bridge 1
  AI <chs> <rate> <n> [RSE|DIFF] [range]
                                    -> OK <scans> <nch> v,v,v,...   (scan-major)
  ASTART <chs> <rate>               -> OK                (continuous, RSE +/-10 V)
  AREAD <n>                         -> OK <scans> <nch> v,v,v,...
  ASTOP                             -> OK
  AO <ch> <volts>                   -> OK <dac_code>     (0..5 V)
  DI <port>                         -> OK <value 0-255>
  DO <port> <value>                 -> OK                (UNTESTED on hardware)
  CSTART / CREAD / CSTOP            -> OK / OK <count> / OK
  QUIT                              -> closes this connection

<chs> is a comma list without spaces, e.g. 0 or 0,1,3.
Example: "AI 0,1 1000 100" returns 100 scans of AI0 and AI1:
"OK 100 2 a0,b0,a1,b1,..." -> LabVIEW: Spreadsheet String To Array (delimiter ",")
then Reshape Array to [scans][nch].

The device stays claimed while the server runs, so the Open6009 GUI can't use it
at the same time. One client at a time.
"""

from __future__ import annotations

import argparse
import socket
import sys

from open6009.acquisition import AnalogInputConfig, TerminalMode
from open6009.device import Usb6009

VERSION = "open6009-bridge 1"


def _channels(text: str) -> tuple[int, ...]:
    return tuple(int(c) for c in text.split(","))


def _fmt(batch) -> str:
    values = ",".join(format(v, ".6f") for scan in batch.scans_volts for v in scan)
    return f"OK {batch.samples_per_channel} {len(batch.channels)} {values}"


class Bridge:
    def __init__(self, device: Usb6009) -> None:
        self.d = device
        self.streaming = False

    def handle(self, line: str) -> str:
        parts = line.split()
        if not parts:
            return "ERR empty command"
        cmd, args = parts[0].upper(), parts[1:]
        d = self.d
        if cmd == "PING":
            return f"OK {VERSION}"
        if cmd == "AI":
            if self.streaming:
                return "ERR stop continuous acquisition first (ASTOP)"
            mode = TerminalMode.DIFFERENTIAL if len(args) > 3 and args[3].upper().startswith("DIFF") \
                else TerminalMode.RSE
            vrange = float(args[4]) if len(args) > 4 else 10.0
            cfg = AnalogInputConfig(_channels(args[0]), mode, vrange, int(args[2]), float(args[1]))
            return _fmt(d.acquire_analog_volts(cfg, explicitly_authorized=True))
        if cmd == "ASTART":
            d.start_continuous_ai(channels=_channels(args[0]), sample_rate_hz=int(args[1]),
                                  explicitly_authorized=True)
            self.streaming = True
            return "OK"
        if cmd == "AREAD":
            return _fmt(d.read_continuous_ai_volts(samples=int(args[0]) if args else None))
        if cmd == "ASTOP":
            d.stop_continuous_ai()
            self.streaming = False
            return "OK"
        if cmd == "AO":
            return f"OK {d.set_reference_ao_voltage(int(args[0]), float(args[1]), explicitly_authorized=True)}"
        if cmd == "DI":
            return f"OK {d.read_captured_digital_port(int(args[0]), explicitly_authorized=True)}"
        if cmd == "DO":
            d.write_digital_port(int(args[0]), int(args[1], 0), explicitly_authorized=True)
            return "OK"
        if cmd == "CSTART":
            d.start_counter(explicitly_authorized=True)
            return "OK"
        if cmd == "CREAD":
            return f"OK {d.read_counter_raw()[1]}"
        if cmd == "CSTOP":
            d.stop_counter()
            return "OK"
        return f"ERR unknown command {cmd}"

    def cleanup(self) -> None:
        if self.streaming:
            try:
                self.d.stop_continuous_ai()
            except Exception:
                pass
            self.streaming = False


def serve(host: str, port: int) -> None:
    with Usb6009.open() as device, socket.create_server((host, port), reuse_port=False) as srv:
        bridge = Bridge(device)
        print(f"{VERSION} listening on {host}:{port} (Ctrl+C to stop)", flush=True)
        while True:
            conn, addr = srv.accept()
            print(f"client {addr[0]}:{addr[1]} connected", flush=True)
            with conn, conn.makefile("rwb", buffering=0) as f:
                for raw in f:
                    line = raw.decode("ascii", "replace").strip()
                    if line.upper() == "QUIT":
                        break
                    try:
                        reply = bridge.handle(line)
                    except Exception as exc:  # report, keep serving
                        reply = f"ERR {type(exc).__name__}: {exc}".replace("\n", " ")
                    f.write((reply + "\n").encode("ascii"))
            bridge.cleanup()
            print("client disconnected", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--host", default="127.0.0.1",
                   help="bind address (default localhost; use 0.0.0.0 or a Tailscale IP "
                        "for another machine - there is NO authentication)")
    p.add_argument("--port", type=int, default=6009)
    a = p.parse_args()
    try:
        serve(a.host, a.port)
    except KeyboardInterrupt:
        print("stopped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
