class GF:
	def __init__(self, inst):
			self
			self.write('SOUR1:FUNC SIN')	
			self.write(":SOUR1:FREQ 2000")
			self.write(":SOUR1:VOLT 2")
			self.write(":OUTP1 ON")

	def output(self, state):
		self.write(f'OUTP1: {state}')
