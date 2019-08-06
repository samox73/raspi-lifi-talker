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
                self.serial_con.reset_output_buffer()  # delete contents of input buffer
                self.serial_con.reset_input_buffer()  # delete contents of output buffer
                self.serial_con.write(_msg)
                self.serial_con.flush()  # flush the message in the buffer
            except IOError:
                print('error communicating...')
        else:
            print('cannot open serial port')
        return

    def read_line(self, _eol_character=b'\r\0\n', _timeout=0.05, _crc_length=4):
        buff = b""
        timer = time.time()  # start time of read_line
        while time.time()-timer < _timeout:
            waiting_bytes = self.serial_con.in_waiting
            buff += self.serial_con.read(waiting_bytes)
            if _eol_character in buff: #[:-(waiting_bytes+2)]:
                return bytearray(buff[:-3]), True
        return bytearray(buff), False
