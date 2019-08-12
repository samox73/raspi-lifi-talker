import difflib
import struct
import sys
import threading
import time

import numpy as np
import RPi.GPIO as GPIO

from ADCDACPi import ADCDACPi
from ctypes import *
from remotemanager import serman
from remotemanager.reptim import *
from remotemanager.clihelper import *
from remotemanager.pachel import *
from threading import Timer
from zlib import crc32

"""
arguments of this script
python3 pi_sender.py {baud_rate} {led_power} {message}
[1] = baud rate (default: 460800)
[2] = led power in range 0-15 (default: 1)
[3] = string, value: either "custom" or "file" (default: "file")
[4] = string of message to transmit or filename (default: "test001.h5")
[5] = packet size in bytes (default: 1500) only for transmitting files
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

adcdac = ADCDACPi(1)
adcdac.set_adc_refvoltage(3.3)
adcdac.set_dac_voltage(1, 0.35)

helpstring = "Usage:"


def main(argv):

    baud_rate_valid = False
    led_power_valid = False

    # parse the CLI options given
    use_defaults, baud_rate, led_power, mode, data_string, packet_size, cvref, manual_input = get_cli_args(argv)

    if not manual_input:
        if use_defaults:
            baud_rate, led_power, mode, data_string, packet_size, cvref = force_defaults()
        else:
            # if variables dont have any value assign the default one
            baud_rate,led_power,mode,data_string,packet_size,cvref = set_missing_to_default(baud_rate,led_power,mode,data_string,packet_size,cvref)
        # use for manual input of parameters
    else:
        print("This is not yet implemented")
        sys.exit()
        # while not baud_rate_valid:
        #     baud_rate, baud_rate_valid = get_baud_rate()
        # while not led_power_valid:
        #     led_power, led_power_valid = get_led_power()
        # while not mode_valid:
        #     mode, mode_valid = get_mode()
        # while not packet_size_valid:
        #     packet_size, packet_size_valid = get_packet_size()
        # while not cvref_valid:
        #     cvref, cvref_valid = get_cvref()
        # if data_string is None or data_string == "":
        #     data_string = input("File/String to transmit (empty: '%s'): " % "test001.h5")
        # if data_string is None or data_string == "":
        #     data_string = "test001.h5"

    # check values of baudrate and led power
    baud_rate_valid, led_power_valid = assert_settings(baud_rate, led_power)
    if not baud_rate_valid:
        print("Argument of flag '-r' must be a valid integer or a list of integers, e.g. [50000, 100000, 200000, 400000]")
        sys.exit()
    if not led_power_valid:
        print("Argument of flag '-p' must be a valid integer or a list of integers in the range [0,15], e.g. [0, 5, 10, 15]")
        sys.exit()

    print(border_count * "=" + "\n > Baudrate(s) set to\t%s" % baud_rate)
    print(" > LED power(s) set to\t%s" % led_power)
    print(" > Transmitting %s:\t%s" % (mode, data_string))
    print(" > Package size set to:\t%i" % packet_size)
    print(" > CVRef set to:\t%.3f" % cvref)
    print(border_count * "=")
    print("Everything set up! Ready for signal transmission!")
    input("Hit enter to start... ")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # iterate over all baud rates and LED power levels
    for i, br in enumerate(baud_rate):
        for j, lp in enumerate(led_power):

            # init serial connection and set LED power
            serial_manager = serman.SerialManager()
            serial_manager.set_port("/dev/serial0")
            serial_manager.establish_connection(_baudrate=br, _timeout=0.1)
            set_led_power(lp)

            # initialize C serial connection for writing to serial buffer
            c_serial_manager = CDLL("./c_libraries/serial_sender.so")
            c_serial_port = c_serial_manager.set_serial_attributes()

            eof_reached = False
            success = 0
            while not eof_reached:  # read until end of file is detected
                rec_msg, eof = serial_manager.read_line(_timeout=1.0, _crc_length=4)
                # print(rec_msg)
                if len(rec_msg) > 4:
                    if struct.unpack(">I", rec_msg[:4])[0]==crc32(rec_msg[4:]):  # check if sent crc of data matches calculated one
                        serial_manager.send_msg(b"0x70\r\0\n")  # send confirmation, pySerial
                        # c_serial_manager.send_msg(c_serial_port, b"0x70\r\0\n", 4)  # send confirmation, own C program

            serial_manager.close_connection()

    print("Measurements done!")
    GPIO.output(17, 0)  # turn off LED


if __name__ == "__main__":
    main(sys.argv[1:])
