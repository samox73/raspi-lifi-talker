import sys
import time
from zlib import crc32
from functools import partial
import struct


def get_packet_of_msg(msg_as_bytearray, length=1500):
    """
    msg_as_bytearray: bytearray of data, which is filled up with zeros at the end, if not large enough
    """
    msg_as_bytearray = msg_as_bytearray.ljust(length, b"\x00")
    msg_crc32_int = crc32(msg_as_bytearray)
    msg_crc32 = struct.pack(">I", msg_crc32_int)
    msg_crc32 = bytearray(msg_crc32.ljust(4, b"\x00"))
    msg = msg_crc32 + msg_as_bytearray
    return msg


class Timer:
    def __init__(self):
        self.start_time = time.time()
        self.duration = 0
        return

    def get_value(self):
        self.duration = time.time() - self.start_time
        return self.duration


class PackageManager:
    def send_packet(serial_manager, event_received, packet, length=1500):
        packet = get_packet_of_msg(packet, length=length)
        serial_manager.send_msg(packet)
        received = False
        while not received:
            serial_manager.read_line()
