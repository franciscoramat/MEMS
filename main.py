import pyvisa
import matplotlib.pyplot as plt

from gf import GF
from li import LI
from sweeper import Sweeper


def main():

    rm = pyvisa.ResourceManager()

    gf = GF(rm.open_resource(
        "USB0::0x1AB1::0x0641::DG4E163251533::INSTR"
    ))

    lockin = LI(rm.open_resource(
        "ASRL10::INSTR",
        write_termination="\r",
        read_termination="\n",
    ))

    lockin.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)

    sweeper = Sweeper(gf, lockin)


    sweeper.run(
        start=64e3,
        end=66e3,
        N=20000,
        amplitude=2e-3,
        direction="forwards",
        plotlive=True,
        stall=False
    )

    sweeper.save()

    plt.ioff()
    plt.show()

if __name__ == "__main__":
    main()