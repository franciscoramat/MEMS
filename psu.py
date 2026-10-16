import time
class PSU:
	def __init__(self, inst):
		self.inst = inst
		self.write = inst.write
		self.query = inst.query

		self.write('OUTP OFF')

	def CV(self):
		self.write('FUNC:MODE VOLT')

	def CC(self):
		self.write('FUNC:MODE CURR')

	def output(self, state):
		self.write(f'OUTP {state}')

	def set_V(self, v, imax):
		self.write(f'CURR {imax}')
		self.write(f'VOLT {v}')

	def set_I(self, i, vmax):
		self.write(f'VOLT {vmax}')
		self.write(f'CURR {i}')

	def read_V(self):
	    return float(self.query('MEAS:VOLT?'))

	def read_I(self):
	    return float(self.query('MEAS:CURR?'))