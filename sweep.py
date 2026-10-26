import pyvisa
import time
import csv 
from datetime import datetime
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

from gf import GF
from li import LI


def main():

    try:
        rm = pyvisa.ResourceManager()

        gf = GF(rm.open_resource(
            "USB0::0x1AB1::0x0641::DG4E163251533::INSTR"
        ))
        amplitude = 50e-3
        gf.set_v(amplitude)
        gf.output("ON")
        print(f"Iniciando... {amplitude}V de excitación.\n")
        time.sleep(5)

        lockin = LI(rm.open_resource(
            "ASRL10::INSTR",
            write_termination="\r",
            read_termination="\n",
        ))

        lockin.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)

        data = []
        start = 63.5e+3
        end = 68e+3
        N = 450

        plt.ion()
        fig, (ax_x, ax_y, ax_r) = plt.subplots(3, 1, sharex=True)

        line_x, = ax_x.plot([], [], label="X", color="cyan")
        line_y, = ax_y.plot([], [], label="Y", color="orange")
        line_r, = ax_r.plot([], [], label="R", color="lime")

        for ax in (ax_x, ax_y, ax_r):
            ax.legend()

        ax_r.set_xlabel("Frecuencia (Hz)")
        ax_r.set_ylabel("Amplitud (V)")
        plt.tight_layout()

        filename = datetime.now().strftime("%d-%m-%H%M")
        
        direction = "forwards"  # "forwards", "backwards", "both"
        for i in range(N if direction != "both" else 2*N):

            if direction == "forwards":
                f = start + i * (end - start) / (N - 1)
            if direction == "backwards":
                f = end - i * (end - start) / (N - 1)
            if direction == "both":
                f = start + min(i, 2*N - 1 - i) * (end - start) / (N - 1)

            gf.set_f(f)
            plt.pause(1)

            x, y = lockin.xy()
            data.append((f, x, y))
            print(data[-1])

            if i % 2 == 0:
                ff, xx, yy = zip(*data)
                rr = [(x**2 + y**2)**0.5 for x, y in zip(xx, yy)]

                line_x.set_data(ff, xx)
                line_y.set_data(ff, yy)
                line_r.set_data(ff, rr)

                for ax in (ax_x, ax_y, ax_r):
                    ax.relim()
                    ax.autoscale_view()

                fig.canvas.draw_idle()
                fig.canvas.flush_events()

        gf.output("OFF")

        with open(f"{filename}.csv", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([f"Excitación: {amplitude}"])
            writer.writerow(["Frecuencia (Hz)", "X (V)", "Y (V)", "R (V)"])
            writer.writerows(
                (f, x, y, (x**2 + y**2)**0.5)
                for f, x, y in data
            )
        fig.savefig(f"{filename}.png")

        plt.ioff()
        plt.show()

    finally:
        gf.output("OFF")


if __name__ == "__main__":
    main()