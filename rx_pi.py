import difflib
import struct
import sys
import threading
import time

import numpy as np
import RPi.GPIO as GPIO
import subprocess as sp

from ctypes import *
from remotemanager import serman
from remotemanager.reptim import *
from remotemanager.clihelper import *
from remotemanager.pachel import *
from threading import Timer
from zlib import crc32

"""
print the help text with 'python3 rx_pi.py -h'
"""


def main(argv):

    # init variables
    baud_rate, led_power, mode, data_string, packet_size, cvref, number_of_transmissions, verbose = init(argv)

    # set up GPIO pins of raspi
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.OUT)
    GPIO.setup(23, GPIO.OUT)
    GPIO.setup(25, GPIO.OUT)
    GPIO.setup(27, GPIO.OUT)
    GPIO.setup(22, GPIO.OUT)
    GPIO.output(17, 1)

    # init serial connection and set LED power
    serial_manager = serman.SerialManager()
    serial_manager.set_port("/dev/serial0")
    serial_manager.establish_connection(_baudrate=baud_rate, _timeout=0.1)
    set_led_power(led_power)

    # counter for successful/failed transmission of packets
    rx_success = 0
    rx_fail = 0

    # variables for determining if packet was already received successfully
    packet_number = 0
    packet_number_last = -1

    with open(data_string, "wb") as file_rx:
        eof_reached = False  # boolean for while (read) loop
        print("Waiting for incoming packets...")

        while not eof_reached:  # read until end of file is detected
            rec_msg, eof_reached = serial_manager.read_line(_timeout=1000.0, _crc_length=4)
            if len(rec_msg) > 8:
                # first 4 bytes of the packet are the CRC32 checksum, next 4 bytes the packet number and rest is data
                if struct.unpack(">I", rec_msg[:4])[0]==crc32(bytes(rec_msg[8:])):  # check if sent checksum matches the calculated one
                    serial_manager.send_msg(b"0x70\r\0\n")  # send confirmation, pySerial
                    # c_serial_manager.send_msg(c_serial_port, b"0x70\r\0\n", 4)  # send confirmation, own C program

                    # check if packet patches the last packet; needed if confirmation message was not sent successfully
                    packet_number = struct.unpack(">I", rec_msg[4:8])[0]
                    if packet_number != packet_number_last:
                        file_rx.write(rec_msg[8:])
                        packet_number_last = packet_number

                    rx_success += 1
                else:
                    rx_fail += 1
            if eof_reached:
                serial_manager.send_msg(b"0x70\r\0\n")  # send confirmation, pySerial


            # print stats
            print_stats(led_power, rx_fail, rx_success, packet_size, cvref, baud_rate, verbose)
            print("Packet number: %i" % int(packet_number))

    print("EOF Reached...\nTransmission successful!")
    serial_manager.close_connection()

    GPIO.output(17, 0)  # turn off LED


if __name__ == "__main__":

    if sys.version_info < (3, 0):
        print("Sorry, requires Python 3.x, not 2.x!")
        sys.exit(1)

    main(sys.argv[1:])
