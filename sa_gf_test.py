import pyvisa

from sa import SA, hz


def main():
    sa_name = "USB0::0x1AB1::0x0960::DSA8A163250968::INSTR"
    frequency = (63e3)*3
    span = 10e3

    rm = pyvisa.ResourceManager()
    sa = SA(rm.open_resource(sa_name))

    try:
        sa.center_f(frequency)
        sa.span(span)
        sa.ref_level(-20)
        sa.y_scale(.1)
        sa.rbw(1e1)
        sa.vbw(1e1)
        sa.continuous("ON")
        sa.sweep()

        data = sa.trace()
        start = frequency - span / 2
        peak_frequency, peak_power = sa.peak(data, start, span)

        print(f"Pico: {peak_power:.2f} dBm a {hz(peak_frequency)}")
    finally:
        sa.inst.close()
        rm.close()


if __name__ == "__main__":
    main()
