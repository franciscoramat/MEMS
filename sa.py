import time

import pyvisa


def hz(value):
    if value >= 1e9:
        return f"{value / 1e9:.3f} GHz"
    if value >= 1e6:
        return f"{value / 1e6:.3f} MHz"
    if value >= 1e3:
        return f"{value / 1e3:.3f} kHz"
    return f"{value:.3f} Hz"


class SA:
    def __init__(self, inst):
        self.inst = inst
        self.write = inst.write
        self.query = inst.query

    def idn(self):
        return self.query("*IDN?").strip()

    def start_f(self, frequency):
        self.write(f":FREQ:STAR {frequency}")

    def stop_f(self, frequency):
        self.write(f":FREQ:STOP {frequency}")

    def center_f(self, frequency):
        self.write(f":FREQ:CENT {frequency}")

    def span(self, span):
        self.write(f":FREQ:SPAN {span}")

    def refresh_amplitude(self, softkey):
        self.write(":KEYB:KEYV ESC")
        time.sleep(0.1)
        self.write(":KEYB:KEYV AMP")
        time.sleep(0.1)
        self.write(f":KEYB:KEYV {softkey}")
        time.sleep(0.2)

    def ref_level(self, level):
        if not -100 <= level <= 20:
            raise ValueError("ref_level debe estar entre -100 y 20 dBm")
        self.write(":DISP:WIND:TRAC:Y:SCAL:SPAC LOG")
        self.write(f":DISP:WIND:TRAC:Y:SCAL:RLEV {level}")
        self.refresh_amplitude("F2")

    def y_scale(self, db_per_div):
        if not 0.1 <= db_per_div <= 20:
            raise ValueError("y_scale debe estar entre 0.1 y 20 dB/div")
        self.write(":DISP:WIND:TRAC:Y:SCAL:SPAC LOG")
        self.write(f":DISP:WIND:TRAC:Y:SCAL:PDIV {db_per_div}")
        self.refresh_amplitude("F4")

    def rbw(self, bandwidth):
        self.write(f":BAND:RES {bandwidth}")

    def vbw(self, bandwidth):
        self.write(f":BAND:VID {bandwidth}")

    def continuous(self, state):
        self.write(f":INIT:CONT {state}")

    def sweep(self, timeout=30000):
        previous_timeout = self.inst.timeout
        self.inst.timeout = timeout
        try:
            self.write(":INIT:IMM")
            self.query("*OPC?")
        finally:
            self.inst.timeout = previous_timeout

    def trace(self, trace=1):
        data = self.query(f":TRAC:DATA? TRACE{trace}")
        if data.startswith("#"):
            digits = int(data[1])
            data = data[2 + digits:]
        return [float(value) for value in data.replace(",", " ").split()]

    def peak(self, data, start, span):
        peak_index = max(range(len(data)), key=data.__getitem__)
        peak_frequency = start + peak_index * span / (len(data) - 1)
        peak_power = data[peak_index]
        return peak_frequency, peak_power


def main():
    name = "USB0::0x1AB1::0x0960::DSA8A163250968::INSTR"
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(name)

    sa = SA(inst)
    try:
        print(sa.idn())

        center = 1e6
        span = 1e6
        sa.center_f(center)
        sa.span(span)
        sa.ref_level(0)
        sa.rbw(10e3)
        sa.vbw(10e3)
        sa.continuous("OFF")
        sa.sweep()

        data = sa.trace()
        start = center - span / 2
        peak_index = max(range(len(data)), key=data.__getitem__)
        peak_frequency = start + peak_index * span / (len(data) - 1)

        print(f"Puntos: {len(data)}")
        print(f"Pico: {data[peak_index]:.2f} dBm a {hz(peak_frequency)}")
    finally:
        inst.close()
        rm.close()


if __name__ == "__main__":
    main()
