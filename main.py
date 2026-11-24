import pyvisa
import time
import math
import matplotlib.pyplot as plt

from gf import GF
from li import LI
from psu import PSU
from sweeper import Sweeper


def wait_for_coil_current(psu, requested_current, field, timeout=30):
    tolerance = max(0.1, 0.2 * abs(requested_current))
    deadline = time.monotonic() + timeout

    while True:
        measured_current = psu.read_I()
        if math.isfinite(measured_current) and abs(measured_current - requested_current) <= tolerance:
            print(f"Coil current: {measured_current:.3f} A at {field:.5f} T")
            return
        if time.monotonic() >= deadline:
            measured_voltage = psu.read_V()
            output_state = psu.query("OUTP?").strip()
            raise RuntimeError(
                f"Coil current did not reach {requested_current:.3f} A after {timeout} s "
                f"at {field:.5f} T: measured {measured_current:.3f} A, "
                f"{measured_voltage:.3f} V, output={output_state}"
            )
        time.sleep(1)


def main():

    rm = pyvisa.ResourceManager()

    gf = GF(rm.open_resource(
        "USB0::0x1AB1::0x0641::DG4E163251533::INSTR"
    ))

    lockin = LI(rm.open_resource(
        "ASRL5::INSTR",
        write_termination="\r",
        read_termination="\n",
    ))

    psu = PSU(rm.open_resource("GPIB0::1::INSTR"))

    lockin.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)

    sweeper = Sweeper(gf, lockin)


    psu.CC()
    time.sleep(2)
    voltage_limit = min(40.0, float(psu.query("VOLT? MAX")))
    if not math.isfinite(voltage_limit) or voltage_limit <= 0:
        raise RuntimeError("Invalid maximum voltage reported by coil PSU")
    print(f"Coil PSU voltage limit: {voltage_limit:g} V")
    max_field = 0.8 * 0.2534
    fields = [max_field * (i + 0) / 4 for i in range(4)]
    psu.set_field(fields[0], vmax=voltage_limit)
    time.sleep(2)

    try:
        psu.output("ON")
        time.sleep(2)

        for field in fields:
            requested_current = psu.set_field(field, vmax=voltage_limit)
            wait_for_coil_current(psu, requested_current, field)

            sweeper.run(
                start=63e3,
                end=69e3,
                N=150,
                amplitude=.120,
                direction="forwards",
                plotlive=True,
                stall=False
            )
            sweeper.save(filename=f"field_{field:.3f}T")
    finally:
        psu.output("OFF")

    plt.ioff()
    plt.show()

if __name__ == "__main__":
    main()
