import pyvisa
import time
from gf import GF


def main():
	rm = pyvisa.ResourceManager()
	gf = GF(rm.open_resource('USB0::0x1AB1::0x0641::DG4E163251533::INSTR'))
	gf.set_v(2)
	
	time.sleep(1) 
	gf.output("ON")
	time.sleep(1) 
	gf.set_v(3)
	time.sleep(2)
	gf.sweep_f(1e+2, 1e+)
	gf.output("OFF")
	
if __name__ == "__main__":
	main()