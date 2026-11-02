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
        start=63.5e3,
        end=67.4e3,
        N=200,
        amplitude=1.5,
        direction="forwards",
        plotlive=True
    )

    sweeper.save()

    sweeper.run(
        start=67.4e3,
        end=67.6e3,
        N=200,
        amplitude=1.5,
        direction="forwards",
        plotlive=True
    )

    sweeper.save()

    sweeper.run(
            start=67.6e3,
            end=80e3,
            N=600,
            amplitude=1.5,
            direction="forwards",
            plotlive=True
        )

    sweeper.save("grueso")

    plt.ioff()
    plt.show()

if __name__ == "__main__":
    main()