import time
import pyvisa 

class LI:

    sensitivities = [
    100e-9, 300e-9, 1e-6, 3e-6,
    10e-6, 30e-6, 100e-6, 300e-6,
    1e-3, 3e-3, 10e-3, 30e-3,
    100e-3, 300e-3, 1, 3
    ]
    upbound = 10000
    lowbound = 1000

    def __init__(self, inst):
        self.inst = inst
        self.write = inst.write
        self.query = inst.query
        self.read = inst.read
        self.inst.flow_control = pyvisa.constants.ControlFlow.rts_cts
        self.write("G 0") # desactiva VERNIER
        time.sleep(.5)
        
        #self.write("IE 0") # usa la entrada REF IN

    def asense(self, x, y):
        r = (int(x)**2 + int(y)**2)**0.5

        if r > self.upbound and self.sens < 15:
            self.sens += 1
        elif r < self.lowbound and self.sens > 0:
            self.sens -= 1
        else:
            return False

        self.write(f"SEN {self.sens}")
        print(f"ajustando SENS... SENS = {self.sens}, x = {x}; y = {y}")
        return True

    def xy(self):
        x, y = self.query("XY").strip().split(";")
        self.sens = int(self.query("SEN"))
        tries = 0

        while tries < 16 and self.asense(x, y):
            time.sleep(2)
            x, y = self.query("XY").strip().split(";")
            tries += 1

        scale = self.sensitivities[self.sens]

        return int(x) * scale / 10000, int(y) * scale / 10000

        return int(x), int(y)