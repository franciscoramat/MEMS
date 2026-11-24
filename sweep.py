import pyvisa
import matplotlib.pyplot as plt
from datetime import datetime

from gf import GF
from li import LI
from sweeper import Sweeper


AMPLITUDES_V = [.9]
START_HZ = 63e3
END_HZ = 80e3
POINTS = 1000
DIRECTION = "forwards"
PLOT_LIVE = True


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
    lockin.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)

    sweeper = Sweeper(gf, lockin)

    try:
        for amplitude in AMPLITUDES_V:
            sweeper.run(
                start=START_HZ,
                end=END_HZ,
                N=POINTS,
                amplitude=amplitude,
                direction=DIRECTION,
                plotlive=PLOT_LIVE,
            )
            timestamp = datetime.now().strftime("%d-%m-%H%M%S")
            filename = f"{timestamp}_{amplitude * 1e3:g}mV"
            sweeper.save(filename=filename)
    finally:
        gf.output("OFF")
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()
