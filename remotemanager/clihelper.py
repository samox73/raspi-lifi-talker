import ast
import getopt
import re
import sys
import numpy as np
import RPi.GPIO as GPIO
import subprocess as sp

from ADCDACPi import *

helpstring = "Usage: python3 {rx_pi.py/tx_pi.py} [OPTION]\nTransmitter/Receiver-end of a Li-fi communication \
system.\nExample: python3 tx_pi.py -m 'custom' -i 'Test string' -r 460800 -p 15 \
\n         python3 tx_pi.py -m file -i test001.h5 -r 9600 -p 5\
\n         python3 rx_pi.py --mode=file --input=test.png --baudrate=115200\
\n\nOptions:\n  \
-r\t--baudrate\t\tBaud rate (default: 460800)\n  \
-p\t--ledpower\t\tLED Power (1-15, default: 15)\n  \
-m\t--mode\t\t\tMode (\"file\", \"custom\", default: \"file\")\n  \
-i\t--input\t\t\tFilename/Custom string (e.g. \"test001.h5\" or \"Hello, World!\", default: \"test001.h5\")\n  \
-h\t--help\t\t\tDisplay this help text end exit\n  \
-s\t--packetsize\t\tSet the size of the transmitted packages in bytes (default: 1500)\n  \
-c\t--cvref\t\t\tSet reference voltage CVRef (default: 0.35)\n  \
-n\t\t\t\tWith mode = \"file\": number of tries to send a package, followed by an exception\n\t\t\t\t     mode =\
 \"custom\": number of times the specified string is transmitted\n\t\t\t\t(default: 500)\n  \
-v\t--verbose\t\tVerbose, print more stats (use only on tx, can lead to inaccurate measurements on rx side)\n  \
-d\t--force-defaults\tForce the use of default values\n\n\
If a value is needed for the connection but not specified, then the default value will be used."

baud_rates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
border_count = 100  # length of border

# default values
br_df = 460800
lp_df = 15
md_df = "file"
dt_df = "test001.h5"
ps_df = 1500
cr_df = 0.35
not_df = 500
vb_df = False


def set_led_power(_led_power):
    power = [0, 0, 0, 0]
    if _led_power >= 1:
        power[0] = 1
    if _led_power >= 2:
        if _led_power <= 3:
            power[1] = (_led_power - 1)
        else:
            power[1] = 2
    if _led_power >= 4:
        if _led_power <= 7:
            power[2] = (_led_power - 3)
        else:
            power[2] = 4
    if _led_power >= 8:
        power[3] = (_led_power - 7)
    GPIO.output(23, power[0])
    GPIO.output(25, power[1])
    GPIO.output(27, power[2])
    GPIO.output(22, power[3])


def assert_range(number, mini, maxi):
    if number < mini:
        print("Item '%s' at index %s is smaller than %s!" % (item, index, mini))
        return False
    if number > maxi:
        print("Item '%s' at index %s is larger than %s!" % (item, index, maxi))
        return False
    return True


def assert_settings(br, lp):  # detects if baudrate(s) and led power(s) are valid integers/integer lists
    if assert_valid_integer(br):
        b_r_valid = assert_range(int(br), 9600, 4000000)
        if b_r_valid:
            print("Baudrates %s are valid!" % br)
    else:
        b_r_valid = False
    if assert_valid_integer(lp):
        l_p_valid = assert_range(int(lp), 0, 15)
        if l_p_valid:
            print("LED power levels %s are valid!" % lp)
    else:
        l_p_valid = False
    return b_r_valid, l_p_valid


def assert_valid_integer(number):
    if not bool(re.match('^[0-9]+$', str(number))):
        return False
    return True

def get_cli_args(argv):

    use_defaults = False
    baud_rate = None
    led_power = None
    mode = None
    data = None
    packet_size = None
    cvref = None
    number_of_transmissions = None
    verbose = None

    try:
        opts, args = getopt.getopt(argv, "hr:p:m:i:s:c:n:vd", ["help", "baudrate=", "ledpower=", "mode=",
            "input=", "packetsize=", "cvref=", "verbose", "force-defaults"])
    except getopt.GetoptError:
        print("Wrong use of arguments, see 'pi_sender.py -h' for details")
        sys.exit()
    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            print(helpstring)
            sys.exit()
        elif opt in ["-r", "--baudrate"]:  # BAUD RATE
            baud_rate = ast.literal_eval(str(arg))
        elif opt in ["-p", "--ledpower"]:  # LED POWER
            led_power = ast.literal_eval(str(arg))
        elif opt in ["-m", "--mode"]:  # MODE
            if arg == "custom":
                mode = "custom"
            elif arg == "file":
                mode = "file"
            else:
                print("Wrong usage of flag '-m', should either be 'custom' or 'file'")
                sys.exit()
        elif opt in ["-i", "--input"]:  # FILENAME/STRING
            data = str(arg)
        elif opt in ["-s", "--packetsize"]:  # PACKET SIZE
            try:
                packet_size = int(arg)
            except ValueError:
                print("Argument of flag '-s' must be a valid integer")
        elif opt in ["-c", "--cvref"]:  # CVREF
            try:
                cvref = float(arg)
            except ValueError:
                print("Argument of flag '-v' must be a valid float between 0 and 1")
            if cvref < 0 or cvref > 10:
                print("CVRef must be in [0,1]!")
                sys.exit()
        elif opt in ["-n"]:
            number_of_transmissions = ast.literal_eval(str(arg))
        elif opt in ["-v", "--verbose"]:
            verbose = True
        elif opt in ["-d", "--force-defaults"]:  # DEFAULT VALUES
            use_defaults = True
        else:
            print("Unknown flag %s, use -h for help." % opt)
            sys.exit()
    return use_defaults, baud_rate, led_power, mode, data, packet_size, cvref, \
