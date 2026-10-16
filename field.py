import pyvisa
import matplotlib

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

from psu import PSU
from gm import GM


def main():
    rm = pyvisa.ResourceManager()
    psu = None

    try:
        gm = GM(rm.open_resource("ASRL6::INSTR"))
        psu = PSU(rm.open_resource("GPIB0::1::INSTR"))

        start = -20
        end = 20
        N = 40
        vmax = 40

        data = []

        psu.CC()
        psu.set_I(0, vmax)
        psu.output("ON")

        plt.ion()
        fig, ax = plt.subplots()

        line_b, = ax.plot([], [], label="Magnetic field")

        ax.set_xlabel("Measured current (A)")
        ax.set_ylabel("Magnetic field")
        ax.legend()

        for k in range(N):
            i = start + k * (end - start) / (N - 1)

            psu.set_I(i, vmax)
            plt.pause(3)

            measured_i = psu.read_I()
            field = gm.read()

            data.append((measured_i, field))
            print(data[-1])

            if k % 3 == 0 or k == N - 1:
                ii, bb = zip(*data)

                line_b.set_data(ii, bb)

                ax.relim()
                ax.autoscale_view()
                fig.canvas.draw_idle()
                fig.canvas.flush_events()
            
        fig.savefig("sweep.png", dpi=300)
        import numpy as np
        np.savetxt("sweep.csv", data, delimiter=",", header="Current_A,Field", comments="")

    finally:
        psu.output("OFF")
        
    plt.ioff()
    plt.show()


if __name__ == "__main__":
    main()