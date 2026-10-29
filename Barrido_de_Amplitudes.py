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

    amplitudes = [i * 10e-3 for i in range(14, 100)
]
    for amplitude in amplitudes:

        sweeper.run(
            start=63.5e3,
            end=68e3,
            N=450,
            amplitude=amplitude,
            direction="forwards",
            plotlive=True
        )

        sweeper.save()

    plt.ioff()
    plt.show()

if __name__ == "__main__":
    main()