import time
from bitalino import BITalino
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import threading
from scipy.signal import iirnotch, filtfilt
from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder

# Configuration
macAddress = "88:6B:0F:D9:19:B0"
BUFFER_SIZE = 1000  # Number of latest samples to display
SAMPLING_RATE = 1000  # Hz
READ_CHUNK_SIZE = 10  # Samples to read at once

# OSC Configuration for Pure Data
OSC_IP = "127.0.0.1"  # localhost
OSC_PORT = 8000  # Pure Data will listen on this port
osc_client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)

# Frequency bands to monitor and send to Pure Data
FREQUENCY_BANDS = {
    'delta': (1, 4),      # 1-4 Hz
    'theta': (4, 8),      # 4-8 Hz  
    'alpha': (8, 13),     # 8-13 Hz
    'beta': (13, 30),     # 13-30 Hz
    'gamma': (30, 100),   # 30-100 Hz
    'emg_low': (20, 60),  # Low EMG band
    'emg_high': (60, 200) # High EMG band
}

# BITalino EMG Transfer Function Parameters
VCC = 3.3  # Operating voltage (3.3V for BITalino)
G_EMG = 1009  # Sensor gain
N_BITS = 10  # Resolution (10-bit ADC)
ADC_MAX = 2**N_BITS - 1  # Maximum ADC value (1023 for 10-bit)

# Notch filter parameters
NOTCH_FREQ = 50.0  # Frequency to remove (Hz)
QUALITY_FACTOR = 30.0  # Higher Q = narrower notch

def convert_adc_to_mv(adc_values):
    """Convert raw ADC values to millivolts using BITalino EMG transfer function"""
    emg_volts = ((adc_values / (2**N_BITS)) - 0.5) * VCC / G_EMG
    emg_mv = emg_volts * 1000
    return emg_mv

def apply_notch_filter(signal, sampling_rate, notch_freq, quality_factor):
    """Apply a notch filter to remove specific frequency component"""
    if len(signal) < 6:  # Need minimum samples for filtering
        return signal
    
    # Design notch filter
    b_notch, a_notch = iirnotch(notch_freq, quality_factor, sampling_rate)
    
    # Apply filter using zero-phase filtering to avoid phase distortion
    try:
        filtered_signal = filtfilt(b_notch, a_notch, signal)
        return filtered_signal
    except:
        return signal

