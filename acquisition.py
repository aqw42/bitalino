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

# Global thread communication
sensor_thread_status = {"running": True, "error": None, "disconnected": False}
data_buffers = {id: deque(maxlen=BUFFER_SIZE) for id, sensor_type in SENSORS}

def transfer_function(adc_values, sensor_type):
    ADC_BITS = 10
    VCC = 3.3
    GAIN = GAINS[sensor_type]  # Fixed: was GAIN instead of GAINS
    
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
            print("[INIT_BT] Connecting...", flush=True)
            device = BITalino(MAC, timeout=1)
            print("[INIT_BT] Connected to BITalino", flush=True)
            return device
    
        except Exception as e:
            print(f"[INIT_BT] Error connecting to BITalino: {e}", flush=True)
            print("[INIT_BT] Trying again in 5 seconds", flush=True)
            missed_count += 1
            time.sleep(5)
        
        if (missed_count > 10):
            print("[INIT_BT] Couldn't connect to the device.", flush=True)
            return None

def sensor_acquisition_loop(device):
    global sensor_thread_status
    missed_count = 0
    
    # Reset status
    sensor_thread_status["running"] = True
    sensor_thread_status["error"] = None
    sensor_thread_status["disconnected"] = False
    
    device.start(SAMPLING_RATE, [port + 1 for port, type in SENSORS])
    
    print("[SENSOR] Starting acquisition loop", flush=True)

    while sensor_thread_status["running"]:
        try:
            # Read is blocking so no need to sleep
            new_samples = device.read(READ_CHUNK_SIZE)
            
            # Process each sensor
            for i, (port, sensor_type) in enumerate(SENSORS):
                # Column index is port + 4 (first 4 columns are sequence, digital channels, etc.)
                channel_data = new_samples[:, port + 3]
                
                # Convert to physical units
                physical_data = transfer_function(channel_data, sensor_type)
                
                # Store in buffer
                data_buffers[port].extend(physical_data)
                print(i)
                print(physical_data)
            
            # Reset missed count on successful read
            missed_count = 0
            
        except Exception as e:
            print(f"[SENSOR] Exception during read: {e}", flush=True)
            print(f"[SENSOR] Exception type: {type(e)}", flush=True)
            
            # Check for specific BITalino exceptions
            if hasattr(e, 'args') and len(e.args) > 0:
                if e.args[0] == ExceptionCode.CONTACTING_DEVICE:
                    print("[SENSOR] Lost communication with device", flush=True)
                elif e.args[0] == ExceptionCode.DEVICE_NOT_IN_ACQUISITION:
                    print("[SENSOR] Device not in acquisition mode", flush=True)
                sensor_thread_status["disconnected"] = True
                break
            
            # Handle other connection-related exceptions
            if "Bluetooth" in str(e) or "connection" in str(e).lower() or "host is down" in str(e).lower():
                print("[SENSOR] Connection-related error detected", flush=True)
                sensor_thread_status["disconnected"] = True
                break
                
            missed_count += 1
            print(f"[SENSOR] Missed read #{missed_count}", flush=True)
            
            if missed_count >= 5:  # Reduced threshold for faster detection
                print("[SENSOR] Too many consecutive missed reads", flush=True)
                sensor_thread_status["disconnected"] = True
                break
                
            # Short sleep before retry
            time.sleep(0.1)
    
    print("[SENSOR] Acquisition loop ended", flush=True)
    sensor_thread_status["running"] = False

def osc_refresh_loop():
    client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
    print("[OSC] Starting OSC transmission loop", flush=True)
    
    while sensor_thread_status["running"]:
        start_time = time.time()
        
        # Send latest data for each sensor
        for sensor_id in data_buffers:
            if len(data_buffers[sensor_id]) > 0:
                latest_value = data_buffers[sensor_id][-1]
                try:
                    client.send_message(f"/{sensor_id}", latest_value)
                except Exception as e:
                    print(f"[OSC] Error sending {sensor_id}: {e}", flush=True)
        
        elapsed = time.time() - start_time
        sleep_time = max(0, (1 / OSC_REFRESH_RATE) - elapsed)
        time.sleep(sleep_time)
    
    print("[OSC] OSC transmission loop ended", flush=True)

def main():
    global sensor_thread_status
    
    print(SENSORS, flush=True)
    print(f"[MAIN] Connecting to {MAC}", flush=True)
    
    device = init_bt()
    if device is None:
        exit(-1)

    print("[MAIN] Starting real-time plotting and OSC transmission to Pure Data...", flush=True)
    print(f"[MAIN] OSC Target: {OSC_IP}:{OSC_PORT}", flush=True)
    
    try:
        sensor_thread = threading.Thread(target=sensor_acquisition_loop, args=(device,))
        sensor_thread.start()

        osc_thread = threading.Thread(target=osc_refresh_loop)
        osc_thread.start()
        
        while True:
            # Check if sensor thread is still running
            if not sensor_thread.is_alive() or sensor_thread_status["disconnected"]:
                print("[MAIN] Sensor thread stopped or device disconnected", flush=True)
                
                # Stop the device if it's still connected
                try:
                    device.close()
                except:
                    pass
                
                print("[MAIN] Attempting to reconnect...", flush=True)
                device = init_bt()
                if device is None:
                    print("[MAIN] Failed to reconnect, exiting", flush=True)
                    exit(-1)
                else:
                    print("[MAIN] Successfully reconnected, resuming data acquisition", flush=True)
                
                # Restart sensor thread
                sensor_thread = threading.Thread(target=sensor_acquisition_loop, args=(device,))
                sensor_thread.start()
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[MAIN] Keyboard interrupt received", flush=True)
        sensor_thread_status["running"] = False
    
    print("[MAIN] Stopping device...", flush=True)
    try:
        device.close()
    except Exception as e:
        print(f"[MAIN] Error stopping device: {e}", flush=True)
    
    print("[MAIN] Device closed!", flush=True)
    exit(0)

if __name__ == "__main__":
    main()