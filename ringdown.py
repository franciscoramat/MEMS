import pyvisa
import matplotlib.pyplot as plt
import time
import numpy as np
from datetime import datetime
from threading import Timer

from gf import GF
from li import LI
from sweeper import Sweeper
from oscilloscope import Oscilloscope 



def main():

    try:
        amplitude = 1.1
        points = 1_000_000
        window = 1

        rm = pyvisa.ResourceManager()

        gf = GF(rm.open_resource(
            "USB0::0x1AB1::0x0641::DG4E163251533::INSTR"
        ))

        lockin = LI(rm.open_resource(
            "ASRL7::INSTR",
            write_termination="\r",
            read_termination="\n",
        ))    
        lockin.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)


        osci = Oscilloscope(rm.open_resource
            ("USB0::0x0699::0x0408::C011271::INSTR"
        ))
        osci.vscale(10e-3)
        osci.vscale(100e-3, 2)
        osci.tscale(window / 10)

        sweeper = Sweeper(gf, lockin)


        sweeper.run(
            start=63e3,
            end=67.4e3,
            N=30,
            amplitude=amplitude,
            direction="forwards",
            plotlive=True,
            stall=True
        )
        sweeper.save()

        Timer(0.5, gf.output, args=("OFF",)).start()
        osci.single(points=points)

        t, v = osci.extract()
        _, v2 = osci.extract(2)
        osci.plot(t,v)
        osci.plot(t,v2)

        date = datetime.now().strftime("%d-%m-%H%M")    
        np.savetxt(
            f"ringdown-{date}.csv",
            np.column_stack((t, v, v2)),
            delimiter=",",
            header="Tiempo (s),CH1 (V),CH2 (V)",
            comments=""
        )



    finally:

        gf.output("OFF")
        plt.ioff()
        plt.show()

if __name__ == "__main__":
    main()
