import ast
import re
import sys
import threading
import time

import numpy as np
import RPi.GPIO as GPIO

from ctypes import *
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


def main(argv):

    # init variables
    baud_rate, led_power, mode, data_string, packet_size, cvref = init(argv)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # counter for statistics on transmission quality
    tx_fail = 0
    tx_success = 0

    # init serial connection and set LED power
    serial_manager = serman.SerialManager()
    serial_manager.set_port("/dev/serial0")
    serial_manager.establish_connection(_baudrate=baud_rate, _timeout=0.05)
    set_led_power(led_power)

    # initialize C serial connection for writing to the serial buffer
    c_serial_manager = CDLL("./c_libraries/serial_sender.so")
    c_serial_port = c_serial_manager.set_serial_attributes()


    # transmit binary data file
    if mode == "file":

        # open file for reading
        with open(data_string, "rb") as file_tx:

            eof_reached = False  # initialize end of file boolean for following while loop
            transmission_timer = Timer()  # times the overall transmission time
            test = AvgTimer()  # times only the writing/sending process and averages over all values, when done
            while not eof_reached:  # until there is nothing more to read from the file, keep sending

                pkt = bytearray(file_tx.read(packet_size))

                # if the length of pkt is smaller than the packet size, the end of the file was reached
                if len(pkt) < packet_size:
                    eof_reached = True
                    transmission_time = transmission_timer.get_value()
                    print("Time of total transmission:\t\t\t%.2fs" % transmission_time)
                    print("Avg time to send a packet of %i bytes:\t%fs" % (packet_size, test.get_avg()))
                    break

                # first 4 bytes contain the checksum, the rest is data
                pkt = bytes(get_packet_of_msg(pkt, packet_size) + bytearray(b'\r\0\n'))

                # send message until a valid response is received or the number of tries is reached
                send_success = False
                number_of_tries = 0
                while not send_success and number_of_tries < 500:
                    # serial_manager.send_msg(pkt)  # send data with pySerial
                    c_serial_manager.send_msg(c_serial_port, pkt, len(pkt))  # send data with self-written C function
                    test.add_time()
                    test.reset()

                    # wait for response from receiver. If valid, break out of while loop
                    timer = Timer()  # measures the time of the read loop
                    # while timer.get_value() < 0.05:  # while loop could eventually be deleted
                    response, eol_detected = serial_manager.read_line(_timeout=0.05)
                    if response == b"0x70":
                        send_success = True
                        tx_success += 1
                    #    break
                    number_of_tries += 1
                    if not send_success:
                        tx_fail += 1

                    # update the status of the transmission and print it
                    print_stats(led_power, tx_fail, tx_success, packet_size, cvref, baud_rate, mode, data_string)

                if not send_success:
                    raise TimeoutError("Packet could not be transmitted after 1000 tries.")

    # transmit a custom string
    elif mode == "custom":
        transmission_count = 500  # number of total transmissions
        transmission_timer = Timer()  # times the overall transmission time
        test = AvgTimer()  # times only the writing/sending process and averages over all values, when done
        tries = 0
        while tries < transmission_count:  # send 500 messages

            tries += 1

            # first 4 bytes contain the checksum, the rest is data
            pkt = bytearray(data_string.encode("ASCII"))
            pkt = bytes(get_packet_of_msg(pkt, packet_size) + bytearray(b'\r\0\n'))

            test.reset()  # start timer
            # serial_manager.send_msg(pkt)  # send data with pySerial
            c_serial_manager.send_msg(c_serial_port, pkt, len(pkt))  # send data with self-written C function
            test.add_time()  # save time to class-internal array

            # read response from receiver
            response, eol_detected = serial_manager.read_line(_timeout=0.05)
            if response == b"0x70":
                send_success = True
                tx_success += 1
            else:
                tx_fail += 1

            # update the status of the transmission and print it
            print_stats(led_power, tx_fail, tx_success, packet_size, cvref, baud_rate, mode, data_string, short=True)
    # =====================================================================

    serial_manager.close_connection()  # close connection to serial port
    print("Measurements done!")
    GPIO.output(17, 0)  # turn off LED


if __name__ == "__main__":
    main(sys.argv[1:])


