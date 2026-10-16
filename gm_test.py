import pyvisa
import time
from gm import GM


def main():


	rm = pyvisa.ResourceManager()
	gm = GM(rm.open_resource('ASRL6::INSTR'))
	print(gm.read())
	gm.inst.write("ZPROBE")

if __name__ == "__main__":
	main()