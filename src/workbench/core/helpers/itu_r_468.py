import numpy as np
import logging
from scipy.signal import lfilter, lfilter_zi, firwin2

LOGGER = logging.getLogger(__name__)

class ITUR468Filter:
    def __init__(self, fs=48000, numtaps=513, window='tukey'):
        self._fs = fs
        self._numtaps:int = numtaps
        self._window = window
        self.coeffs = self.design_itu_r_468_fir()
        self.zi = lfilter_zi(self.coeffs, 1.0)
        LOGGER.debug(f'First initial conditions of size {self.zi.size}')

    @property
    def numtaps(self) -> int:
        return self._numtaps
    
    @numtaps.setter
    def numtaps(self, taps: int):
        if taps % 2 == 0:
            self._numtaps = taps + 1
        else:
            self._numtaps = taps

        self.design_itu_r_468_fir()
        self.zi = lfilter_zi(self.coeffs, 1.0)

    @property
    def fs(self) -> int:
        return self._fs
    
    @fs.setter
    def fs(self, nfs: int):
        self._fs = nfs
        self.design_itu_r_468_fir()
        self.zi = lfilter_zi(self.coeffs, 1.0)

    def design_itu_r_468_fir(self):
        # Tabla oficial ITU-R BS.468-4 (frecuencia en Hz, ganancia en dB)
        official_table = np.array([
            [31.5, -29.9],
            [63, -23.9],
            [100, -19.8],
            [200, -13.8],
            [400, -7.8],
            [800, -1.9],
            [1000, 0.0],
            [2000, 5.6],
            [3150, 9.0],
            [4000, 10.5],
            [5000, 11.7],
            [6300, 12.2],
            [7100, 12.0],
            [8000, 11.4],
            [9000, 10.1],
            [10000, 8.1],
            [12500, 0.0],
            [14000, -5.3],
            [16000, -11.7],
            [20000, -22.2],
        ])
        
        f_ext = np.concatenate(([0], official_table[:, 0], [self._fs / 2]))
        g_ext_db = np.concatenate(([-60], official_table[:, 1], [-60]))
        g_ext = 10 ** (g_ext_db / 20)
        f_norm = f_ext / (self.fs / 2)
        LOGGER.debug(f'ITUR468Filter: creating ITUR468 filter with sample rate {self.fs} and {self.numtaps} coefficients')
        h = firwin2(self._numtaps, f_norm, g_ext, window=self._window)
        return h

    def apply_itu_r_468_fir(self, signal):
        # LOGGER.debug(f'First initial conditions of shape {self.zi.shape}')
        # LOGGER.debug(f'Coeffs shape {self.coeffs.shape}')
        signal = np.asarray(signal).flatten()   # Need to flatten signal shape for lfilter
        # LOGGER.debug(f'signal shape {signal.shape}')
        try:
            filtered, self.zi = lfilter(self.coeffs, 1.0, signal, zi=self.zi)
        except ValueError as e:
            LOGGER.error(f'Filter failed')
        # LOGGER.debug(f'Initial conditions : {self.zi}')
        return filtered.reshape(-1, 1)

if __name__ == "__main__":
    import matplotlib.pyplot as plt

    filtro = ITUR468Filter()
    fs = 48000
    bloque_size = 512
    num_bloques = 10
    t = np.linspace(0, bloque_size * num_bloques / fs, bloque_size * num_bloques, endpoint=False)

    plt.figure(figsize=(10, 6))
    for i in range(num_bloques):
        bloque = np.sin(2 * np.pi * 6000 * t[:bloque_size])
        salida = filtro.apply_itu_r_468_fir(bloque)

        plt.plot(t[i * bloque_size:(i + 1) * bloque_size], salida, label=f"Bloque {i+1}")
        plt.plot(t[i * bloque_size:(i + 1) * bloque_size], bloque, label=f"Bloque {i+1}", color='g')

    plt.title("Salida del filtro ITU-R BS.468-4 por bloques")
    plt.xlabel("Tiempo [s]")
    plt.ylabel("Amplitud")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

