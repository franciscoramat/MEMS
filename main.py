import pyvisa
from gf import GF


def main():
	rm = pyvisa.ResourceManager()
	gf = GF(rm.open_resource('USB0::0x1AB1::0x0641::DG4E163251533::INSTR'))


if __name__ == "__main__":
	main()