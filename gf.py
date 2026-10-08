import time
class GF:
	def __init__(self, inst):
			self.inst = inst

			self.write = inst.write
			self.query = inst.query
			
			self.write('SOUR1:FUNC SIN')	
			self.output("OFF")

	def output(self, state):
		self.write(f':OUTP1 {state}')

	def set_v(self, voltage):
		self.write(f'SOUR1:VOLT {voltage}')

	def set_f(self, frequency):
		self.write(f'SOUR1:FREQ {frequency}')

	def sweep_f(self, start, end, N):
	    for i in range(N):
	        time.sleep(1)
	        f = start + i * (end - start) / (N - 1)
	        self.set_f(f)
