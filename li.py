import time
class LI:
	def __init__(self, inst):
		self.inst = inst
		self.write = inst.write
		self.query = inst.query
		self.write('SEN 6')
		time.sleep(10)

	def x(self):
		return int(self.query("X"))

	def y(self):
		return int(self.query("Y"))

	def xy(self):
		return self.x(), self.y()
