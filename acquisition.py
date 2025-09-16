#! /usr/bin/python

import time
from bitalino import BITalino, ExceptionCode
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
# Supported : 10 / 100 / 1000
READ_CHUNK_SIZE = 10
    
# OpenSoundControl server 
OSC_IP = "127.0.0.1"
OSC_PORT = 8000
OSC_REFRESH_RATE = 100

# analog input number and sensor type
SENSORS = [
    (1, "EMG"),
    (2, "ECG"),
    (3, "EEG")
]

# Given by sensors datasheets
# https://support.pluxbiosignals.com/wp-content/uploads/2021/11/revolution-emg-sensor-datasheet-1.pdf
# https://bitalino.com/storage/uploads/media/revolution-ecg-sensor-datasheet-revb-1.pdf
# https://bitalino.com/storage/uploads/media/revolution-eeg-sensor-datasheet-revb.pdf
GAINS = {   
    "EMG": 1009, # [-1.64𝑚𝑉, 1.64𝑚𝑉]
    "ECG": 1100, # [-1.5𝑚𝑉, 1.5𝑚𝑉]
    "EEG": 41782 # [-39.49𝜇𝑉, 39.49𝜇𝑉]
}



def transfer_function(adc_values, sensor_type):
    ADC_BITS = 10
    VCC = 3.3
    GAIN = GAINS[sensor_type]
    
    measured_v = ((adc_values / (2**ADC_BITS)) - 0.5) * VCC / GAIN

    # EEG unit is uV, others are mV
    if (sensor_type == "EEG"):
        return measured_v * 1000000
    else:
        return measured_v * 1000



def init_bt():
    missed_count = 0
    while True:
        try:
            device = BITalino(MAC)
            print("[INIT_BT] Connected to BITalino")
    
            ports = [port + 1 for port, type in SENSORS]
            device.start(SAMPLING_RATE, ports)
            print("[INIT_BT] Device started")
            return device
    
        except Exception as e:
            print(f"[INIT_BT] Error connecting to BITalino: {e}")
            print("[INIT_BT] Trying again in 10 seconds")
            missed_count += 1
            time.sleep(10)
        
        if (missed_count > 10):
            print("[INIT_BT] Couldn't connect to the device.")
            return None


def sensor_acquisition_loop(device):
    missed_count = 0
    missed_read = False

    while True:
        try:
            # Read is blocking so no need to sleep
            new_samples = device.read(READ_CHUNK_SIZE)
            ports = [port + 4 for port, type in SENSORS]
            channel_data = new_samples[:, ports]

        except Exception as e:
            if (e.args == ExceptionCode.CONTACTING_DEVICE):
                print("[SENSOR] Lost the communication with the device", flush=True)
            if (e.args == ExceptionCode.DEVICE_NOT_IN_ACQUISITION):
                print("[SENSOR] The device weirded itself duh", flush=True)
            missed_count += 1
            missed_read = True            

        finally:
            if not missed_read:
                missed_count = 0
            elif missed_count >= 10:
                print("[SENSOR] Missed too much consecutive reads", flush=True)
                return
    

def osc_refresh_loop():
    while True:
        start_time = time.time()
        
        # Update osc here
        
        elapsed = time.time() - start_time
        sleep_time = max(0, (1 / OSC_REFRESH_RATE) - elapsed)
        time.sleep(sleep_time)


def main():
    print(SENSORS)
    print(f"[MAIN] Connecting to {MAC}")
    
    device = init_bt()
    if (device == None):
        exit(-1)

    print("[MAIN] Starting real-time plotting and OSC transmission to Pure Data...")
    print(f"[MAIN] OSC Target: {OSC_IP}:{OSC_PORT}")
    
    try:
        sensor_thread = threading.Thread(target=sensor_acquisition_loop, args=(device,))
        sensor_thread.start()

        osc_thread = threading.Thread(target=osc_refresh_loop)
        osc_thread.start()
        
        while True:
            if (sensor_thread.is_alive() == False):
                print("[MAIN] Restarting the connection")
                
                device = init_bt()
                if (device == None):
                    exit(-1)
                else:
                    print("[MAIN] Successfully reconnected, resuming data acquisition")
                
                sensor_thread = threading.Thread(target=sensor_acquisition_loop, args=(device,))
                sensor_thread.start()
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nNooo don't go")
    
    print("Stopping device...")
    device.stop()
    device.close()
    print("Device closed !")
    exit(0)


if __name__ == "__main__":
    main()