import pyvisa
import numpy as np
import time
import matplotlib.pyplot as plt
from cycler import cycler
from matplotlib.collections import LineCollection

class Oscilloscope:
	def __init__(self, inst):
		self.inst = inst
		self.write = inst.write
		self.query = inst.query

	def idn(self):
		return self.query("*IDN?").strip()

	def tscale(self, scale):
		self.write(f"HORIZONTAL:SCALE {scale}")

	def vscale(self, scale, channel=1):
		self.write(f"CH{channel}:SCALE {scale}")

	def position(self, position, channel=1):
	    self.write(f"CH{channel}:POSITION {position}")

	def offset(self, voltage, channel=1):
	    self.write(f"CH{channel}:OFFSET {voltage}")


	def single(self, points=10000):
		self.write("ACQUIRE:STATE OFF")
		self.write("SELECT:CH1 ON")
		self.write("SELECT:CH2 ON")
		self.write(f"HORIZONTAL:RECORDLENGTH {points}")
		self.write("ACQUIRE:MODE SAMPLE")
		self.write("ACQUIRE:STOPAFTER SEQUENCE")
		self.write("ACQUIRE:STATE ON")
		time.sleep(.5)
		self.write("TRIGGER FORCE")
		time.sleep(.5)
		print("Adquisición:", self.query("ACQUIRE:STATE?"))
		print("Single completado")

	def extract(self, channel=1):
		self.write("HEADER 0")
		self.write(f"DATA:SOURCE CH{channel}")
		self.write("DATA:ENCDG RIBINARY")
		self.write("DATA:WIDTH 1")

		n = int(self.query("HORIZONTAL:RECORDLENGTH?"))
		self.write("DATA:START 1")
		self.write(f"DATA:STOP {n}")

		# Factores de conversión
		dt = float(self.query("WFMOUTPRE:XINCR?"))
		t0 = float(self.query("WFMOUTPRE:XZERO?"))

		ymult = float(self.query("WFMOUTPRE:YMULT?"))
		yoff = float(self.query("WFMOUTPRE:YOFF?"))
		yzero = float(self.query("WFMOUTPRE:YZERO?"))

		# Transferencia binaria
		raw = self.inst.query_binary_values(
			"CURVE?",
			datatype="b",
			container=np.array
		)

		# Conversión a unidades físicas
		t = t0 + np.arange(len(raw)) * dt
		v = (raw - yoff) * ymult + yzero

		return t, v

	def plot(self, t, *v):

		plt.rcParams.update({
			# Fondo
			"figure.facecolor": "#080D14",
			"axes.facecolor": "#080D14",
			"savefig.facecolor": "#080D14",

			# Grilla
			"axes.grid": True,
			"axes.axisbelow": True,
			"grid.color": "#657080",
			"grid.alpha": 0.12,
			"grid.linewidth": 0.4,
			"grid.linestyle": "-",

			# Ejes
			"axes.edgecolor": "#4A5565",
			"axes.labelcolor": "#C8D0DA",
			"axes.linewidth": 0.6,
			"xtick.color": "#A0AAB8",
			"ytick.color": "#A0AAB8",
			"xtick.direction": "in",
			"ytick.direction": "in",

			# Texto
			"text.color": "#C8D0DA",
			"font.size": 9,

			# Resolución
			"figure.dpi": 160,
		})

		fig, ax1 = plt.subplots(figsize=(6, 4))
		ax2 = ax1.twinx()

		# Efecto fósforo: acumulación de brillo
		def phosphor(ax, signal, color):

			chunk = 32

			segments = [
				np.column_stack((t[i:i+chunk+1], signal[i:i+chunk+1]))
				for i in range(0, len(t)-1, chunk)
			]

			ax.add_collection(LineCollection(
				segments,
				colors=color,
				linewidths=0.35,
				alpha=0.06,
				antialiaseds=True
			))

			ax.autoscale_view()

		# CH1 - Eje izquierdo
		phosphor(ax1, v[0], "#F0CF4B")
		ax1.set_ylabel("CH1 (V)", color="#F0CF4B")
		ax1.tick_params(axis="y", colors="#F0CF4B")

		# CH2 - Eje derecho
		phosphor(ax2, v[1], "#4CD4E6")
		ax2.set_ylabel("CH2 (V)", color="#4CD4E6")
		ax2.tick_params(axis="y", colors="#4CD4E6")

		# Eje temporal compartido
		ax1.set_xlabel("Tiempo (s)")
		ax1.set_xlim(t[0], t[-1])

		# Grilla
		ax1.minorticks_on()
		ax1.grid(which="minor", alpha=0.08, linewidth=0.4)
		ax2.grid(False)

		fig.tight_layout()

		return fig

def main():
	name = "USB0::0x0699::0x0408::C011271::INSTR"
	rm = pyvisa.ResourceManager()
	inst = rm.open_resource(name)

	inst.timeout = 30000
	inst.chunk_size = 1024 * 1024

	osci = Oscilloscope(inst)
	osci.inst.timeout = 3000
	print(osci.idn())

	osci.tscale(1e-3)  # 10 µs/div
	osci.vscale(1)     # 500 mV/div

	print("Modo:", osci.query("TRIGGER:A:MODE?"))
	print("Estado:", osci.query("TRIGGER:STATE?"))
	osci.single(points=1_000_000)

	t, v = osci.extract()

	print(f"Recibidos {len(v)} puntos")
	print(f"Intervalo de muestreo: {t[1] - t[0]:.3e} s")

	np.savetxt(
		"waveform.csv",
		np.column_stack((t, v)),
		delimiter=",",
		header="Tiempo (s),Voltaje (V)",
		comments=""
	)

	inst.close()
	rm.close()


if __name__ == "__main__":
	main()