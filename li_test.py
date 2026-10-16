import pyvisa
from li import LI

rm = pyvisa.ResourceManager()

inst = rm.open_resource(
    "ASRL5::INSTR",
    write_termination="\r",
    read_termination="\n",
)

lockin = LI(inst)
lockin.asense()

print("X, Y =", lockin.xy())