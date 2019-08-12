import difflib
import struct
import sys
import threading
import time

import numpy as np
import RPi.GPIO as GPIO
import subprocess as sp

from ADCDACPi import ADCDACPi
from ctypes import *
from remotemanager import serman
from remotemanager.reptim import *
from remotemanager.clihelper import *
from remotemanager.pachel import *
from threading import Timer
from zlib import crc32

"""
print the help text with 'python3 pi_receiver.py -h'
"""

# set up GPIO pins of raspi
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(25, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.output(17, 1)


def main(argv):

    # init variables
    baud_rate, led_power, mode, data_string, packet_size, cvref = init(argv)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # init serial connection and set LED power
    serial_manager = serman.SerialManager()
    serial_manager.set_port("/dev/serial0")
    serial_manager.establish_connection(_baudrate=baud_rate, _timeout=0.1)
    set_led_power(led_power)

    # initialize C serial connection for writing to serial buffer
    c_serial_manager = CDLL("./c_libraries/serial_sender.so")
    c_serial_port = c_serial_manager.set_serial_attributes()

    eof_reached = False
    rx_success = 0
    rx_fail = 0
    while not eof_reached:  # read until end of file is detected, currently an infty-loop
        rec_msg, eof = serial_manager.read_line(_timeout=100.0, _crc_length=4)
        if len(rec_msg) > 4:
            if struct.unpack(">I", rec_msg[:4])[0]==crc32(bytes(rec_msg[4:])):  # check if sent crc of data matches calculated one
                serial_manager.send_msg(b"0x70\r\0\n")  # send confirmation, pySerial
                # c_serial_manager.send_msg(c_serial_port, b"0x70\r\0\n", 4)  # send confirmation, own C program
                rx_success += 1
            else:
                rx_fail += 1

        # print stats
        print_stats(led_power, rx_fail, rx_success, packet_size, cvref, baud_rate, short=True)

    serial_manager.close_connection()

    print("Measurements done!")
    GPIO.output(17, 0)  # turn off LED


if __name__ == "__main__":
    main(sys.argv[1:])
