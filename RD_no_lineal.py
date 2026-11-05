import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft

###################################################################
# Parámetros del ring-down


A0 = 1.0

gamma = 2.0       # tasa de decaimiento [1/s]

f0 = 65e3         # frecuencia lineal [Hz]
w0 = 2*np.pi*f0   # frecuencia angular [rad/s]

f_initial = 69e3  # frecuencia inicial sobre la curva no lineal [Hz]

phi0 = 0.0

###################################################################
# Elegimos beta para obtener 69 kHz al inicio
#
# f_inst(0) = f0 + 3*beta*A0^2/(16*pi*w0)
#
# Por lo tanto:
#
# beta = (f_initial-f0) * 16*pi*w0 / (3*A0^2)


beta = (
    (f_initial - f0)
    * 16*np.pi*w0
    / (3*A0**2)
)

print("beta =", beta)

###################################################################
# Tiempo


fs = 500e3       # frecuencia de muestreo, 500 [kHz]
T = 3.0          # duración del ring-down [s], N_puntos * (1/fs)  

t = np.arange(0, T, 1/fs)

###################################################################
# Amplitud (envolvente del RD)

A = A0 * np.exp(-gamma*t)       # decaimiento exponencial de la amplitud


###################################################################
# Fase no lineal
#
# phi(t) = phi0 +
#          3 beta A0^2/(16 gamma w0)
#          (1-exp(-2 gamma t))


phi = (
    phi0
    + 3*beta*A0**2/(16*gamma*w0)
    * (1 - np.exp(-2*gamma*t))
)


###################################################################
# Señal de ring-down


V = A * np.cos(w0*t + phi)


###################################################################
# Frecuencia instantánea


w_inst = (
    w0
    + 3*beta*A0**2/(8*w0)
    * np.exp(-2*gamma*t)
)

f_inst = w_inst/(2*np.pi)


###################################################################
# Gráficos
#

fig, ax = plt.subplots(
    2, 1,
    figsize=(11, 8),
    sharex=True
)



# Ring-down


ax[0].plot(
    t,
    V,
    color='black',
    lw=0.8
)

ax[0].plot(
    t,
    A,
    'r--',
    alpha=0.7,
    label='Envolvente'
)

ax[0].plot(
    t,
    -A,
    'r--',
    alpha=0.7
)

ax[0].set_ylabel('V(t)')
ax[0].set_title('Ring-down de un oscilador Duffing')
ax[0].grid(True)
ax[0].legend()


# Frecuencia instantánea


ax[1].plot(
    t,
    f_inst/1e3,
    color='blue',
    lw=2
)

ax[1].axhline(
    65,
    color='gray',
    linestyle='--',
    label='65 kHz'
)

ax[1].axhline(
    69,
    color='red',
    linestyle='--',
    label='69 kHz'
)

ax[1].set_xlabel('Tiempo [s]')
ax[1].set_ylabel('Frecuencia [kHz]')
ax[1].set_ylim(64, 70)
ax[1].grid(True)
ax[1].legend()

plt.tight_layout()
plt.savefig("RD.jpg", dpi=150) 
plt.show()



# STFT


f, tt, Zxx = stft(
    V,
    fs=fs,
    window='hann',   #ventana de Hann para analizar la señal en cada segmento temporal.
    nperseg=8192, #cuántas muestras tiene cada ventana.
    noverlap=7000,#cuántas muestras comparte una ventana con la siguiente.
    boundary=None
)

S = np.abs(Zxx)



# Espectrograma


plt.figure(figsize=(11, 7))

plt.pcolormesh(
    tt,
    f/1e3,
    S,
    shading='gouraud',
    cmap='viridis'
)

# Superponer frecuencia instantánea
plt.plot(
    t,
    f_inst/1e3,
    color='cyan',
    lw=2,
    label=r'$f_{\mathrm{inst}}(t)$'
)

plt.ylim(63, 71)

plt.xlabel('Tiempo [s]')
plt.ylabel('Frecuencia [kHz]')

plt.title('STFT del ring-down Duffing')

plt.colorbar(
    label='|STFT|'
)

plt.legend()

plt.tight_layout()

plt.savefig("STFT.jpg", dpi=150) 
plt.show()