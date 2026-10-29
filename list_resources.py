import pyvisa

def main():
	rm = pyvisa.ResourceManager()
	print(rm.list_resources())


if __name__ == "__main__":
	main()



#CONFIGURACIÓN COMPU DE SANTI
# Todos juntos hay  'USB0::0x1AB1::0x0641::DG4E163251533::INSTR', 'USB0::0x0699::0x0408::C011271::INSTR', 
# 'ASRL3::INSTR', 'ASRL4::INSTR', 'ASRL5::INSTR', 'ASRL6::INSTR', 'ASRL10::INSTR'

# Lock In: ASRL10::INSTR
# Osciloscopio: USB0::0x0699::0x0408::C011271::INSTR
# GAF: USB0::0x1AB1::0x0641::DG4E163251533::INSTR