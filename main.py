import pyvisa
import time
import matplotlib.pyplot as plt

from gf import GF
from li import LI
from psu import PSU
from sweeper import Sweeper


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
    fields = [-0.2536 + i * (0.5070 / 9) for i in range(10)]
    psu.set_field(fields[0], vmax=40)
    time.sleep(2)
    psu.output("ON")
    time.sleep(2)

    try:
        for field in fields:
            psu.set_field(field, vmax=40)
            time.sleep(2)

            sweeper.run(
                start=63e3,
                end=70e3,
                N=150,
                amplitude=.2,
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
