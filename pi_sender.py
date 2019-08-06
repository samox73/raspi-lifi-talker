import ast
import getopt
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

    use_defaults = True
    baud_rate = None
    led_power = None
    mode = None
    data = None
    packet_size = None
    cvref = None

    # parse the CLI options given
    try:
        opts, args = getopt.getopt(argv, "hr:p:m:i:s:v:d")
    except getopt.GetoptError:
        print("Wrong use of arguments, see 'pi_sender.py -h' for details")
        sys.exit()
    for opt, arg in opts:
        if opt == "-h":
            print(helpstring)
            sys.exit()
        elif opt in ["-r"]:
            baud_rate = ast.literal_eval(str(arg))
        elif opt in ["-p"]:
            led_power = ast.literal_eval(str(arg))
        elif opt in ["-m"]:
            if arg == "custom":
                mode = "custom"
            elif arg == "file":
                mode = "file"
            else:
                print("Wrong usage of flag '-m', should either be 'custom' or 'file'")
                sys.exit()
        elif opt in ["-i"]:
            data = str(arg)
        elif opt in ["-s"]:
            try:
                packet_size = int(arg)
            except ValueError:
                print("Argument of flag '-s' must be a valid integer")
        elif opt in ["-v"]:
            try:
                cvref = float(arg)
            except ValueError:
                print("Argument of flag '-v' must be a valid float between 0 and 1")
            if cvref < 0 or cvref > 1:
                print("CVRef must be in [0,1]!")
                sys.exit()
        elif opt in ["-d"]:
            use_defaults = False
        else:
            print("Unknown flag %s, use -h for help." % opt)
            sys.exit()

    if use_defaults:
        # if variables dont have any value assign the default one
        if baud_rate == "" or baud_rate is None:
            baud_rate = [460800]
        if led_power == "" or led_power is None:
            led_power = [1]
        if mode == "" or mode is None:
            mode = "file"
        if data == "" or data is None:
            # data = "arch-bg.jpg"
            data = "test001.h5"
        if packet_size is None:
            packet_size = 1500
        if cvref is None:
            cvref = 0.4
    # use for manual input of parameters
    else:
        while not baud_rate_valid:
            baud_rate, baud_rate_valid = get_baud_rate()
        while not led_power_valid:
            led_power, led_power_valid = get_led_power()
    if data is None or data == "":
        data = input("File to transmit (empty: '%s'): " % "arch-bg.jpg")
    if data is None or data == "":
        data = "arch-bg.jpg"

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
    print(" > Transmitting %s:\t%s" % (mode, data))
    print(" > Package size set to:\t%i" % packet_size)
    print(" > CVRef set to:\t%.3f" % cvref)
    print("Everything set up! Ready for signal transmission!")
    print(border_count * "=")
    input("Hit enter to start")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
            with open(data, "rb") as file_tx:
                eof_reached = False
                transmission_timer = Timer()
                test = AvgTimer()
                while not eof_reached:
                    # first 4 bytes contain the checksum, the rest is data

                    # pkt = bytearray("Hello World!".encode("ASCII"))
                    pkt = bytearray(file_tx.read(packet_size))
                    if len(pkt) == 0:
                        eof_reached = True
                        print("Time of total transmission:\t\t\t%.2fs" % (transmission_timer.get_value()))
                        print("Avg time to send a packet of %i bytes:\t%fs" % (packet_size, test.get_avg()))
                        return

                    pkt = get_packet_of_msg(pkt, packet_size)
                    send_success = False
                    number_of_tries = 0
                    while not send_success and number_of_tries < 500000:
                        # print("SENDING MESSAGE: %s" % pkt)
                        test.reset()
                        serial_manager.send_msg(pkt + bytearray(b'\r\0\n'))
                        test.add_time()
                        timer = Timer()
                        while timer.get_value() < 0.05:
                            response, eol_detected = serial_manager.read_line(_timeout=0.05)
                            if response == b"0x70":
                                # print("success")
                                send_success = True
                                tx_success += 1
                                break
                        number_of_tries += 1
                        if not send_success:
                            tx_fail += 1

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
                    # time.sleep(0.5)

            # =====================================================================
            time.sleep(0.5)
            serial_manager.close_connection()
            print(40 * "=")

    print("Measurements done!")
    GPIO.output(17, 0)


if __name__ == "__main__":
    main(sys.argv[1:])
