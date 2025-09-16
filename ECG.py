import time
from bitalino import BITalino
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import threading
from scipy.signal import iirnotch, filtfilt
from pythonosc import udp_client


class Sender:
    """Handles OSC communication with Pure Data"""
    
    def __init__(self, ip="127.0.0.1", port=8000):
        self.osc_client = udp_client.SimpleUDPClient(ip, port)
        self.osc_send_counter = 0
        self.OSC_SEND_INTERVAL = 10
        
        # Frequency bands to monitor
        self.FREQUENCY_BANDS = {
            'delta': (1, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 100),
            'emg_low': (20, 60),
            'emg_high': (60, 200)
        }
        
        # Specific frequencies to monitor
        self.specific_frequencies = [10, 20, 30, 40, 60, 80, 100]
        
    def get_frequency_band_power(self, freqs, magnitudes, freq_range):
        """Extract average power in a specific frequency band"""
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
    
    def send_data_to_puredata(self, freqs, magnitudes, raw):
        """Send frequency band data to Pure Data via OSC"""
        try:
            self.osc_client.send_message("/ecg/latest_amp", min(abs(raw[-100:])))
            print(f"latest ECG biggest value : {max(abs(raw[-10:]))}")
            # Send individual frequency band powers
            for band_name, freq_range in self.FREQUENCY_BANDS.items():
                power = self.get_frequency_band_power(freqs, magnitudes, freq_range)
                self.osc_client.send_message(f"/emg/{band_name}", power)
            
            # Send dominant frequency
            if len(magnitudes) > 1:
                dominant_freq_idx = np.argmax(magnitudes[5:]) + 1
                dominant_freq = freqs[dominant_freq_idx] if dominant_freq_idx < len(freqs) else 0.0
                dominant_power = magnitudes[dominant_freq_idx] if dominant_freq_idx < len(magnitudes) else 0.0
                
                self.osc_client.send_message("/emg/dominant_freq", float(dominant_freq))
                self.osc_client.send_message("/emg/dominant_power", float(dominant_power))
            
            # Send total RMS power
            total_rms = np.sqrt(np.mean(magnitudes**2)) if len(magnitudes) > 0 else 0.0
            self.osc_client.send_message("/emg/total_rms", float(total_rms))
            
            # Send specific frequency amplitudes
            for target_freq in self.specific_frequencies:
                if len(freqs) > 0:
                    closest_idx = np.argmin(np.abs(freqs - target_freq))
                    if closest_idx < len(magnitudes):
                        amplitude = float(magnitudes[closest_idx])
                        self.osc_client.send_message(f"/emg/freq_{target_freq}hz", amplitude)
                        
        except Exception as e:
            print(f"Error sending OSC data: {e}")
    
    def should_send_data(self):
        return True
        """Check if it's time to send data based on interval"""
        self.osc_send_counter += 1
        if self.osc_send_counter >= self.OSC_SEND_INTERVAL:
            self.osc_send_counter = 0
            return True
        return False
    
    def print_osc_info(self, ip, port):
        """Print OSC configuration information"""
        print(f"OSC Target: {ip}:{port}")
        print("Pure Data OSC messages:")
        for band_name, freq_range in self.FREQUENCY_BANDS.items():
            print(f"  /emg/{band_name} - {freq_range[0]}-{freq_range[1]}Hz")
        print("  /emg/dominant_freq - Dominant frequency")
        print("  /emg/dominant_power - Dominant frequency power")
        print("  /emg/total_rms - Total RMS power")
        print("  /emg/freq_XXhz - Specific frequency amplitudes")


