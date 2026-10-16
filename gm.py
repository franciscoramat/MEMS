import time
import pyvisa 

class GM:
	def __init__(self, inst):
			self.inst = inst
			self.write = inst.write
			self.query = inst.query
			inst.baud_rate = 57600
			inst.data_bits = 7
			inst.parity = pyvisa.constants.Parity.odd
			inst.stop_bits = pyvisa.constants.StopBits.one
			inst.write_termination = "\n"
			inst.read_termination = "\n"
			inst.write("UNIT 2")
			
	def read(self):
	    self.inst.write("RDGFIELD?")
	    return float(self.inst.read_bytes(30, break_on_termchar=True).decode().strip())
