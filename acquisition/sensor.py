class Sensor:
    def __init__(self, sensor_type, port, index):
        self.type = sensor_type.upper()
        self.port = port
        self.index = index

    def apply_transfer_function(self, raw_data):
        """
        Applies the appropriate transfer function to the raw_data based on the sensor type.

        For EMG, EEG, and ECG sensors, different transfer functions are applied to convert
        the raw sensor data (expected as a list or numpy array of integers or floats) into
        meaningful physical values (output as a list or numpy array of floats).
        
        Args:
            raw_data (list or numpy.ndarray): The raw data samples from the sensor.

        Returns:
            list or numpy.ndarray: The processed data after applying the transfer function.
        """
        # Default: EMG transfer function, can be extended for EEG/ECG
        VCC = 3.3
        GAIN = 1009 if self.type == 'EMG' else 1  # Placeholder for other types
        N_BITS = 10
        emg_volts = ((raw_data / (2**N_BITS)) - 0.5) * VCC / GAIN
        emg_mv = emg_volts * 1000
        return emg_mv
