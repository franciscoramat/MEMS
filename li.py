import time

class LI: 
    upbound = 12000
    lowbound = 1000

    def __init__(self, inst):
        self.inst = inst
        self.write = inst.write
        self.query = inst.query
        self.sens = int(self.query("SEN"))

    def asense(self, x, y):
        r = (x**2 + y**2)**0.5
        
        if r > upbound:
        	self.sens += 1
        	return True
        if r < lowerbound:
        	self.sens -= 1
        	return True
        # self.write("AS")
        # inst.read_bytes(1)


    def xy(self):
        x, y = self.query("XY").strip().split(";")
        
        if self.asense(x, y):
        	time.sleep(2)
        	x, y = self.query("XY").strip().split(";")
        
        return int(x), int(y)