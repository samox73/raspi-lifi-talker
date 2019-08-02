import ast
import re
import numpy as np
import RPi.GPIO as GPIO

baud_rates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
border_count = 40  # length of border


def get_baud_rate():
    print("Available baudrates:")
    for index, item in enumerate(baud_rates):
        print("\t[%i] %i" % (index + 1, item))
    print("\t[%i] custom\n" % (len(baud_rates) + 1) + border_count * "=")
    idx = input("Selection [1-%i] (default: 460800): " % (len(baud_rates) + 1))
    idx = ast.literal_eval(str(idx))
    if not hasattr(idx, "__len__"):
        idx = [idx]
    _baud_rate = []
    for index in list(map(str, idx)):
        if index == str(len(baud_rates) + 1):
            _baud_rate.append(input("Custom baudrate (default: 2,000,000): "))
            if _baud_rate[-1] is None or _baud_rate[-1] == "":
                _baud_rate[-1]
            if not bool(re.match('^[0-9]+$', _baud_rate[-1])):
                print("Baud rate not valid!\n" + border_count * "=")
                _baud_rate = set_baud_rate()[0]
                return list(map(int, _baud_rate)), True
        elif index in np.arange(len(baud_rates) + 1).astype(str):
            _baud_rate.append(baud_rates[int(index) - 1])
        else:
            if index is None or index == "":
                _baud_rate.append(460800)
            else:
                print("Baud rate not valid!\n" + border_count * "=")
                _baud_rate = set_baud_rate()[0]
                return list(map(int, _baud_rate)), True
    return list(map(int, _baud_rate)), True


def get_led_power():
    print("Available LED power levels: 0-15")
    _led_power = input("LED power [0-15]: ")
    _led_power = ast.literal_eval(str(_led_power))
    if not hasattr(_led_power, "__len__"):
        _led_power = [_led_power]
    for item in list(map(str, _led_power)):
        if not bool(re.match('^[0-9]+$', item)):
            print("LED power not valid, enter a value between 0 and 15!\n" + border_count * "=")
            _led_power = get_led_power()[0]
        if int(item) not in np.arange(0, 16):
            print("LED power not valid, enter a value between 0 and 15!\n" + border_count * "=")
            _led_power = get_led_power()[0]
    return list(map(int, _led_power)), True


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


def assert_range(numbers, mini, maxi):
    for index, item in enumerate(numbers):
        if item < mini:
            # raise ValueError("Item '%s' at index %s is smaller than %s!" % (item, index, mini))
            print("Item '%s' at index %s is smaller than %s!" % (item, index, mini))
            return False
        if item > maxi:
            # raise ValueError("Item '%s' at index %s is larger than %s!" % (item, index, maxi))
            print("Item '%s' at index %s is larger than %s!" % (item, index, maxi))
            return False
    return True


def assert_settings(br, lp):  # detects if baudrate(s) and led power(s) are valid integers/integer lists
    if assert_valid_integer(br):
        b_r_valid = assert_range(list(map(int, br)), 9600, 4000000)
        if b_r_valid:
            print("Baudrates %s are valid!" % br)
    else:
        b_r_valid = False
    if assert_valid_integer(lp):
        l_p_valid = assert_range(list(map(int, lp)), 0, 15)
        if l_p_valid:
            print("LED power levels %s are valid!" % lp)
    else:
        l_p_valid = False
    return b_r_valid, l_p_valid


def assert_valid_integer(numbers):
    for index, item in enumerate(numbers):
        if not bool(re.match('^[0-9]+$', str(item))):
            # raise ValueError("Number %s at %s is not a valid integer!" % (item, index))
            return False
    return True
