from bitalino import BITalino

class BITalinoInterface:
    def __init__(self, mac_address):
        self.mac_address = mac_address
        self.device = None

    def connect(self):
        """Connect to the BITalino device."""
        # self.device = BITalino(self.mac_address)
        pass

    def start(self, sampling_rate, channels):
        """Start acquisition with given sampling rate and channels."""
        # self.device.start(sampling_rate, channels)
        pass

    def read(self, chunk_size):
        """Read a chunk of data from the device."""
        # return self.device.read(chunk_size)
        pass

    def stop(self):
        """Stop data acquisition."""
        # self.device.stop()
        pass

    def close(self):
        """Close the device connection."""
        # self.device.close()
        pass
