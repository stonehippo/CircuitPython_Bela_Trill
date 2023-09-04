import time
import struct

from adafruit_bus_device import i2c_device
from micropython import const

try:
    from busio import I2C
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/stonehippo/CircuitPython_Bela_Trill.git"

class Touch:
    def __init__(self, location = 0, size = 0) -> None:
        self.location = location
        self.size = size

# Modes for reading a Trill device
class TrillMode:
    AUTO = const(-1)
    CENTROID = const(0)
    RAW = const(1)
    BASELINE = const(2)
    DIFF = const(3)    

# Trill device types
_TRILL_DEVICE_NONE = const(-1)
_TRILL_DEVICE_UNKNOWN = const(0)
_TRILL_DEVICE_BAR = const(1)
_TRILL_DEVICE_SQUARE = const(2)
_TRILL_DEVICE_CRAFT = const(3)
_TRILL_DEVICE_RING = const(4)
_TRILL_DEVICE_HEX = const(5)
_TRILL_DEVICE_FLEX = const(6)

_CMD_NONE = const(0)
_CMD_MODE = const(1)
_CMD_SCAN_SETTINGS = const(2)
_CMD_PRESCALER = const(3)
_CMD_NOISE_THRESHOLD = const(4)
_CMD_IDAC = const(5)
_CMD_BASELINE_UPDATE = const(6)
_CMD_MINIMUM_SIZE = const(7)
_CMD_AUTO_SCAN_INTVL = const(16)
_CMD_IDENTIFY = const(255)

# intercommand delay (in seconds)
_CMD_DELAY = 0.015

_MAX_TOUCH_1D = const(5)
_MAX_TOUCH_2D = const(4)

_OFFSET_CMD = const(0)
_OFFSET_DATA = const(4)

_CENTROID_LENGTH_DEFAULT = const(20)
_CENTROID_LENGTH_RING = const(24)
_CENTROID_LENGTH_2D = const(32)
_RAW_LENGTH = const(60)
_RAW_LENGTH_BAR = const(52)
_RAW_LENGTH_HEX = const(60)
_RAW_LENGTH_RING = const(56)

_PRESCALER_MAX = const(8)
# valid values for the speed parameter in scan settings
_TRILL_SPEED = range(0,4)

# max values for each board type; see https://learn.bela.io/using-trill/trill-and-arduino/#reading-from-the-sensor
# BAR_POSITION_MAX = 3200
# BAR_SIZE_MAX = 4566
# RING_POSITION_MAX = 3456
# RING_SIZE_MAX = 5000
# SQUARE_POSITION_MAX = 1792
# SQUARE_SIZE_MAX = 3780
# HEX_POSITION_MAX = 1920
# HEX_SIZE_MAX = 4000
# FLEX_POSITION_MAX = 3712
# FLEX_SIZE_MAX = 1200

