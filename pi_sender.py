import sys
import time
import threading
import re
import ast
import RPi.GPIO as GPIO
import numpy as np
from zlib import crc32
from ADCDACPi import *
from remotemanager import serman
from remotemanager.reptim import *
from remotemanager.clihelper import *
from remotemanager.pachel import *

"""
arguments of this script
python3 pi_sender.py {baud_rate} {led_power} {message}
[1] = baud rate
[2] = led power in terms of PTX1/2/3/4R, e.g. 1248 for full power or 0001 for minimal power
[3] = string to transmit
"""

baud_rate_valid = False
led_power_valid = False
msg = ""


# ~~~~~~~~~~~~~~~~~ setting up all variables and connecting to the serial port ~~~~~~~~~~~~~~~~~~~
if len(sys.argv) == 4:
    filename = str(sys.argv[3])
elif len(sys.argv) == 3:
    filename = "test001.h5"
if len(sys.argv) >= 3:
    baud_rate = ast.literal_eval(str(sys.argv[1]))
    led_power = ast.literal_eval(str(sys.argv[2]))
    # convert to list if not already a list
    if not hasattr(baud_rate, "__len__"):
        baud_rate = [baud_rate]
    if not hasattr(led_power, "__len__"):
        led_power = [led_power]
    # validate values
    baud_rate_valid, led_power_valid = assert_settings(baud_rate, led_power)
    if baud_rate_valid:
        baud_rate = list(map(int, baud_rate))
    else:
        raise ValueError("Input baudrate(s) not valid!")
    if led_power_valid:
        led_power = list(map(int, led_power))
    else:
        raise ValueError("Input led power(s) not valid!")
else:
    while not baud_rate_valid:
        baud_rate, baud_rate_valid = get_baud_rate()
    while not led_power_valid:
        led_power, led_power_valid = get_led_power()

if msg is None or msg == "":
    filename = input("File to transmit (empty: 'test001.h5'): ")

if filename is None or msg == "":
    filename = "test001.h5"

print(border_count * "=" + "\nBaudrate(s) set to\t%s" % baud_rate)
print("LED power(s) set to\t%s" % led_power)
print("Transmitting file:\t%s\n" % filename + border_count * "=")

# set up GPIO pins of raspi
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(25, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.output(17, 1)

print("Everything set up! Ready for signal transmission!")

if len(sys.argv) == 1:
    input("Hit enter to start")
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def send_msg_countdown(*args):
    count = args[0]
    thread_done = args[1]
    if count <= 0:
        rt.stop()
        args[1].set()
    serial_manager.send_msg(msg)
    count -= 1
    return [count, thread_done]

tx_fail = 0
tx_success = 0
# iterate over all baudrates and led powers
for br in baud_rate:
    for lp in led_power:
        print("Establishing connection...")
        serial_manager = serman.SerialManager()
        serial_manager.set_port("/dev/serial0")
        serial_manager.establish_connection(_baudrate=br, _timeout=0.05)
        print("Established serial connection at port %s" % serial_manager.get_port())
        set_led_power(lp)
        print("Sending with baudrate %s and led power %s" % (br, lp))
        # =====================================================================
        with open(filename, "rb") as file_tx:
            eof_reached = False
            while not eof_reached:
                # first 4 bytes contain the checksum, the rest is data

                # pkt = bytearray("Hello World!".encode("ASCII"))
                pkt = bytearray(file_tx.read(100))
                # print(pkt)

                # if len(pkt) < 50:
                #     eof_reached = True
                pkt = get_packet_of_msg(pkt, 100)
                send_success = False
                number_of_tries = 0
                while not send_success and number_of_tries < 1000:
                    # print("SENDING MESSAGE: %s" % pkt)
                    serial_manager.send_msg(pkt + bytearray(b'\r\0\n'))
                    timer = Timer()
                    while timer.get_value() < 0.02:
                        response, eol_detected = serial_manager.read_line(_timeout=0.005)
                        if response == b"0x70":
                            print("success")
                            send_success = True
                            tx_success += 1
                            break
                    number_of_tries += 1
                    if not send_success:
                        tx_fail += 1
                    print("Failed:\t\t%i" % tx_fail)
                    print("Success:\t%i" % tx_success)
                    print(len(pkt))
                if not send_success:
                    raise TimeoutError("Packet could not be transmitted after 1000 tries.")
                # time.sleep(0.5)

        # =====================================================================
        thread_done.wait()
        time.sleep(0.5)
        serial_manager.close_connection()
        print(40 * "=")

print("Measurements done!")
GPIO.output(17, 0)
