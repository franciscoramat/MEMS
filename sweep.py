import pyvisa
import time

from gf import GF
from li import LI


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

    data = []
    start = 32.74e+3
    end = 32.77e+3
    N = 40

    for i in range(N):
        f = start + i * (end - start) / (N - 1)

        gf.set_f(f)
        time.sleep(0.1)

        x, y = lockin.xy()

        data.append((f, x, y))
        print(data[-1])

    gf.output("OFF")


if __name__ == "__main__":
    main()