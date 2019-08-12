from ctypes import *

c_serial_sender = CDLL("./serial_sender.so")

serial_port = c_serial_sender.set_serial_attributes()

msg_str = "Hello there, this is some really long and random string\r\0\n"
msg = c_char_p(msg_str.encode("ASCII"))
lngth = len(msg_str)
c_serial_sender.send_msg(serial_port, msg, lngth)
