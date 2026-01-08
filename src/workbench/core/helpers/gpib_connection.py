import logging
import serial
import time
import sys
import glob

LOGGER = logging.getLogger(__name__)

class GPIBConnection:
    def __init__(self, port : str = None, gpib_address=None, baudrate=9600, timeout=1):
        self.name = "USB-GPIB connection"
        self._port = port
        self._baudrate = baudrate
        self._gpib_address = gpib_address
        self._timeout = timeout
        self.ser = None
    
    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        LOGGER.debug(f"{self.name}: Changing port to {value}")
        self._port = value

    @property
    def baudrate(self):
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value):
        LOGGER.debug(f"{self.name}: Changing baud rate to {value}")
        self._baudrate = value

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        LOGGER.debug(f"{self.name}: Changing timeout to {value}")
        self._timeout = value
    
    @property
    def gpib_address(self):
        return self._gpib_address

    @gpib_address.setter
    def gpib_address(self, value):
        LOGGER.debug(f"{self.name}: Changing GPIB address to {value}")
        self._gpib_address = value
        if self.ser:
            self._gpib_write(f'++addr {value}')

    def gpib_connect(self) -> bool:
        """
        Connects to the previously defined GPIB address through the previously specified USB port.
        Returns:
        - _False_ if connection failed or port/gpib_address is None
        - _True_ if connection successful

        """
        if self.port != None:
            self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
            time.sleep(0.5)
            if self.ser != None:    
                LOGGER.info(f"Connected to port {self.port}.")
            else:
                LOGGER.error(f"Unable to connecto to port {self.port}")
                return False
            
            if self.gpib_address is None:
                LOGGER.error(f"{self.name}: USB connection established, but GPIB address not defined.")
                return False
            else:
                LOGGER.info(f"{self.name}: Connecting to GPIB address {self.gpib_address} through port {self.port}")
                self._gpib_write('++mode 1')       # Modo controlador
                self._gpib_write('++auto 0')       # Lectura manual
                self._gpib_write(f'++addr {self.gpib_address}')  # Dirección GPIB
                return True
        else:
            LOGGER.error(f"No port selected")
            return False

    def _gpib_write(self, command):
        if self.ser:
            self.ser.write((command + '\n').encode())

    def gpib_send_command(self, command):
        """Envía un comando GPIB al instrumento"""
        LOGGER.debug(f"{self.name}: sending GPIB command \"{command}\"")
        self._gpib_write(command)

    def gpib_query(self, command):
        """Envía un comando y lee la respuesta"""
        LOGGER.debug(f"{self.name}: sending GPIB query \"{command}\"")
        self._gpib_write(command)
        self._gpib_write('++read eoi')
        response = self.ser.readline().decode().strip()
        LOGGER.debug(f"{self.name}: GPIB responded \"{command}\"")
        return response

    # def set_gpib_address(self, address):
    #     self.gpib_address = address
    #     self._gpib_write(f'++addr {address}')
    
    def scan_gpib_addresses(self, start=0, end=30, test_command='*IDN?'):
        """Scan GPIB addressed, returns the first one that responds"""
        LOGGER.info(f"{self.name}: Scanning GPIB addreses")
        for addr in range(start, end + 1):
            LOGGER.debug(f"{self.name}: Trying GPIB address {addr}")
            self.gpib_address = addr
            self._gpib_write(test_command)
            self._gpib_write('++read eoi')
            time.sleep(0.2)
            response = self.ser.readline().decode().strip()
            if response:
                return (addr, response)
        return (-1, -1)

    def close(self):
        if self.ser:
            LOGGER.info(f"{self.name}: closing connection")
            self.ser.close()
            self.ser = None
        else:
            LOGGER.info(f"{self.name}: connecton is closed")


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result