class Trill:
    @staticmethod
    def process_centroids(data) -> list:
        return []
    
    @staticmethod
    def process_centroid_bytes(l, x) -> list:
        return [l[i+1] + (l[i] << 8) for i in range(0,len(l), x)]

    @staticmethod
    def is_valid_address(address, first, last) -> bool:
        if address not in range(first, last + 1):
            raise ValueError("address not valid")
    
    def __init__(self, i2c_bus: I2C, type=_TRILL_DEVICE_UNKNOWN, address=0xFF, mode=TrillMode.CENTROID):
        self._address = address
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        
        self._type, self._version = self.identify()

        if self._type is not type:
            raise Exception(f"Device identifies as type {self._type}; expected type {type}")

        self.set_mode(mode)
        time.sleep(_CMD_DELAY)
        self.set_scan_settings(0, 12)
        time.sleep(_CMD_DELAY)
        self.update_baseline()
        time.sleep(_CMD_DELAY) # give the system enough time to get set up before taking user interactions

        self.vertical_touches = []
        self.horizontal_touches = []

    # does the device has a single axis for sensing?
    def is_1D(self) -> bool:
        if self._mode is not TrillMode.CENTROID:
            return False
        switch = {
            _TRILL_DEVICE_BAR: True,
            _TRILL_DEVICE_RING: True,
            _TRILL_DEVICE_CRAFT: True,
            _TRILL_DEVICE_FLEX: True,
        }
        return switch.get(self._type, False)
    
    # does does ths device have two axes for sensing?
    def is_2D(self) -> bool:
        if self._mode is not TrillMode.CENTROID:
            return False
        switch = {
            _TRILL_DEVICE_HEX: True,
            _TRILL_DEVICE_SQUARE: True,
        }
        return switch.get(self._type, False)
    
    # get the type of the device
    def type(self) -> str:
        switch = {
            _TRILL_DEVICE_BAR: 'Trill Bar',
            _TRILL_DEVICE_CRAFT: 'Trill Craft',
            _TRILL_DEVICE_FLEX: 'Trill Flex',
            _TRILL_DEVICE_HEX: 'Trill Hex',
            _TRILL_DEVICE_RING: 'Trill Ring',
            _TRILL_DEVICE_SQUARE: 'Trill Square',
            _TRILL_DEVICE_UNKNOWN: 'Unknown'
        }
        return switch.get(self._type, 'None')

    def mode(self) -> str:
        switch = {
            TrillMode.AUTO: 'auto',
            TrillMode.CENTROID: 'centroid',
            TrillMode.RAW: 'raw',
            TrillMode.BASELINE: 'baseline',
            TrillMode.DIFF: 'diff',
        }
        return switch.get(self._mode, 'Unknown')
    
    def firmware_version(self) -> int:
        return self._version
    
    def command(self, cmd, buffer_size=32) -> bytearray:
        buffer = bytearray(buffer_size)
        with self.i2c_device as trill:
            trill.write(cmd)
            if buffer_size > 0:
                time.sleep(0.025)
                trill.readinto(buffer)
            return buffer

    def identify(self) -> tuple:
        cmd = bytes([_OFFSET_CMD, _CMD_IDENTIFY])
        result = self.command(cmd, 3)
        # ignore first byte, second byte is device type, third is firmware version
        return (result[1], result[2])

    # return the I2C address of the device
    def address(self, to_hex=True) -> int:
        if to_hex:
            return hex(self._address)
        return self._address
    
    # return the number of capacative channels
    def number_of_channels(self) -> int:
        switch = {
            _TRILL_DEVICE_BAR: 26,
            _TRILL_DEVICE_RING: 30,
        }
        return switch.get(self._type, 30)

    def number_of_vertical_touches(self) -> int:
        return len(self.vertical_touches)
    
    def number_of_horizontal_touches(self) -> int:
        return len(self.horizontal_touches)

    # return the number of "button" channels
    def number_of_buttons(self) -> int:
        if self._type is _TRILL_DEVICE_RING and self._mode is TrillMode.CENTROID:
            return 2
        return 0
    
    def prepare_data_read(self) -> None:
        cmd = bytes([_OFFSET_DATA])
        self.command(cmd, 0)


    
    def read(self) -> None:
        if self._mode is not TrillMode.CENTROID:
            raise Exception("Device must be in centroid mode")

        buffer_size_switch = {
            _TRILL_DEVICE_SQUARE: _CENTROID_LENGTH_2D,
            _TRILL_DEVICE_HEX: _CENTROID_LENGTH_2D,
            _TRILL_DEVICE_RING: _CENTROID_LENGTH_RING,
        }

        buffer_length = buffer_size_switch.get(self._type, _CENTROID_LENGTH_DEFAULT)
        buffer = bytearray(buffer_length)
        
        self.prepare_data_read()

        with self.i2c_device as trill:
            trill.readinto(buffer)

        self.vertical_touches = []

        # merge every two bytes to create a set of WORDs (16-bit values)
        buffer = Trill.process_centroid_bytes(buffer, 2)

        if (self.is_1D()):
            # split the buffer in half: first half is touches, second is sizes
            split_at = buffer_length // 4
            locations, sizes = buffer[:split_at], buffer[split_at:]

            for i in range(len(locations)):
                if locations[i] is 0xffff: # no touches past this point
                    break
                self.vertical_touches.append(Touch(location = locations[i], size = sizes[i]))
        elif (self.is_2D()):
            self.horizontal_touches = []
            # the first half is split between the vertical and horizontal centroids,
            # and then split each of those in half to get the locations and sizes
            half = buffer_length // 4
            quarter = half // 2
            v_locations, v_sizes, h_locations, h_sizes = buffer[:quarter], buffer[quarter:half], buffer[half:half + quarter], buffer[half + quarter:]

            for i in range(len(v_locations)):
                if v_locations[i] is 0xffff: # no more touches
                    break
                self.vertical_touches.append(Touch(location=v_locations[i], size=v_sizes[i]))

            for i in range(len(h_locations)):
                if h_locations[i] is 0xffff: # no more touches
                    break
                self.horizontal_touches.append(Touch(location=h_locations[i], size=h_sizes[i]))



    def button_value(self):
        pass

    def set_mode(self, mode) -> None:
        if mode not in _TRILL_SPEED:
            mode = 0
        cmd = bytes([_OFFSET_CMD, _CMD_MODE, mode])
        self.command(cmd, 0)
        self._mode = mode
    
    def set_scan_settings(self, speed, bits) -> None:
        if speed > 3:
            speed =3
        if bits < 9:
            bits = 9
        if bits > 16:
            bits = 16
        cmd = bytes([_OFFSET_CMD, _CMD_SCAN_SETTINGS, speed, bits])
        self.command(cmd, 0)

    def set_prescaler(self, prescaler) -> None:
        if prescaler > _PRESCALER_MAX:
            prescaler = _PRESCALER_MAX
        cmd = bytes([_OFFSET_CMD, _CMD_PRESCALER, prescaler])
        self.command(cmd, 0)

    def set_noise_threshold(self, threshold) -> None:
        if threshold > 255:
            threshold = 255
        elif threshold < 0:
            threshold = 0
        cmd = bytes([_OFFSET_CMD, _CMD_NOISE_THRESHOLD, threshold])
        self.command(cmd, 0)

    def set_IDAC(self, value) -> None:
        cmd = bytes([_OFFSET_CMD, _CMD_IDAC, value])
        self.command(cmd, 0)

    def set_minimum_touch_size(self, size) -> None:
        cmd = bytes([_OFFSET_CMD, _CMD_MINIMUM_SIZE, size >> 8, size & 0xFF])
        self.command(cmd, 0)

    def set_autoscan_interval(self, interval) -> None:
        cmd = bytes([_OFFSET_CMD, _CMD_AUTO_SCAN_INTVL, interval >> 8, interval & 0xFF])

    def update_baseline(self)-> None:
        cmd = bytes([_OFFSET_CMD, _CMD_BASELINE_UPDATE])
        self.command(cmd, 0)

