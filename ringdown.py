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
        amplitude = 1.5
        points = 1_000_000
        window = .5

        rm = pyvisa.ResourceManager()

        gf = GF(rm.open_resource(
            "USB0::0x1AB1::0x0641::DG4E163251533::INSTR",
            timeout=5000
        ))

        lockin = LI(rm.open_resource(
            "ASRL7::INSTR",
            write_termination="\r",
            read_termination="\n",
            timeout=5000
        ))    
        lockin.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)


        osci = Oscilloscope(rm.open_resource
            ("USB0::0x0699::0x0408::C011271::INSTR",
            timeout=5000
        ))
        osci.vscale(3e-3)
        osci.vscale(150e-3, 2)
        osci.position(0, 2)
        osci.offset(0, 2)
        osci.tscale(window / 10)


        sweeper = Sweeper(gf, lockin)


        sweeper.run(
            start=63e3,
            end=69e3,
            N=40,
            amplitude=amplitude,
            direction="forwards",
            plotlive=True,
            stall=True
        )
        sweeper.save()

        Timer(0.4, gf.output, args=("OFF",)).start()
        osci.single(points=points)

        t, v = osci.extract()
        _, v2 = osci.extract(2)
        fig = osci.plot(t,v, v2)


        date = datetime.now().strftime("%d-%m-%H%M")    
        np.savetxt(
            f"ringdown-{date}.csv",
            np.column_stack((t, v, v2)),
            delimiter=",",
            header="Tiempo (s),CH1 (V),CH2 (V)",
            comments=""
        )

        fig.savefig(f'ringdown_{date}.png')


    finally:

        gf.output("OFF")
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()
