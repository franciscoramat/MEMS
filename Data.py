import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgb
from scipy import signal
from scipy.ndimage import gaussian_filter
from scipy.optimize import curve_fit


class Sweep:
    def __init__(self, filename):
        self.filename = Path(filename)

        with self.filename.open(newline="", encoding="latin-1") as file:
            lines = file.readlines()

        self.excitation = lines[0].strip()
        self.amplitude = float(self.excitation.split(":")[1].split()[0])
        self.resonance_window = None

        header = 1
        if lines[1].startswith("Ventana de resonancia"):
            values = lines[1].split(":")[1].split(",")
            self.resonance_window = tuple(float(value) for value in values)
            header = 2

        reader = csv.DictReader(lines[header:])
        self.data = [
            (
                float(row["Frecuencia (Hz)"]),
                float(row["X (V)"]),
                float(row["Y (V)"]),
            )
            for row in reader
            if row.get("X (V)") is not None
        ]

        if not self.data:
            raise ValueError("El archivo no contiene datos de barrido")

        self.fig = None


    def subtract_background(self, resonance_window, degree=2):
        ff, xx, yy = np.array(self.data).T
        start, end = resonance_window
        background = (ff < start) | (ff > end)
        background[:3] = False

        x_fit = np.polyfit(ff[background], xx[background], degree)
        y_fit = np.polyfit(ff[background], yy[background], degree)

        xx = xx - np.polyval(x_fit, ff)
        yy = yy - np.polyval(y_fit, ff)

        corrected = object.__new__(Sweep)
        corrected.filename = self.filename
        corrected.excitation = self.excitation
        corrected.amplitude = self.amplitude
        corrected.resonance_window = resonance_window
        corrected.data = list(zip(ff[3:], xx[3:], yy[3:]))
        corrected.fig = None

        return corrected


    def subtract_reference_background(
        self,
        reference_frequency,
        reference_x,
        reference_y,
        resonance_window,
    ):
        ff, xx, yy = np.array(self.data).T
        start, end = resonance_window
        resonance = (ff >= start) & (ff <= end)
        xx = xx - self.amplitude * np.interp(
            ff, reference_frequency, reference_x
        )
        yy = yy - self.amplitude * np.interp(
            ff, reference_frequency, reference_y
        )
        xx[~resonance] = 0
        yy[~resonance] = 0

        corrected = object.__new__(Sweep)
        corrected.filename = self.filename
        corrected.excitation = self.excitation
        corrected.amplitude = self.amplitude
        corrected.resonance_window = resonance_window
        corrected.data = list(zip(ff, xx, yy))
        corrected.fig = None

        return corrected


    def split_bidirectional(self):
        frequencies = np.array([frequency for frequency, _, _ in self.data])
        turning_point = int(np.argmax(frequencies))

        if turning_point == 0 or turning_point == len(self.data) - 1:
            raise ValueError("El barrido no contiene ida y vuelta")

        forward = object.__new__(Sweep)
        backward = object.__new__(Sweep)

        for branch, branch_data in (
            (forward, self.data[:turning_point + 1]),
            (backward, self.data[turning_point:]),
        ):
            branch.filename = self.filename
            branch.excitation = self.excitation
            branch.amplitude = self.amplitude
            branch.resonance_window = None
            branch.data = list(branch_data)
            branch.fig = None

        return forward, backward


    @classmethod
    def stitch(cls, sweeps, increasing=True):
        if not sweeps:
            raise ValueError("No hay barridos para unir")

        stitched = object.__new__(Sweep)
        stitched.filename = sweeps[0].filename
        stitched.excitation = sweeps[0].excitation
        stitched.amplitude = sweeps[0].amplitude
        stitched.resonance_window = None
        stitched.fig = None
        stitched.data = []

        for sweep in sweeps:
            for point in sweep.data:
                if not stitched.data:
                    stitched.data.append(point)
                    continue

                previous_frequency = stitched.data[-1][0]
                if (increasing and point[0] > previous_frequency) or (
                    not increasing and point[0] < previous_frequency
                ):
                    stitched.data.append(point)

        return stitched


    def subtract_background_bidirectional(
        self, forward_window, backward_window
    ):
        forward, backward = self.split_bidirectional()

        resonance_window = (
            min(forward_window[0], backward_window[0]),
            max(forward_window[1], backward_window[1]),
        )

        return (
            forward.subtract_background(resonance_window),
            backward.subtract_background(resonance_window),
        )


    def save(self, filename):
        start, end = self.resonance_window

        with open(filename, "w", newline="", encoding="latin-1") as file:
            file.write(f"{self.excitation}\n")
            file.write(f"Ventana de resonancia (Hz): {start}, {end}\n")

            writer = csv.writer(file)
            writer.writerow(
                ["Frecuencia (Hz)", "X (V)", "Y (V)", "R (V)", "Fase (rad)"]
            )
            writer.writerows(
                (f, x, y, np.hypot(x, y), np.arctan2(y, x))
                for f, x, y in self.data
            )


    def plot(self, axes=None, color=None, label=None,
             linewidth=1.2, alpha=0.8, marker=""):

        if axes is None:
            self.fig, axes = plt.subplots(
                3, 1, sharex=True, figsize=(6, 5)
            )

        ff, xx, yy = np.array(self.data).T
        rr = np.hypot(xx, yy)

        for ax, values in zip(axes, (xx, yy, rr)):
            ax.plot(
                ff, values,
                color=color,
                label=label,
                linewidth=linewidth,
                alpha=alpha,
                marker=marker
            )

        return axes


