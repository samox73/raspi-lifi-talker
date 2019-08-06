import ast
import re
import sys
import threading
import time

import numpy as np
import RPi.GPIO as GPIO
import subprocess as sp

from ADCDACPi import *
from remotemanager import serman
from remotemanager.reptim import *
from remotemanager.clihelper import *
from remotemanager.pachel import *
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
adcdac.set_dac_voltage(1, 0.4)

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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # counter for statistics on transmission quality
    tx_fail = 0
    tx_success = 0

    # iterate over all baudrates and led powers
    for br in baud_rate:
        for lp in led_power:
            # init serial connection and set LED power
            serial_manager = serman.SerialManager()
            serial_manager.set_port("/dev/serial0")
            serial_manager.establish_connection(_baudrate=br, _timeout=0.05)
            set_led_power(lp)

            # transmit data
            with open(data_string, "rb") as file_tx:
                eof_reached = False
                transmission_timer = Timer()  # times the overall transmission time
                test = AvgTimer()  # times only the writing/sending process and averages over all values, when done
                while not eof_reached:  # until there is nothing more to read from the file, keep sending

                    pkt = bytearray(file_tx.read(packet_size))
                    # pkt = bytearray("Hello World!".encode("ASCII"))

                    # if the length of pkt is smaller than the packet size, the end of the file was reached
                    if len(pkt) < packet_size:
                        eof_reached = True
                        print("Time of total transmission:\t\t\t%.2fs" % (transmission_timer.get_value()))
                        print("Avg time to send a packet of %i bytes:\t%fs" % (packet_size, test.get_avg()))
                        return

                    # first 4 bytes contain the checksum, the rest is data
                    pkt = get_packet_of_msg(pkt, packet_size) + bytearray(b'\r\0\n')

                    # send message until a valid response is received or the number of tries is reached
                    send_success = False
                    number_of_tries = 0
                    while not send_success and number_of_tries < 500:
                        test.reset()
                        serial_manager.send_msg(pkt)
                        test.add_time()

                        # wait for response from receiver. If valid, break out of while loop
                        timer = Timer()  # measures the time of the read loop
                        while timer.get_value() < 0.05:  # while loop could eventually be deleted
                            response, eol_detected = serial_manager.read_line(_timeout=0.05)
                            if response == b"0x70":
                                send_success = True
                                tx_success += 1
                                break
                        number_of_tries += 1
                        if not send_success:
                            tx_fail += 1

                        # update the status of the transmission and print it
                        sent_bytes = packet_size * tx_success
                        if 0 <= sent_bytes <= 1024:
                            progress = "%.2fB" % sent_bytes
                        elif 1024 < sent_bytes <= 1048576:
                            progress = "%.2fKiB" % (sent_bytes / 1024)
                        elif 1048576 < sent_bytes:
                            progress = "%.2fMiB" % (sent_bytes / 1048576)
                        tmp = sp.call("clear", shell=True)
                        print(border_count * "=")
                        print(" > Failed:\t%i" % tx_fail)
                        print(" > Success:\t%i" % tx_success)
                        print(" > Sent bytes:\t%s" % progress)
                        print(border_count * "=")

                    if not send_success:
                        raise TimeoutError("Packet could not be transmitted after 1000 tries.")

            # =====================================================================
            time.sleep(0.1)
            serial_manager.close_connection()
            print(border_count * "=")

    print("Measurements done!")
    GPIO.output(17, 0)  # turn off LED


if __name__ == "__main__":
    main(sys.argv[1:])
