import difflib
import sys
import time
import threading
import struct
import numpy as np
from zlib import crc32
from remotemanager import serman
from remotemanager.reptim import *
from remotemanager.clihelper import *
from ADCDACPi import ADCDACPi
from threading import Timer
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, 1)

adcdac = ADCDACPi(1)
adcdac.set_adc_refvoltage(3.3)
adcdac.set_dac_voltage(1, 0.4)

accuracy = np.array([])
baud_rate_valid = False
led_power_valid = False
msg = ""

# ~~~~~~~~~~~~~~~~~~~~ setting up all variables ~~~~~~~~~~~~~~~~~~~~~~~~~
if len(sys.argv) == 4:
    msg = str(sys.argv[3])
elif len(sys.argv) == 3:
    msg = "Hello World!"
if len(sys.argv) >= 3:
    baud_rate = ast.literal_eval(str(sys.argv[1]))
    led_power = ast.literal_eval(str(sys.argv[2]))
    # convert to list if not already a list
    if not hasattr(baud_rate, "__len__"):
        baud_rate = [baud_rate]
    if not hasattr(led_power, "__len__"):
        led_power = [led_power]

    baud_rate_valid, led_power_valid = assert_settings(baud_rate, led_power)
    if baud_rate_valid:
        baud_rate = list(map(int, baud_rate))
    else:
        raise ValueError("Input baudrate(s) not valid!")
    if led_power_valid:
        led_power = list(map(int, led_power))
    else:
        raise ValueError("Input led power(s) not valid!")

while not baud_rate_valid:
    baud_rate, baud_rate_valid = get_baud_rate()
while not led_power_valid:
    led_power, led_power_valid = get_led_power()

if msg is None or msg == "":
    msg = input("Message to transmit [blank: 'Hello World!']: ")
if msg == "" or msg is None:
    msg = "Hello World!"

print(border_count * "=" + "\nBaudrate(s) set to\t%s" % baud_rate)
print("LED power(s) set to\t%s" % led_power)
print("Receiving message:\t%s\n" % msg + border_count * "=")
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def get_accuracy(count, accuracy, accuracy_avg, thread_done):
    if count <= 0:
        accuracy_avg = np.mean(accuracy)
        rt.stop()
        thread_done.set()
    read_msg, eol_detected = serial_manager.read_line(_timeout=0.03)
    acc = difflib.SequenceMatcher(None, read_msg, msg).ratio()
    if eol_detected:
        acc = (acc * len(msg) + 1) / (len(msg) + 1)
    accuracy = np.append(accuracy, acc)
    accuracy_avg = np.mean(accuracy)
    print("countdown: %i, accuracy: %f, received msg: %s" % (count, accuracy_avg, read_msg))
    count -= 1
    return [count, accuracy, accuracy_avg, thread_done]


accuracy_map = np.ones(shape=(2, 2))
for i, br in enumerate(baud_rate):
    for j, lp in enumerate(led_power):
        acc_avg = None
        serial_manager = serman.SerialManager()
        serial_manager.set_port("/dev/serial0")
        serial_manager.establish_connection(_baudrate=br, _timeout=0.03)
        # ====================================================================
        while True:
            rec_msg, eof_reached = serial_manager.read_line(_timeout=0.05)
            print(rec_msg.decode("ASCII", errors="replace"))
            # rec_msg = bytearray("hello there".encode("ASCII"))
            # rec_msg = struct.pack(">I", crc32(rec_msg)) + rec_msg
            if len(rec_msg) > 4:
                crc32_int_sent = struct.unpack(">I", rec_msg[:4])[0]
                crc32_int_calc = crc32(rec_msg[4:])
                print(40 * "=" + "\ncomparing %i and %i" % (crc32_int_sent, crc32_int_calc))
                if crc32_int_sent == crc32_int_calc:
                    print("SUUUUUCCCCCEEEEEEEEEEESS")

        # ===================================================================
        print("Waiting to close connection...")
        serial_manager.close_connection()
        print(40 * "=")

print("Measurements done!")
np.savetxt("~/project/test.csv", accuracy_map, delimiter=",")
print("Results saved!")
GPIO.output(17, 0)
