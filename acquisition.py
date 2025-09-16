import time
from bitalino import BITalino
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import threading
from scipy.signal import iirnotch, filtfilt
from pythonosc import udp_client

    # Configuration
MAC = "88:6B:0F:D9:19:B0"
BUFFER_SIZE = 10000
SAMPLING_RATE = 1000
READ_CHUNK_SIZE = 10
    
OSC_IP = "127.0.0.1"
OSC_PORT = 8000

SENSORS = {
    (1, "EMG"),
    (2, "ECG")
}

def init_bt():
    while True:
        try:
            device = BITalino(MAC)
            print("Connected to BITalino")
            device.start(SAMPLING_RATE, [0])
            print("Device started")
            return device
        except Exception as e:
            print(f"Error connecting to BITalino: {e}")
            print("Trying again in 5 seconds")
            time.sleep(5)

device = None
running = True

def data_acquisition_loop():
    while running:
        try:
            new_samples = device.read(READ_CHUNK_SIZE)
            channel_data = new_samples[:, 5]
            graphs.add_data(channel_data)
            time.sleep(0.01)
        except Exception as e:
            print(f"Error reading data: {e}")
            break
    
def launch_data_acquisition_thread():
    data_thread = threading.Thread(target=data_acquisition_loop)
    data_thread.daemon = True
    data_thread.start()


def main():
    print(SENSORS)
    print(f"Connecting to {MAC}")
    
    device = init_bt()

    print("Starting real-time plotting and OSC transmission to Pure Data...")
    print(f"OSC Target: {OSC_IP}:{OSC_PORT}")
    
    launch_data_acquisition_thread()

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