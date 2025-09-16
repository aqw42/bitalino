#! /usr/bin/python


SENSORS = [
    (1, "EMG"),
    (2, "ECG")
    (2, "ECG")
]
ports = [port + 4 for port, type in SENSORS]
print(ports)

GAINS = [
    ("EMG", 1009),
    ("ECG", 1),
    ("EEG", 1)
]

import threading
import time

count = 0

def test(a):
    global count
    for i in range(a):
        count += 1
        time.sleep(0.1)
    print("Exiting")
    return

t = threading.Thread(target=test, args=[10])
t.start()

while t.is_alive():
    time.sleep(1)
    print("waiting")



