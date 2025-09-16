from pythonosc import udp_client
import numpy as np

class OSCSender:
    def __init__(self, ip, port):
        self.osc_client = udp_client.SimpleUDPClient(ip, port)
        self.FREQUENCY_BANDS = {
            'delta': (1, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 100),
            'emg_low': (20, 60),
            'emg_high': (60, 200)
        }
        self.specific_frequencies = [10, 20, 30, 40, 60, 80, 100]

    def get_frequency_band_power(self, freqs, magnitudes, freq_range):
        if len(freqs) == 0 or len(magnitudes) == 0:
            return 0.0
        start_freq, end_freq = freq_range
        start_idx = np.where(freqs >= start_freq)[0]
        end_idx = np.where(freqs <= end_freq)[0]
        if len(start_idx) == 0 or len(end_idx) == 0:
            return 0.0
        start_idx = start_idx[0]
        end_idx = end_idx[-1] if len(end_idx) > 0 else len(magnitudes) - 1
        if start_idx >= len(magnitudes) or end_idx >= len(magnitudes) or start_idx > end_idx:
            return 0.0
        band_power = np.mean(magnitudes[start_idx:end_idx + 1])
        return float(band_power)

    def send_raw(self, sensor, data):
        # Example: /EMG1/raw
        endpoint = f"/{sensor.type}{sensor.index}/raw"
        self.osc_client.send_message(endpoint, data.tolist() if hasattr(data, 'tolist') else data)

    def send_fft(self, sensor, freqs, magnitudes):
        # Send frequency band powers and dominant frequency for this sensor
        prefix = f"/{sensor.type}{sensor.index}"
        for band_name, freq_range in self.FREQUENCY_BANDS.items():
            power = self.get_frequency_band_power(freqs, magnitudes, freq_range)
            self.osc_client.send_message(f"{prefix}/{band_name}", power)
        if len(magnitudes) > 1:
            dominant_freq_idx = np.argmax(magnitudes[5:]) + 1
            dominant_freq = freqs[dominant_freq_idx] if dominant_freq_idx < len(freqs) else 0.0
            dominant_power = magnitudes[dominant_freq_idx] if dominant_freq_idx < len(magnitudes) else 0.0
            self.osc_client.send_message(f"{prefix}/dominant_freq", float(dominant_freq))
            self.osc_client.send_message(f"{prefix}/dominant_power", float(dominant_power))
        total_rms = np.sqrt(np.mean(magnitudes**2)) if len(magnitudes) > 0 else 0.0
        self.osc_client.send_message(f"{prefix}/total_rms", float(total_rms))
        for target_freq in self.specific_frequencies:
            if len(freqs) > 0:
                closest_idx = np.argmin(np.abs(freqs - target_freq))
                if closest_idx < len(magnitudes):
                    amplitude = float(magnitudes[closest_idx])
                    self.osc_client.send_message(f"{prefix}/freq_{target_freq}hz", amplitude)

    def send_filtered_fft(self, sensor, freqs, magnitudes):
        # For now, same as send_fft (could be extended for filtered-specific endpoints)
        self.send_fft(sensor, freqs, magnitudes)
