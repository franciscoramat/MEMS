import pyvisa
from li import LI

rm = pyvisa.ResourceManager()

inst = rm.open_resource(
    "ASRL10::INSTR",
    write_termination="\r",
    read_termination="\n",
)

lockin = LI(inst)
x, y = lockin.xy()
print(f"X, Y = {x}V, {y}V")
print(f"r = {(x**2 + y**2)**(.5)}V")