class Graphs:
    """Handles real-time plotting of EMG data"""
    
    def __init__(self, buffer_size=100, sampling_rate=1000):
        self.buffer_size = buffer_size
        self.sampling_rate = sampling_rate
        self.start_time = time.time()
        
        # Notch filter parameters
        self.NOTCH_FREQ = 50.0
        self.QUALITY_FACTOR = 30.0
        
        # Data buffers
        self.raw_data_buffer = deque(maxlen=buffer_size)
        self.emg_data_buffer = deque(maxlen=buffer_size)
        
        # BITalino EMG Transfer Function Parameters
        self.VCC = 3.3
        self.G_EMG = 1100
        self.N_BITS = 10
        self.ADC_MAX = 2**self.N_BITS - 1
        
        self._setup_plot()
        
    def _setup_plot(self):
        """Initialize matplotlib plots"""
        plt.ion()
        self.fig, (self.ax2, self.ax3, self.ax4) = plt.subplots(3, 1, figsize=(12, 14))
        
        # EMG in mV plot
        self.line2, = self.ax2.plot([], [], 'r-', label='EMG Signal')
        self.ax2.set_xlim(0, self.buffer_size)
        self.ax2.set_ylim(-1.64, 1.64)
        self.ax2.set_xlabel('Sample Index')
        self.ax2.set_ylabel('EMG Signal (mV)')
        self.ax2.set_title('EMG Signal in millivolts (Latest 1000 samples)')
        self.ax2.grid(True)
        self.ax2.legend()
        
        # FFT plot (original signal)
        self.line3, = self.ax3.plot([], [], 'g-', label='Original FFT')
        self.ax3.set_xlim(0, self.sampling_rate // 2)
        self.ax3.set_ylim(0, 1)
        self.ax3.set_xlabel('Frequency (Hz)')
        self.ax3.set_ylabel('Magnitude')
        self.ax3.set_title('Real-time FFT of EMG Signal')
        self.ax3.grid(True)
        self.ax3.legend()
        
        # FFT Filtered plot
        self.line4, = self.ax4.plot([], [], 'b-', label='Filtered FFT (50Hz Notch)')
        self.ax4.set_xlim(0, self.sampling_rate // 2)
        self.ax4.set_ylim(0, 1)
        self.ax4.set_xlabel('Frequency (Hz)')
        self.ax4.set_ylabel('Magnitude')
        self.ax4.set_title(f'FFT after {self.NOTCH_FREQ}Hz Notch Filter - Sending to Pure Data')
        self.ax4.grid(True)
        self.ax4.legend()
        
        plt.tight_layout()
    
    def convert_adc_to_mv(self, adc_values):
        """Convert raw ADC values to millivolts using BITalino EMG transfer function"""
        emg_volts = ((adc_values / (2**self.N_BITS)) - 0.5) * self.VCC / self.G_EMG
        emg_mv = emg_volts * 1000
        return emg_mv
    
    def apply_notch_filter(self, signal, notch_freq, quality_factor):
        """Apply a notch filter to remove specific frequency component"""
        if len(signal) < 6:
            return signal
        
        b_notch, a_notch = iirnotch(notch_freq, quality_factor, self.sampling_rate)
        
        try:
            filtered_signal = filtfilt(b_notch, a_notch, signal)
            return filtered_signal
        except:
            return signal
    
    def compute_fft(self, signal):
        """Compute the FFT of the signal and return frequencies and magnitudes"""
        if len(signal) < 2:
            return np.array([]), np.array([])
        
        windowed_signal = signal * np.hanning(len(signal))
        fft_data = np.fft.fft(windowed_signal)
        
        n_samples = len(signal)
        freqs = np.fft.fftfreq(n_samples, 1/self.sampling_rate)[:n_samples//2]
        magnitudes = np.abs(fft_data[:n_samples//2])
        
        return freqs, magnitudes
    
    def add_data(self, channel_data):
        """Add new data to buffers"""
        emg_mv_data = self.convert_adc_to_mv(channel_data)
        self.raw_data_buffer.extend(channel_data)
        self.emg_data_buffer.extend(emg_mv_data)
    
    def update_plot(self, sender=None):
        """Update the matplotlib plot with latest data"""
        if len(self.raw_data_buffer) == 0 or len(self.emg_data_buffer) == 0:
            return None, None
        
        raw_data = np.array(self.raw_data_buffer)
        emg_data = np.array(self.emg_data_buffer)
        x_data = np.arange(len(raw_data))
        
        # Update EMG mV plot
        self.line2.set_data(x_data, emg_data)
        self.ax2.set_xlim(0, len(emg_data))
        if len(emg_data) > 0:
            data_range = np.max(emg_data) - np.min(emg_data)
            margin = max(0.1, data_range * 0.1)
            y_min = max(-1.64, np.min(emg_data) - margin)
            y_max = min(1.64, np.max(emg_data) + margin)
            self.ax2.set_ylim(y_min, y_max)
        
        # Apply notch filter to EMG data
        filtered_emg = self.apply_notch_filter(emg_data, self.NOTCH_FREQ, self.QUALITY_FACTOR)
        filtered_emg = self.apply_notch_filter(filtered_emg, 1, 20)
        
        # Update FFT plot (original signal)
        freqs_filt, magnitudes_filt = None, None
        if len(emg_data) > 10:
            freqs, magnitudes = self.compute_fft(emg_data)
            if len(freqs) > 0:
                self.line3.set_data(freqs, magnitudes)
                self.ax3.set_xlim(0, min(500, self.sampling_rate // 2))
                if np.max(magnitudes) > 0:
                    self.ax3.set_ylim(0, np.max(magnitudes) * 1.1)
                
                if len(magnitudes) > 1:
                    dominant_freq_idx = np.argmax(magnitudes[5:]) + 1
                    dominant_freq = freqs[dominant_freq_idx]
                    self.ax3.set_title(f'Original FFT - Dominant: {dominant_freq:.1f} Hz')
        
        # Update FFT plot (filtered signal)
        if len(filtered_emg) > 10:
            freqs_filt, magnitudes_filt = self.compute_fft(filtered_emg)
            if len(freqs_filt) > 0:
                self.line4.set_data(freqs_filt, magnitudes_filt)
                self.ax4.set_xlim(0, min(500, self.sampling_rate // 2))
                if np.max(magnitudes_filt) > 0:
                    self.ax4.set_ylim(0, np.max(magnitudes_filt) * 1.1)
                
                # Send data to Pure Data if sender is provided (every 5ms)
                if sender and sender.should_send_data():
                    sender.send_data_to_puredata(freqs_filt, magnitudes_filt, emg_data)
                
                if len(magnitudes_filt) > 1:
                    dominant_freq_idx_filt = np.argmax(magnitudes_filt[1:]) + 1
                    dominant_freq_filt = freqs_filt[dominant_freq_idx_filt]
                    self.ax4.set_title(f'Filtered FFT (>5Hz) - Dom: {dominant_freq_filt:.1f}Hz - OSC→PD')
        
        # Update main title
        elapsed_time = time.time() - self.start_time
        self.ax2.set_title(f'EMG Signal - Range: [{np.min(emg_data):.2f}, {np.max(emg_data):.2f}] mV - {elapsed_time:.1f}s')
        
        plt.draw()
        plt.pause(0.001)
        #time.sleep(0.001)
        
        return freqs_filt, magnitudes_filt
    
    def is_open(self):
        """Check if plot window is still open"""
        return bool(plt.get_fignums())
    
    def close(self):
        """Close the plot"""
        plt.ioff()
        plt.show()


def main():
    """Main function to run the EMG signal processing"""
    # Configuration
    macAddress = "88:6B:0F:D9:19:B0"
    BUFFER_SIZE = 1000
    SAMPLING_RATE = 1000
    READ_CHUNK_SIZE = 100
    OSC_IP = "127.0.0.1"
    OSC_PORT = 8000
    
    # Initialize classes
    sender = Sender(OSC_IP, OSC_PORT)
    graphs = Graphs(BUFFER_SIZE, SAMPLING_RATE)
    
    # Initialize BITalino
    try:
        device = BITalino(macAddress)
        print("Connected to BITalino")
        device.start(SAMPLING_RATE, [1])
        print("Device started")
    except Exception as e:
        print(f"Error connecting to BITalino: {e}")
        return
    
    # Print OSC information
    print("Starting real-time plotting and OSC transmission to Pure Data...")
    sender.print_osc_info(OSC_IP, OSC_PORT)
    
    # Variables for thread control
    running = True
    
    def data_acquisition():
        """Thread function for continuous data acquisition"""
        nonlocal running
        while running:
            try:
                new_samples = device.read(10)
                channel_data = new_samples[:, 5]
                graphs.add_data(channel_data)
                time.sleep(0.01)
            except Exception as e:
                print(f"Error reading data: {e}")
                break
    
    # Start data acquisition thread
    data_thread = threading.Thread(target=data_acquisition)
    data_thread.daemon = True
    data_thread.start()
    
    try:
        # Main loop
        while True:
            graphs.update_plot(sender)
            if not graphs.is_open():
                break
                
    except KeyboardInterrupt:
        print("\nStopping acquisition...")
    finally:
        running = False
        print("Stopping device...")
        try:
            device.stop()
            device.close()
        except:
            pass
        graphs.close()
    
    print("Acquisition complete")


if __name__ == "__main__":
    main()