def compute_fft(signal, sampling_rate):
    """Compute the FFT of the signal and return frequencies and magnitudes"""
    if len(signal) < 2:
        return np.array([]), np.array([])
    
    # Apply window function to reduce spectral leakage
    windowed_signal = signal * np.hanning(len(signal))
    
    # Compute FFT
    fft_data = np.fft.fft(windowed_signal)
    
    # Get magnitude spectrum (only positive frequencies)
    n_samples = len(signal)
    freqs = np.fft.fftfreq(n_samples, 1/sampling_rate)[:n_samples//2]
    magnitudes = np.abs(fft_data[:n_samples//2])
    
    return freqs, magnitudes

def get_frequency_band_power(freqs, magnitudes, freq_range):
    """Extract average power in a specific frequency band"""
    if len(freqs) == 0 or len(magnitudes) == 0:
        return 0.0
    
    # Find indices for the frequency range
    start_freq, end_freq = freq_range
    start_idx = np.where(freqs >= start_freq)[0]
    end_idx = np.where(freqs <= end_freq)[0]
    
    if len(start_idx) == 0 or len(end_idx) == 0:
        return 0.0
    
    start_idx = start_idx[0]
    end_idx = end_idx[-1] if len(end_idx) > 0 else len(magnitudes) - 1
    
    if start_idx >= len(magnitudes) or end_idx >= len(magnitudes) or start_idx > end_idx:
        return 0.0
    
    # Calculate average power in the band
    band_power = np.mean(magnitudes[start_idx:end_idx + 1])
    return float(band_power)

def send_data_to_puredata(freqs, magnitudes):
    """Send frequency band data to Pure Data via OSC"""
    try:
        # Send individual frequency band powers
        for band_name, freq_range in FREQUENCY_BANDS.items():
            power = get_frequency_band_power(freqs, magnitudes, freq_range)
            osc_client.send_message(f"/emg/{band_name}", power)
        
        # Send dominant frequency
        if len(magnitudes) > 1:
            dominant_freq_idx = np.argmax(magnitudes[1:]) + 1  # Exclude DC
            dominant_freq = freqs[dominant_freq_idx] if dominant_freq_idx < len(freqs) else 0.0
            dominant_power = magnitudes[dominant_freq_idx] if dominant_freq_idx < len(magnitudes) else 0.0
            
            osc_client.send_message("/emg/dominant_freq", float(dominant_freq))
            osc_client.send_message("/emg/dominant_power", float(dominant_power))
        
        # Send total RMS power
        total_rms = np.sqrt(np.mean(magnitudes**2)) if len(magnitudes) > 0 else 0.0
        osc_client.send_message("/emg/total_rms", float(total_rms))
        
        # Send specific frequency amplitudes (example: 10Hz, 20Hz, 30Hz, 40Hz, 60Hz)
        specific_frequencies = [10, 20, 30, 40, 60, 80, 100, 200, 300, 400, 500]
        for target_freq in specific_frequencies:
            if len(freqs) > 0:
                closest_idx = np.argmin(np.abs(freqs - target_freq))
                if closest_idx < len(magnitudes):
                    amplitude = float(magnitudes[closest_idx])
                    osc_client.send_message(f"/emg/freq_{target_freq}hz", amplitude)
        
    except Exception as e:
        print(f"Error sending OSC data: {e}")

# Initialize BITalino
device = BITalino(macAddress)
print("Connected to BITalino")

# Start acquisition
device.start(SAMPLING_RATE, [0])
print("Device started")

# Initialize data buffers
raw_data_buffer = deque(maxlen=BUFFER_SIZE)
emg_data_buffer = deque(maxlen=BUFFER_SIZE)

# Variables for thread control
running = True
start_time = time.time()

def data_acquisition():
    """Thread function for continuous data acquisition"""
    global running
    while running:
        try:
            new_samples = device.read(READ_CHUNK_SIZE)
            channel_data = new_samples[:, 5]
            emg_mv_data = convert_adc_to_mv(channel_data)
            
            raw_data_buffer.extend(channel_data)
            emg_data_buffer.extend(emg_mv_data)
            
            time.sleep(0.01)
        except Exception as e:
            print(f"Error reading data: {e}")
            break

def update_plot():
    """Update the matplotlib plot with latest data and send to Pure Data"""
    global osc_send_counter
    
    if len(emg_data_buffer) > 0:
        emg_data = np.array(emg_data_buffer)
    
        # Apply notch filter to EMG data
        filtered_emg = apply_notch_filter(emg_data, SAMPLING_RATE, NOTCH_FREQ, QUALITY_FACTOR)

        # Update FFT plot (filtered signal) and send to Pure Data
        if len(filtered_emg) > 10:
            freqs_filt, magnitudes_filt = compute_fft(filtered_emg, SAMPLING_RATE)
            if len(freqs_filt) > 0:
                # Send data to Pure Data
                send_data_to_puredata(freqs_filt, magnitudes_filt)


# Start data acquisition thread
data_thread = threading.Thread(target=data_acquisition)
data_thread.daemon = True
data_thread.start()

print("Starting real-time plotting and OSC transmission to Pure Data...")
print(f"OSC Target: {OSC_IP}:{OSC_PORT}")
print("Pure Data OSC messages:")
for band_name, freq_range in FREQUENCY_BANDS.items():
    print(f"  /emg/{band_name} - {freq_range[0]}-{freq_range[1]}Hz")
print("  /emg/dominant_freq - Dominant frequency")
print("  /emg/dominant_power - Dominant frequency power")
print("  /emg/total_rms - Total RMS power")
print("  /emg/freq_XXhz - Specific frequency amplitudes")

try:
    while True:
        update_plot()
        time.sleep(0.001)

except KeyboardInterrupt:
    print("\nStopping acquisition...")
finally:
    running = False
    print("Stopping device...")
    device.stop()
    device.close()
    plt.ioff()
    plt.show()

print("Acquisition complete")