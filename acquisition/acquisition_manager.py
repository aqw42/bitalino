class AcquisitionManager:
    def __init__(self, bitalino_interface, sensors, buffer_size):
        self.bitalino = bitalino_interface
        self.sensors = sensors
        self.buffer_size = buffer_size
        self.buffers = {sensor: [] for sensor in sensors}

    def acquire_data(self):
        # Placeholder: would read from device and fill buffers per sensor
        pass
