import pyvisa
import time
from psu import PSU


def main():
	try: 
		rm = pyvisa.ResourceManager()
		psu = PSU(rm.open_resource('GPIB0::1::INSTR'))
		psu.CC()
		psu.set_I(5, 20)
		time.sleep(1)
		psu.output('ON')
		time.sleep(2)
		print(psu.read_I())
		time.sleep(2)

	finally:
		psu.output('OFF')

if __name__ == "__main__":
	main()