import pyvisa
import time
import matplotlib
matplotlib.use("Agg")
matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
plt.style.use("dark_background")

plt.rcParams.update({
    "font.family": "monospace",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "lines.linewidth": 2,
    "lines.marker": "."

})

from gf import GF
from li import LI


def main():

    try:
        rm = pyvisa.ResourceManager()

        gf = GF(rm.open_resource(
            "USB0::0x1AB1::0x0641::DG4E163251533::INSTR"
        ))
        gf.set_v(50e-3)
        gf.output("ON")

        lockin = LI(rm.open_resource(
            "ASRL5::INSTR",
            write_termination="\r",
            read_termination="\n",
        ))

        lockin.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)
        
        data = []
        start = 32.764e+3
        end = 32.767e+3
        N = 500

        plt.ion()
        fig, ax = plt.subplots()
        line_x, = ax.plot([], [], label="X")
        line_y, = ax.plot([], [], label="Y")
        ax.legend()

        for i in range(N):
            f = start + i * (end - start) / (N - 1)

            gf.set_f(f)
            plt.pause(2)

            x, y = lockin.xy()
            data.append((f, x, y))
            print(data[-1])

            ff, xx, yy = zip(*data)

            if i % 3 == 0:
                line_x.set_data(ff, xx)
                line_y.set_data(ff, yy)

                ax.relim()
                ax.autoscale_view()
                fig.canvas.draw_idle()
                fig.canvas.flush_events()

        plt.ioff()
        plt.show()


        gf.output("OFF")

        f, x, y = zip(*data)

        plt.plot(f, x, label="X")
        plt.plot(f, y, label="Y")
        plt.legend()
        plt.savefig("sweep.png")
    
    finally:
        gf.output("OFF")


if __name__ == "__main__":
    main()