class Bar(Trill):
    def __init__(self, i2c_bus: I2C, address=0x20, mode=TrillMode.CENTROID):
        try:
            Trill.is_valid_address(address, 0x20, 0x28)
            super().__init__(i2c_bus, type=_TRILL_DEVICE_BAR, address=address, mode=mode)
        except ValueError:
            raise RuntimeError("Address must be from 0x20 to 0x28 for Trill Bar")
    
class Square(Trill):
    def __init__(self, i2c_bus: I2C, address=0x28, mode=TrillMode.CENTROID):
        try:
            Trill.is_valid_address(address, 0x28, 0x30)
            super().__init__(i2c_bus, type=_TRILL_DEVICE_SQUARE, address=address, mode=mode)
        except:
            raise RuntimeError("Address must be from 0x28 to 0x30 for Trill Square")
    
class Craft(Trill):
    def __init__(self,i2c_bus: I2C, address=0x30, mode=TrillMode.DIFF):
        try:
            Trill.is_valid_address(address, 0x30, 0x38)
            super().__init__(i2c_bus, type=_TRILL_DEVICE_CRAFT, address=address, mode=mode)
        except:
            raise RuntimeError("Address must be from 0x30 to 0x38 for Trill Craft")
    
class Ring(Trill):
    def __init__(self, i2c_bus: I2C, address=0x38, mode=TrillMode.CENTROID):
        try:
            Trill.is_valid_address(address, 0x38, 0x40)
            super().__init__(i2c_bus, type=_TRILL_DEVICE_RING, address=address, mode=mode)
        except:
            raise RuntimeError("Address must be from 0x38 to 0x41 for Trill Ring")
    
class Hex(Trill):
    def __init__(self, i2c_bus: I2C, address=0x40, mode=TrillMode.CENTROID):
        try:
            Trill.is_valid_address(address, 0x40, 0x48)
            super().__init__(i2c_bus, type=_TRILL_DEVICE_HEX, address=address, mode=mode)
        except:
            raise RuntimeError("Address must be from 0x40 to 0x48 for Trill Hex")
    
class Flex(Trill):
    def __init__(self, i2c_bus: I2C, address=0x48, mode=TrillMode.DIFF):
        try:
            Trill.is_valid_address(address, 0x48, 0x50)
            super().__init__(i2c_bus, type=_TRILL_DEVICE_FLEX, address=address, mode=mode)
        except:
            raise RuntimeError("Address must be from 0x48 to 0x50 for Trill Flex")


