import pyvisa
import numpy as np


class Oscilloscope:
	def __init__(self, inst):
		self.inst = inst
		self.write = inst.write
		self.query = inst.query

	def idn(self):
		return self.query("*IDN?").strip()

	def tscale(self, scale):
		self.write(f"HORIZONTAL:SCALE {scale}")

	def vscale(self, scale):
		self.write(f"CH1:SCALE {scale}")

	def single(self, points=10000):
		self.write("ACQUIRE:STATE OFF")
		self.write("SELECT:CH1 ON")
		self.write(f"HORIZONTAL:RECORDLENGTH {points}")
		self.write("ACQUIRE:MODE SAMPLE")
		self.write("ACQUIRE:STOPAFTER SEQUENCE")
		self.write("ACQUIRE:STATE ON")

		self.query("*OPC?")
		print("Single completado")

	def extract(self):
		self.write("HEADER 0")
		self.write("DATA:SOURCE CH1")
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


def main():
	name = "USB0::0x0699::0x0408::C011271::INSTR"
	rm = pyvisa.ResourceManager()
	inst = rm.open_resource(name)

	inst.timeout = 30000
	inst.chunk_size = 1024 * 1024

	osci = Oscilloscope(inst)

	print(osci.idn())

	osci.tscale(10e-6)  # 10 µs/div
	osci.vscale(0.5)     # 500 mV/div

	osci.single(points=10_000)

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