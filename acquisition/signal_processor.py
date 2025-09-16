import numpy as np
from scipy.signal import butter, filtfilt, iirnotch

class SignalProcessor:
    @staticmethod
    def compute_fft(signal, sampling_rate):
        """
        Compute the Fast Fourier Transform (FFT) of the given signal.

        Parameters:
            signal (array-like): The input signal for FFT.
            sampling_rate (float): The sampling rate of the signal in Hz.

        Returns:
            freqs (numpy.ndarray): Array of frequency bins.
            magnitudes (numpy.ndarray): Array of magnitude values corresponding to the frequency bins.
        """
        if len(signal) < 2:
            return np.array([]), np.array([])
        windowed_signal = signal * np.hanning(len(signal))
        fft_data = np.fft.fft(windowed_signal)
        n_samples = len(signal)
        freqs = np.fft.fftfreq(n_samples, 1/sampling_rate)[:n_samples//2]
        magnitudes = np.abs(fft_data[:n_samples//2])
        return freqs, magnitudes

    @staticmethod
    def apply_lowpass(signal, cutoff, sampling_rate, order=4):
        """
        Apply a 4th-order Butterworth lowpass filter to the input signal.

        Parameters:
            signal (array-like): The input signal to be filtered.
            cutoff (float): The cutoff frequency of the filter in Hz (e.g., 5Hz).
            sampling_rate (float): The sampling rate of the signal in Hz.

        Returns:
            array-like: The filtered signal.
        """
        if len(signal) < 2:
            return signal
        nyq = 0.5 * sampling_rate
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        try:
            filtered_signal = filtfilt(b, a, signal)
            return filtered_signal
        except Exception:
            return signal

    @staticmethod
    def apply_notch(signal, notch_freq, sampling_rate, quality_factor=30.0):
        """
        Apply a notch (band-stop) filter to the input signal to remove a specific frequency.

        Args:
            signal (numpy.ndarray or list): Input time-domain signal samples.
            notch_freq (float): Frequency to be removed from the signal (e.g., 50Hz for powerline interference).
            sampling_rate (float): Sampling rate of the signal in Hz.
            quality_factor (float, optional): Quality factor (Q) of the notch filter, which determines the bandwidth.
                Higher Q means a narrower notch. Default is 30.

        Returns:
            filtered_signal (numpy.ndarray): Signal after notch filtering.

        Notes:
            - Uses a second-order IIR notch filter (scipy.signal.iirnotch).
            - 'quality_factor' controls the width of the notch; typical values are between 20 and 50 for powerline removal.
        """
        if len(signal) < 6:
            return signal
        b_notch, a_notch = iirnotch(notch_freq, quality_factor, sampling_rate)
        try:
            filtered_signal = filtfilt(b_notch, a_notch, signal)
            return filtered_signal
        except Exception:
            return signal
