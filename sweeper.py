import time
import csv 
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt




class Sweeper:
    def __init__(self, gf, lockin):
        self.gf = gf
        self.lockin = lockin
        self.data = []
        self.fig = None
        self.timestep = .5




    def run(self, start, end, N, amplitude, 
        direction="forwards", 
        plotlive=False,
        stall=False):

        success = False

        self.data = []

        if self.fig is not None:
            plt.close(self.fig)
        self.fig = None

        self.amplitude = amplitude

        if plotlive:
            self.liveplot()

        print(f"Iniciando... {amplitude} V de excitación.\n")

        try:

            self.gf.set_v(amplitude)
            self.gf.output("ON")
            time.sleep(2)

            for i in range(N if direction != "both" else 2*N):

                if direction == "forwards":
                    f = start + i * (end - start) / (N - 1)

                if direction == "backwards":
                    f = end - i * (end - start) / (N - 1)

                if direction == "both":
                    f = start + min(i, 2*N - 1 - i) * (end - start) / (N - 1)

                self.gf.set_f(f)
                
                if plotlive:
                    plt.pause(self.timestep)
                else:
                    time.sleep(self.timestep)

                x, y = self.lockin.xy()
                self.data.append((f, x, y))
                print(self.data[-1])

                if plotlive and i % 2 == 0:
                    self.liveplot()

            success = True

        except (Exception, KeyboardInterrupt) as e:
            if self.data:
                self.save(error=str(e))
            raise


        finally:
            if not(stall and success):
                self.gf.output("OFF")

        if plotlive:
            self.liveplot()
        return self.data




    def liveplot(self):


        if self.fig is None:
                
            plt.style.use("dark_background")

            plt.rcParams.update({
                "font.family": "monospace",
                "axes.grid": True,
                "grid.alpha": 0.25,
                "lines.linewidth": 2,
                "lines.marker": "."
            })

            plt.ion()
            self.fig, (self.ax_x, self.ax_y, self.ax_r) = plt.subplots(
                3, 1, sharex=True
            )

            self.line_x, = self.ax_x.plot([], [], label="X", color="cyan")
            self.line_y, = self.ax_y.plot([], [], label="Y", color="orange")
            self.line_r, = self.ax_r.plot([], [], label="R", color="lime")

            for ax in (self.ax_x, self.ax_y, self.ax_r):
                ax.legend()

            self.ax_r.set_xlabel("Frecuencia (Hz)")
            self.ax_r.set_ylabel("Amplitud (V)")
            plt.tight_layout()

        if not self.data:
            return

        ff, xx, yy = zip(*self.data)
        rr = [(x**2 + y**2)**0.5 for x, y in zip(xx, yy)]

        self.line_x.set_data(ff, xx)
        self.line_y.set_data(ff, yy)
        self.line_r.set_data(ff, rr)

        for ax in (self.ax_x, self.ax_y, self.ax_r):
            ax.relim()
            ax.autoscale_view()

        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()




    def save(self, filename=None, error=None):



        if not self.data:
            raise ValueError("No hay datos para guardar")

        if filename is None:
            filename = datetime.now().strftime("%d-%m-%H%M")

        # Guardar CSV
        with open(f"{filename}.csv", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([f"Excitación: {self.amplitude} V"])
            writer.writerow(["Frecuencia (Hz)", "X (V)", "Y (V)", "R (V)"])
            writer.writerows(
                (f, x, y, (x**2 + y**2)**0.5)
                for f, x, y in self.data
            )
            if error is not None:
                writer.writerow([f"ERROR: {error}"])

        # Guardar PNG
        self.liveplot()
        self.fig.savefig(f"{filename}.png")

        print(f"Archivos guardados: {filename}.csv, {filename}.png")