number_of_transmissions, verbose

def set_missing_to_default(baud_rate, led_power, mode, data, packet_size, cvref, n_of_transmissions, \
        verbose):
    # if variables dont have any value assign the default one
    if baud_rate == "" or baud_rate is None:
        baud_rate = br_df
    if led_power == "" or led_power is None:
        led_power = lp_df
    if mode == "" or mode is None:
        mode = md_df
    if data == "" or data is None:
        data = dt_df
    if packet_size is None:
        packet_size = ps_df
    if cvref is None:
        cvref = cr_df
    if n_of_transmissions is None:
        n_of_transmissions = not_df
    if verbose is None:
        verbose = vb_df
    return baud_rate, led_power, mode, data, packet_size, cvref, n_of_transmissions, verbose

def force_defaults():
    return br_df, lp_df, md_df, dt_df, ps_df, cr_df, not_df, vb_df

def print_stats(lp, tx_fail, tx_success, packet_size, cvref, br, mode=None, data_string=None, verbose=False, filesize=None, \
                sent_bytes = None):
    """
    prints the statistics of the current transmission
    lp: led power (int)
    tx_fail: failed transmissions on the transmitter end (int)
    tx_success: successful transmissions on the transmitter end (int)
    packet_size: size of the transmitted package in bytes (int)
    """
    tmp = sp.call("clear", shell=True)
    print(border_count * "=")
    if verbose and sent_bytes is not None:
        if 0 <= sent_bytes <= 1024:
            progress = "%.2fB" % sent_bytes
        elif 1024 < sent_bytes <= 1048576:
            progress = "%.2fKiB" % (sent_bytes / 1024)
        elif 1048576 < sent_bytes:
            progress = "%.2fMiB" % (sent_bytes / 1048576)
        print(" > Baud rate:\t\t%i" % br)
        print(" > LED Power:\t\t%i" % lp)
        if mode is not None and data_string is not None:
            print(" > Transmitting %s:\t%s" % (mode, data_string))
        print(" > Package size:\t%s" % packet_size)
        print(" > CVRef:\t\t%.3f" % cvref)
    tx_count = tx_fail + tx_success
    print(" > Failed:\t\t%.3f%% (%i/%i)" % (tx_fail / tx_count * 100, tx_fail, tx_count))
    print(" > Success:\t\t%.3f%% (%i/%i)" % (tx_success / tx_count * 100, tx_success, tx_count))
    if verbose and sent_bytes is not None:
        print(" > Sent bytes:\t\t%s" % progress)
        print("\n\n" + 45 * "=" + " Progress " + 45 * "=")
        percentage = sent_bytes / filesize * 100
        percentage_int = int(percentage)
        digit = str(int(10 * (percentage - percentage_int)))
        if percentage_int == 100:
            digit = ""
        print(int(percentage) * "#" + digit + \
              (99 - percentage_int) * "." + "| %i%%" % percentage_int)
    print(border_count * "=")

def init(argv, tx=True):

    adcdac = ADCDACPi(1)
    adcdac.set_adc_refvoltage(3.3)

    baud_rate_valid = False
    led_power_valid = False

    # parse the CLI options given
    use_defaults, baud_rate, led_power, mode, data_string, packet_size, cvref, number_of_transmissions, \
verbose = get_cli_args(argv)

    if use_defaults:
        baud_rate, led_power, mode, data_string, packet_size, cvref, number_of_transmissions, verbose = force_defaults()
    else:
        # if variables dont have any value assign the default one
        baud_rate, led_power, mode, data_string, packet_size,cvref, number_of_transmissions, verbose = \
        set_missing_to_default(baud_rate, led_power, mode, data_string, packet_size, cvref, \
                               number_of_transmissions, verbose)

    # check values of baudrate and led power
    baud_rate_valid, led_power_valid = assert_settings(baud_rate, led_power)
    if not baud_rate_valid:
        print("Argument of flag '-r' must be a valid integer")
        sys.exit()
    if not led_power_valid:
        print("Argument of flag '-p' must be a valid integer in range [0, 15]")
        sys.exit()

    # set reference voltage of rectifier
    adcdac.set_dac_voltage(1, float(cvref))

    print(border_count * "=" + "\n > Baudrate set to\t%s" % baud_rate)
    print(" > LED power set to\t%s" % led_power)
    if tx:
        print(" > Transmitting %s:\t%s" % (mode, data_string))
    else:
        print(" > Receiving packets")
    print(" > Package size set to:\t%s" % packet_size)
    print(" > CVRef set to:\t%.3f" % cvref)
    print(border_count * "=")
    print("Everything set up! Ready for signal transmission!")
    # input("Hit enter to start... ")
    return baud_rate, led_power, mode, data_string, packet_size, cvref, number_of_transmissions, verbose
