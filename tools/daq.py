"""Quick interactive helpers for poking at the USB-6009 from Python.

Usage (from ~/Proyects/Open6009):
    .venv/bin/python -i tools/daq.py          # opens the DAQ, drops you in a REPL
    >>> ai(0)                                  # mean voltage on AI0
    >>> v = ai(0, rate=1000, n=500, raw=True)  # list of samples
    >>> ao(0, 2.5)
    >>> sweep(ao_ch=0, ai_ch=0)                # AO->AI loopback table
    >>> plot(ai([0, 1], rate=2000, n=1000, raw=True))
    >>> trace(True)                            # print every USB packet (hex)

Or in your own script:
    import sys; sys.path.insert(0, "tools"); import daq
    daq.connect(); print(daq.ai(0)); daq.close()
"""

from __future__ import annotations

import statistics

from open6009.acquisition import AnalogInputConfig, TerminalMode
from open6009.device import Usb6009

dev: Usb6009 | None = None
_trace = False
_orig_io = None


def connect() -> Usb6009:
    """Open the DAQ (once). Close the Open6009 GUI / LabVIEW bridge first."""
    global dev, _orig_io
    if dev is None:
        dev = Usb6009.open()
        dev.__enter__()
        t = dev.transport
        _orig_io = (t.write, t.read)

        def write(ep, data, timeout_ms=1000):
            if _trace:
                print(f"  -> EP{ep:02x} {bytes(data).hex(' ')}")
            return _orig_io[0](ep, data, timeout_ms=timeout_ms)

        def read(ep, size, timeout_ms=1000):
            data = _orig_io[1](ep, size, timeout_ms)
            if _trace:
                shown = bytes(data[:48]).hex(" ") + (" ..." if len(data) > 48 else "")
                print(f"  <- EP{ep:02x} [{len(data)}] {shown}")
            return data

        t.write, t.read = write, read
    return dev


def close() -> None:
    global dev
    if dev is not None:
        dev.__exit__(None, None, None)
        dev = None


def trace(on: bool = True) -> None:
    """Print every USB packet sent/received (EP2 streaming bypasses this)."""
    global _trace
    _trace = on


def ai(ch=0, rate=1000, n=200, diff=False, vrange=10.0, raw=False):
    """Read AI. ch: int or list. Returns mean V (or list of means), or samples if raw=True."""
    chans = tuple(ch) if isinstance(ch, (list, tuple)) else (ch,)
    mode = TerminalMode.DIFFERENTIAL if diff else TerminalMode.RSE
    cfg = AnalogInputConfig(chans, mode, vrange if diff else 10.0, n, rate)
    scans = connect().acquire_analog_volts(cfg, explicitly_authorized=True).scans_volts
    cols = [[s[i] for s in scans] for i in range(len(chans))]
    if raw:
        return cols[0] if len(chans) == 1 else cols
    means = [statistics.mean(c) for c in cols]
    return means[0] if len(chans) == 1 else means


def ao(ch: int, volts: float) -> int:
    """Set AO0/AO1 (0..5 V). Returns the DAC code."""
    return connect().set_reference_ao_voltage(ch, volts, explicitly_authorized=True)


def di(port: int = 0) -> int:
    return connect().read_captured_digital_port(port, explicitly_authorized=True)


def do(port: int, value: int) -> None:
    """Write a digital port (open-collector; UNTESTED on this unit)."""
    connect().write_digital_port(port, value, explicitly_authorized=True)


def sweep(ao_ch=0, ai_ch=0, points=(0, 0.5, 1, 2, 2.5, 3, 4, 4.5, 5)):
    """AO->AI loopback check; needs a wire from AO<ao_ch> to AI<ai_ch>."""
    print(f"AO{ao_ch} set   AI{ai_ch} read   error")
    for v in points:
        ao(ao_ch, v)
        m = ai(ai_ch)
        print(f"{v:7.3f} V  {m:8.4f} V  {(m - v) * 1000:+7.1f} mV")
    ao(ao_ch, 0)


def plot(data, rate=None):
    """Plot samples from ai(..., raw=True). Needs matplotlib in the venv."""
    import matplotlib.pyplot as plt
    series = data if data and isinstance(data[0], list) else [data]
    for i, s in enumerate(series):
        x = [k / rate for k in range(len(s))] if rate else range(len(s))
        plt.plot(x, s, label=f"ch {i}")
    plt.xlabel("Time (s)" if rate else "Sample")
    plt.ylabel("Voltage (V)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()


if __name__ == "__main__":
    import atexit
    connect()
    atexit.register(close)
    print("USB-6009 connected. Try: ai(0), ao(0, 2.5), di(0), sweep(), trace(True). help(ai) for options.")
