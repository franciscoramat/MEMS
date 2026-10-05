import pyvisa

def main():
	rm = pyvisa.ResourceManager()
	print(rm.list_resources())


if __name__ == "__main__":
	main()