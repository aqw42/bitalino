import matplotlib.pyplot as plt
import numpy as np
from collections import deque

class GraphManager:
    def __init__(self, sensors, buffer_size, sampling_rate):
        self.sampling_rate = sampling_rate
        self.buffer_size = buffer_size
        self.sensors = sensors
        self.start_time = None
        self.buffers = {sensor: deque(maxlen=buffer_size) for sensor in sensors}
        self.mv_buffers = {sensor: deque(maxlen=buffer_size) for sensor in sensors}
        self.fig, self.axes = plt.subplots(len(sensors), 3, figsize=(12, 5*len(sensors)))
        if len(sensors) == 1:
            self.axes = np.expand_dims(self.axes, axis=0)
        plt.ion()
        plt.tight_layout()
        self.start_time = None

    def convert_adc_to_mv(self, adc_values, sensor):
        # Use BITalino EMG transfer function as default; can be extended per sensor type
        VCC = 3.3
        G_EMG = 1009
        N_BITS = 10
        emg_volts = ((adc_values / (2**N_BITS)) - 0.5) * VCC / G_EMG
        emg_mv = emg_volts * 1000
        return emg_mv

    def add_data(self, sensor, channel_data):
        emg_mv_data = self.convert_adc_to_mv(np.array(channel_data), sensor)
        self.buffers[sensor].extend(channel_data)
        self.mv_buffers[sensor].extend(emg_mv_data)

    def update_plot(self, sensor, freqs=None, magnitudes=None, filtered_freqs=None, filtered_magnitudes=None):
        idx = self.sensors.index(sensor)
        raw_data = np.array(self.buffers[sensor])
        emg_data = np.array(self.mv_buffers[sensor])
        x_data = np.arange(len(raw_data))
        ax2, ax3, ax4 = self.axes[idx]
        ax2.clear()
        ax2.plot(x_data, emg_data, 'r-', label='Signal (mV)')
        ax2.set_xlim(0, len(emg_data))
        ax2.set_xlabel('Sample Index')
        ax2.set_ylabel('Signal (mV)')
        ax2.set_title(f'{sensor.type}{sensor.index} Signal (mV)')
        ax2.grid(True)
        ax2.legend()
        if freqs is not None and magnitudes is not None:
            ax3.clear()
            ax3.plot(freqs, magnitudes, 'g-', label='Original FFT')
            ax3.set_xlim(0, min(500, self.sampling_rate // 2))
            ax3.set_xlabel('Frequency (Hz)')
            ax3.set_ylabel('Magnitude')
            ax3.set_title(f'{sensor.type}{sensor.index} FFT')
            ax3.grid(True)
            ax3.legend()
        if filtered_freqs is not None and filtered_magnitudes is not None:
            ax4.clear()
            ax4.plot(filtered_freqs, filtered_magnitudes, 'b-', label='Filtered FFT')
            ax4.set_xlim(0, min(500, self.sampling_rate // 2))
            ax4.set_xlabel('Frequency (Hz)')
            ax4.set_ylabel('Magnitude')
            ax4.set_title(f'{sensor.type}{sensor.index} Filtered FFT')
            ax4.grid(True)
            ax4.legend()
        plt.draw()
        plt.pause(0.01)

    def is_open(self):
        return bool(plt.get_fignums())

    def close(self):
        plt.ioff()
        plt.show()
