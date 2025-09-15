class SignalProcessor:
    @staticmethod
    def compute_fft(signal, sampling_rate):
        """
    @staticmethod
    def apply_lowpass(signal, cutoff, sampling_rate):
        """
        Apply a 4th-order Butterworth lowpass filter to the input signal.

        Parameters:
            signal (array-like): The input signal to be filtered.
            cutoff (float): The cutoff frequency of the filter in Hz (e.g., 5Hz).
            sampling_rate (float): The sampling rate of the signal in Hz.

        Returns:
            array-like: The filtered signal.
        """
        from scipy.signal import butter, filtfilt
        nyquist = 0.5 * sampling_rate
        normal_cutoff = cutoff / nyquist
        b, a = butter(N=4, Wn=normal_cutoff, btype='low', analog=False)
        return filtfilt(b, a, signal)
            signal (numpy.ndarray or list): Input time-domain signal samples.
            sampling_rate (float): Sampling rate of the signal in Hz.

        Returns:
            freqs (numpy.ndarray): Array of frequency bins.
    @staticmethod
    def apply_notch(signal, notch_freq, sampling_rate, quality_factor=30):
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
        pass
            - 'signal' is a 1D array-like object (e.g., numpy array or list).
            - 'sampling_rate' is a positive float representing Hz.
        """
        import numpy as np
        signal = np.asarray(signal)
        n = len(signal)
        fft_values = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(n, d=1.0/sampling_rate)
        return freqs, fft_values
    @staticmethod
    def apply_lowpass(signal, cutoff, sampling_rate):
        pass
    @staticmethod
    def apply_notch(signal, notch_freq, sampling_rate):
        pass