class Ringdown:
    def __init__(self, filename):
        self.filename = Path(filename)
        raw_data = np.loadtxt(
            self.filename,
            delimiter=",",
            skiprows=1,
        )

        if raw_data.ndim != 2 or raw_data.shape[1] != 3:
            raise ValueError(
                "El archivo de ring-down debe tener tiempo, CH1 y CH2."
            )

        self.raw_time = raw_data[:, 0]
        self.channel_1 = raw_data[:, 1]
        self.channel_2 = raw_data[:, 2]

        self.reconstructed_time = None
        self.reconstructed_signal = None
        self.time = None
        self.signal = None
        self.filtered_signal = None
        self.envelope = None
        self.spectrogram_time = None
        self.spectrogram_frequency = None
        self.spectrogram_power = None
        self.spectrogram_decibels = None
        self.spectrogram_frequency_limits = None
        self.release_time = None
        self.switch_time = None
        self.channel_2_scale = None
        self.noise_floor = None
        self.noise_limit = None
        self.filter_transient = None
        self.decay_start_time = None
        self.decay_start_time_error = None
        self.fit_mask = None
        self.damping = None
        self.damping_error = None
        self.fit_curve = None
        self.reconstructed_filename = None
        self.fig = None

    def reconstruct(self, release_time, save=True):
        release_index = np.argmin(
            np.abs(self.raw_time - release_time)
        )
        self.release_time = self.raw_time[release_index]
        self.switch_time = self.release_time

        channel_1_minimum = np.min(self.channel_1)
        channel_1_maximum = np.max(self.channel_1)
        channel_1_saturated = (
            (self.channel_1 == channel_1_minimum)
            | (self.channel_1 == channel_1_maximum)
        )

        before_switch = self.raw_time < self.switch_time
        channel_2_peak = np.max(np.abs(self.channel_2[before_switch]))
        if channel_2_peak == 0:
            raise ValueError("CH2 no permite reconstruir la señal.")

        channel_1_limit = max(
            abs(channel_1_minimum),
            abs(channel_1_maximum),
        )
        self.channel_2_scale = channel_1_limit / channel_2_peak
        scaled_channel_2 = self.channel_2_scale * self.channel_2

        after_switch = ~before_switch
        usable_channel_1 = after_switch & ~channel_1_saturated
        cleaned_channel_1 = self.channel_1.copy()
        cleaned_channel_1[after_switch] = np.interp(
            self.raw_time[after_switch],
            self.raw_time[usable_channel_1],
            self.channel_1[usable_channel_1],
        )

        self.reconstructed_time = self.raw_time - self.release_time
        self.reconstructed_signal = np.where(
            before_switch,
            scaled_channel_2,
            cleaned_channel_1,
        )
        self.time = self.reconstructed_time[after_switch]
        self.signal = self.reconstructed_signal[after_switch]

        if save:
            self.reconstructed_filename = self.filename.with_name(
                f"{self.filename.stem}_reconstruida.csv"
            )
            np.savetxt(
                self.reconstructed_filename,
                np.column_stack((
                    self.reconstructed_time,
                    self.reconstructed_signal,
                )),
                delimiter=",",
                header="Tiempo (s),Señal reconstruida (V)",
                comments="",
            )

        return self

    def analyze(
        self,
        frequency_band,
        fit_method="exponential",
        decay_start_time=None,
        spectrogram_window=20e-3,
        spectrogram_overlap=0.9,
        spectrogram_peak_range=15,
    ):
        if self.signal is None:
            raise ValueError("Primero hay que reconstruir la señal.")

        low_frequency, high_frequency = frequency_band
        sample_interval = np.median(np.diff(self.time))
        sample_rate = 1 / sample_interval
        nyquist_frequency = sample_rate / 2

        if not 0 < low_frequency < high_frequency < nyquist_frequency:
            raise ValueError("La banda de frecuencias no es válida.")
        if spectrogram_window <= 0:
            raise ValueError("spectrogram_window debe ser positivo.")
        if not 0 <= spectrogram_overlap < 1:
            raise ValueError("spectrogram_overlap debe estar entre 0 y 1.")
        if spectrogram_peak_range <= 0:
            raise ValueError("spectrogram_peak_range debe ser positivo.")

        spectrogram_samples = round(spectrogram_window / sample_interval)
        if not 1 < spectrogram_samples <= len(self.signal):
            raise ValueError("spectrogram_window no es compatible con la señal.")
        spectrogram_overlap_samples = round(
            spectrogram_samples * spectrogram_overlap
        )
        frequency, time, spectrum = signal.stft(
            self.signal,
            fs=sample_rate,
            window="hann",
            nperseg=spectrogram_samples,
            noverlap=spectrogram_overlap_samples,
            boundary="zeros",
            padded=True,
        )
        power = np.abs(spectrum) ** 2
        frequency_mask = (
            (frequency >= low_frequency)
            & (frequency <= high_frequency)
        )
        self.spectrogram_time = time
        self.spectrogram_frequency = frequency[frequency_mask]
        self.spectrogram_power = power[frequency_mask]
        maximum_power = np.max(self.spectrogram_power)
        self.spectrogram_decibels = 10 * np.log10(
            self.spectrogram_power / maximum_power
        )
        visible_frequency = self.spectrogram_frequency[
            np.max(self.spectrogram_decibels, axis=1)
            >= -spectrogram_peak_range
        ]
        frequency_margin = 0.5e3
        self.spectrogram_frequency_limits = (
            max(low_frequency, visible_frequency[0] - frequency_margin),
            min(high_frequency, visible_frequency[-1] + frequency_margin),
        )

        filter_sections = signal.butter(
            4,
            (low_frequency, high_frequency),
            btype="bandpass",
            fs=sample_rate,
            output="sos",
        )
        self.filtered_signal = signal.sosfiltfilt(
            filter_sections,
            self.signal,
        )
        self.envelope = np.abs(signal.hilbert(self.filtered_signal))

        tail_size = max(1, len(self.envelope) // 10)
        self.noise_floor = np.median(self.envelope[-tail_size:])
        self.noise_limit = 3 * self.noise_floor
        self.filter_transient = 3 / low_frequency
        analysis_mask = (
            (self.time >= self.filter_transient)
            & (self.envelope >= self.noise_limit)
        )

        if np.count_nonzero(analysis_mask) < 4:
            raise ValueError("No hay suficientes puntos para ajustar.")

        if decay_start_time is None:
            raise ValueError("Hay que indicar decay_start_time manualmente.")
        if not self.time[0] <= decay_start_time <= self.time[-1]:
            raise ValueError("decay_start_time está fuera del intervalo.")
        self.decay_start_time = decay_start_time
        self.decay_start_time_error = None

        self.fit_mask = analysis_mask & (self.time >= self.decay_start_time)
        if np.count_nonzero(self.fit_mask) < 3:
            raise ValueError("No hay suficientes puntos después del inicio del decaimiento.")

        if fit_method == "exponential":
            def exponential_decay(time, amplitude, damping, offset):
                return amplitude * np.exp(-damping * time) + offset

            fit_time = self.time[self.fit_mask] - self.decay_start_time
            fit_envelope = self.envelope[self.fit_mask]
            initial_amplitude = max(
                fit_envelope[0] - self.noise_floor,
                0,
            )
            initial_damping = 1 / fit_time[-1]
            parameters, covariance = curve_fit(
                exponential_decay,
                fit_time,
                fit_envelope,
                p0=(initial_amplitude, initial_damping, self.noise_floor),
                bounds=(0, np.inf),
            )
            amplitude, self.damping, offset = parameters
            self.fit_curve = np.full_like(self.time, np.nan)
            after_decay_start = self.time >= self.decay_start_time
            self.fit_curve[after_decay_start] = exponential_decay(
                self.time[after_decay_start] - self.decay_start_time,
                amplitude,
                self.damping,
                offset,
            )
            self.damping_error = np.sqrt(covariance[1, 1])

        elif fit_method == "logarithmic":
            fit_time = self.time[self.fit_mask] - self.decay_start_time
            coefficients, covariance = np.polyfit(
                fit_time,
                np.log(self.envelope[self.fit_mask]),
                1,
                cov=True,
            )
            slope, intercept = coefficients
            self.damping = -slope
            self.damping_error = np.sqrt(covariance[0, 0])
            self.fit_curve = np.full_like(self.time, np.nan)
            after_decay_start = self.time >= self.decay_start_time
            elapsed_time = self.time[after_decay_start] - self.decay_start_time
            self.fit_curve[after_decay_start] = np.exp(
                intercept - self.damping * elapsed_time
            )

        else:
            raise ValueError(
                "fit_method debe ser 'exponential' o 'logarithmic'."
            )

        return self

    def plot(self, trace_style="lines"):
        if trace_style not in ("density", "lines"):
            raise ValueError("trace_style debe ser 'density' o 'lines'.")

        plt.rcParams.update({
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.grid": False,
            "axes.edgecolor": "#273142",
            "axes.labelcolor": "#273142",
            "axes.linewidth": 1.2,
            "xtick.color": "#273142",
            "ytick.color": "#273142",
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": True,
            "ytick.right": True,
            "xtick.major.size": 6,
            "ytick.major.size": 6,
            "xtick.major.width": 1.2,
            "ytick.major.width": 1.2,
            "text.color": "#273142",
            "font.size": 14,
            "axes.labelsize": 16,
            "xtick.labelsize": 13,
            "ytick.labelsize": 13,
            "legend.fontsize": 13,
            "figure.dpi": 160,
        })

        def density_phosphor(axis, time, signal, color):
            density, time_edges, signal_edges = np.histogram2d(
                time,
                signal,
                bins=(1_000, 300),
            )
            density = gaussian_filter(density.T, sigma=0.8)
            density /= density.max()

            image = np.empty((*density.shape, 4))
            image[:, :, :3] = to_rgb(color)
            image[:, :, 3] = np.where(
                density > 0,
                0.18 + 0.72 * density ** 0.70,
                0,
            )

            axis.imshow(
                image,
                origin="lower",
                aspect="auto",
                extent=(
                    time_edges[0],
                    time_edges[-1],
                    signal_edges[0],
                    signal_edges[-1],
                ),
                interpolation="bilinear",
                zorder=1,
            )

        def line_phosphor(axis, time, signal, color):
            sample_step = max(1, len(time) // 100_000)
            points = np.column_stack((time[::sample_step], signal[::sample_step]))
            segments = np.stack((points[:-1], points[1:]), axis=1)
            axis.add_collection(LineCollection(
                segments,
                colors=color,
                linewidths=0.18,
                alpha=0.55,
                antialiaseds=True,
                zorder=1,
            ))
            axis.set_xlim(time[0], time[-1])
            axis.set_ylim(np.min(signal), np.max(signal))

        def plot_signal(axis, time, signal, color):
            if trace_style == "density":
                density_phosphor(axis, time, signal, color)
            else:
                line_phosphor(axis, time, signal, color)

        def style_axis(axis):
            axis.tick_params(
                axis="both",
                which="major",
                direction="in",
                top=True,
                right=True,
                length=6,
                width=1.2,
            )

        colors = {
            "channel_1": "#C2410C",
            "channel_2": "#0891B2",
            "filtered": "#2563EB",
            "fit": "#DC2626",
        }

        panel_count = 3 if self.spectrogram_power is not None else 2
        figure_height = 7.2 if panel_count == 3 else 4.8
        self.fig, axes = plt.subplots(
            panel_count,
            1,
            figsize=(6.5, figure_height),
            constrained_layout=True,
        )
        if panel_count == 3:
            axes[2].sharex(axes[1])
        raw_time = self.raw_time * 1e3
        plot_signal(
            axes[0],
            raw_time,
            self.channel_1 * 1e3,
            colors["channel_1"],
        )
        axes[0].set_ylabel("CH1 (mV)", color=colors["channel_1"])
        axes[0].tick_params(axis="y", colors=colors["channel_1"])
        channel_2_axis = axes[0].twinx()
        plot_signal(
            channel_2_axis,
            raw_time,
            self.channel_2,
            colors["channel_2"],
        )
        channel_2_axis.set_ylabel("CH2 (V)", color=colors["channel_2"])
        channel_2_axis.tick_params(axis="y", colors=colors["channel_2"])
        axes[0].set_xlabel("Tiempo (ms)")
        axes[0].set_xlim(raw_time[0], raw_time[-1])
        style_axis(axes[0])
        channel_2_axis.grid(False)

        if self.filtered_signal is not None:
            plot_signal(
                axes[1],
                self.time * 1e3,
                self.filtered_signal * 1e3,
                colors["filtered"],
            )
            if self.fit_curve is not None:
                decay_mask = self.time >= self.decay_start_time
                axes[1].plot(
                    self.time[decay_mask] * 1e3,
                    self.fit_curve[decay_mask] * 1e3,
                    color=colors["fit"],
                    linewidth=2.0,
                )
            axes[1].set_ylabel("Señal filtrada (mV)")
            axes[1].set_xlabel("Tiempo desde la liberación (ms)")
            style_axis(axes[1])

        if self.spectrogram_power is not None:
            spectrogram = axes[2].pcolormesh(
                self.spectrogram_time * 1e3,
                self.spectrogram_frequency * 1e-3,
                self.spectrogram_decibels,
                shading="auto",
                cmap="turbo",
            )
            axes[2].set_ylim(
                np.array(self.spectrogram_frequency_limits) * 1e-3
            )
            axes[2].set_xlim(axes[1].get_xlim())
            axes[2].set_ylabel("Frecuencia (kHz)")
            axes[2].set_xlabel("Tiempo desde la liberación (ms)")
            style_axis(axes[2])

        return axes


