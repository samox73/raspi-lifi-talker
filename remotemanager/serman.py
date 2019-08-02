import sys
import serial as pyserial
import time
from serial.tools import list_ports  # this may return differently named strings on different
# platforms, make sure to set verbose=True in method detect_port to debug errors

"""
- Make sure all Tx are connected to an Rx!
- If not connected, the timeout specified upon the initialization of the pyserial.serial object will  
"""


class SerialManager:
    def __init__(self, _port=""):
        self.port = _port
        self.serial_con = None

    def detect_port(self, verbose=True):
        # configure the serial connections (the parameters differs on the device you are connecting to)
        ports_list = []  # list of ports of all ttl232 capable devices
        connection_log = ""  # a string for writing to a CLI/GUI-log
        com_ports = list(list_ports.comports())
        for port_no, description, address in com_ports:
            if verbose:
                connection_log += "port_no:\t%s\n" % port_no
                connection_log += "description:\t%s\n" % description
                connection_log += "address:\t%s\n" % address
            # if 'Product' in description:
                # ports_list.append(port_no)
            ports_list.append(port_no)
        if verbose:
            connection_log += "Found the following com-ports: %s\n" % ports_list
        if len(ports_list) == 0:
            print('no suitable serial port (fr: pas de port serie convenable)')
        else:
            connection_log += "Selecting port %s" % ports_list[0]
            self.port = ports_list[0]
        return connection_log

    def get_port(self):
        return self.port

    def set_port(self, _port):
        self.port = _port
        return

    def close_connection(self):
        if self.serial_con is not None:
            if self.serial_con.is_open:
                print("Closing connection")
                self.serial_con.close()
        return

    def establish_connection(self, _baudrate=9600, _timeout=1):
        self.serial_con = pyserial.Serial(
            port=self.port,
            baudrate=_baudrate,
            parity=pyserial.PARITY_NONE,
            stopbits=pyserial.STOPBITS_ONE,
            bytesize=pyserial.EIGHTBITS,
            timeout=_timeout
        )
        return

    def send_msg(self, _msg):
        if self.serial_con is None:
            print("serial_con is 'None'. Open a serial connection first!")
            return
        if self.serial_con.is_open:
            try:
                self.serial_con.flushInput()  # flush input buffer, discarding all its contents
                self.serial_con.flushOutput()  # flush output buffer, aborting current output
                # and discard all that is in buffer

                # print("Sending message %s" % _msg)
                self.serial_con.write(_msg)
                # print("Message sent!")

                self.serial_con.flush()
            except IOError:
                print('error communicating...')
        else:
            print('cannot open serial port')
        return

    def read_line(self, _eol_character=b'\r\0\n', _timeout=0.05, _crc_length=4):
        buffer = b""
        eol_buffer = bytearray("000".encode("ASCII"))
        timer = time.time()  # start time of read_line
        stopwatch = time.time() - timer  # time consumption of this method
        time_a = time.time()
        byte_count = 0
        while stopwatch < _timeout:
            delta_t = time.time() - time_a  # delta t after updating the "Elapsed time"
            if delta_t > _timeout:
                time_a = time.time()
            one_byte = self.serial_con.read(1)
            if not one_byte == b'':
                byte_count += 1
                eol_buffer.pop(0)
                eol_buffer += one_byte
            # print("byte: %s\nbyte count: %i" % (one_byte, byte_count))
            if eol_buffer == bytearray(_eol_character) and byte_count > _crc_length:
                return bytearray(buffer[:-2]), True
            else:
                buffer += one_byte
            stopwatch = time.time() - timer
        return bytearray(buffer), False
