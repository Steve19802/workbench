# from __future__ import annotations
import logging
from enum import Enum
from threading import Lock
import json
from workbench.contracts.enums import RadioModes, StereoModes
from ..base_blocks import Block
from ..helpers.gpib_connection import GPIBConnection
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel("DEBUG")

@register_block
#NOTE: An output is added so the block is registered as producer and on_start() works
@define_ports(["config"], [""])
class PanasonicRFGenerator(Block):
    """
    Generic class to control Panasonic RF generators via GPIB.
    Supported models:
    - VP-8191A
    - VP-8174A
    - VP-8120A
    """
    model_specs = {
        # "vp-8191a": {
        #     "freq_format": "{:.4f}",
        #     "freq_unit": "",
        #     "freq_range": (0.0800, 136.0000),
        #     "am_range": (0, 80),
        #     "fm_range": (0, 300),
        #     "level_units_cmd": ["DB", "DM"],
        #     "level_units": ["dB EMF", "dBm"],
        #     "level_range": [(-17.9, 132.0), (-130.9, 19.0)],
        #     "pilot_range": (0, 15)
        # },
        "vp-8174a": {
            "freq_format": "{:.1f}",
            "freq_unit": "",
            "freq_range": (0.1, 110.0),
            "modulation_cmd": {
                "external": "TO0", 
                "1khz": "TO1", 
                "400hz": "TO4"
                },
            "stereo_settings":{
                "MONO": 1,
                "L=R": 2,
                "L": 3,
                "R": 4,
                "L=-R": 5
            },
            "amfm_turn_onoff": "", #Requires explicit command to turn modes on or off
            "am_range": (0, 60),
            "fm_range": (0, 99.5),
            "level_units_cmd": [""],
            "level_units": ["dB EMF"],
            "level_range":[(-19, 99)],
            "pilot_range": (0, 15)
        },
        "vp-8120a": {
            # External stereo modulation not supported
            "freq_format": "{:.5f}",
            "freq_unit": "MZ",
            "freq_range": (0.01000, 280.00000),
            "modulation_cmd": {
                "external": "AMXD", 
                "1khz": "AMT1", 
                "400hz": "AMT4"
                },
            "stereo_settings":{
                "MONO": '01',
                "L=R": '02',
                "L": '03',
                "R": '04',
                "L=-R": '05'
            },
            "amfm_turn_onoff": ['ON', 'OF'],
            "am_range": (0, 125),
            "fm_range": (0, 300),
            "level_units_cmd": ["DM", "DB", "MV", "UV"],
            "level_units": ["dBm", "dBuV", "mV", "uV"],
            "level_range": [(-133.0, 19.0), (-26.0, 126.0), (0.00005, 2000),(0.05, 2000000)],
            "pilot_range": (0, 19.9),
            "EMF": "EM"
        }
    }
        
    def __init__(self, name:str):
        super().__init__(name)
        self._com_port = None
        self._gpib_address = None
        self.connection = GPIBConnection()
        
        self._generator_model = "vp-8174a"
        if self._generator_model not in self.model_specs:
            LOGGER.error(f"Modelo no soportado: {self._generator_model}")
        self.specs = self.model_specs[self._generator_model]

        self._mode: RadioModes = None
        self._frequency_mhz = None
        self._am_depth = None
        self._fm_deviation = None
        self._output_level = None
        self._stereo_mode: StereoModes = None
        self._output_unit = None
        self._pilot_level = None
        self.find_gpib_address : bool = True

        self._lock = Lock()

        # self.add_output_port("RF_out")

    @property
    def generator_model(self) -> str:
        return self._generator_model
    
    @generator_model.setter
    def generator_model(self, model:str):
        model_low = model.lower()
        if model_low not in self.model_specs:
            LOGGER.error(f"Modelo no soportado: {model_low}")
        else:
            self._generator_model = model_low
            self.specs = self.model_specs[model_low]
            self.on_property_changed("generator_model", model_low)

    @property
    def com_port(self) -> str:
        return self._com_port
    
    @com_port.setter
    def com_port(self, newport: str):
        with self._lock:
            self.connection.port = newport
            self._com_port = newport
            self.on_property_changed("com_port", newport)


    @property
    def gpib_address(self) -> str:
        return self._com_port
    
    @gpib_address.setter
    def gpib_address(self, newaddress):
        with self._lock:
            self.connection.gpib_address = newaddress
            self._gpib_address = newaddress

    @property
    def mode(self) -> RadioModes:
        return self._mode
    
    @mode.setter
    def mode(self, nmode: RadioModes) -> None:
        with self._lock:
            if nmode != self.mode:
                LOGGER.info(f"Setting RF mode to {nmode}")
                if nmode is RadioModes.AM:
                    if self.specs["amfm_turn_onoff"]!="":
                        self.connection.gpib_send_command(f"FM{self.specs["amfm_turn_onoff"][1]}")
                        self.connection.gpib_send_command(f"AM{self.specs["amfm_turn_onoff"][0]}")
                    else:
                        self.connection.gpib_send_command("AM")
                elif nmode is RadioModes.FM:
                    if self.specs["amfm_turn_onoff"]!="":
                        self.connection.gpib_send_command(f"AM{self.specs["amfm_turn_onoff"][1]}")
                        self.connection.gpib_send_command(f"FM{self.specs["amfm_turn_onoff"][0]}")
                    else:
                        self.connection.gpib_send_command("FM")

                # LOGGER.debug(f"ARE YOU HERE????? {nmode}")
                self._mode = nmode
            self.on_property_changed("mode", nmode)

    @property
    def frequency_mhz(self) -> float:
        return self._frequency_mhz

    @frequency_mhz.setter
    def frequency_mhz(self, mhz) -> None:
        with self._lock:
            if not self.range_check(mhz, self.specs["freq_range"]):
                LOGGER.info(f"{self.name}: Frequency out of range, choosing closest value {mhz}")
            formatted = self.specs["freq_format"].format(mhz)
            unit = self.specs["freq_unit"]
            self.connection.gpib_send_command(f"FR{formatted}{unit}")
            self._frequency_mhz = mhz
            self.on_property_changed("frequency_mhz", mhz)

    @property
    def fm_deviation(self) -> float:
        return self._fm_deviation

    @fm_deviation.setter
    def fm_deviation(self, khz) -> None:
        self.mode = RadioModes.FM
        if not self.range_check(khz, self.specs["fm_range"]):
            LOGGER.info(f"{self.name}: FM deviation out of range, choosing closest value {khz}")
        self.connection.gpib_send_command(f"FM{khz:.2f}")
        self._fm_deviation = khz
        self.on_property_changed("fm_deviation", khz)

    @property
    def am_depth(self) -> float:
        return self._am_depth

    @am_depth.setter
    def am_depth(self, percent) -> None:
        self.mode = RadioModes.AM
        if not self.range_check(percent, self.specs["am_range"]):
            LOGGER.info(f"{self.name}: AM depth out of range, choosing closest value {percent}")
        self.connection.gpib_send_command(f"AM{percent:.1f}")
        self._am_depth = percent
        self.on_property_changed("am_depth", percent)

    @property
    def output_level(self) -> float:
        return self._output_level

    @output_level.setter
    def output_level(self, value_unit_tuple : tuple) -> None:
        value, unit = value_unit_tuple
        if unit.lower() not in [u.lower() for u in self.specs["level_units"]]:
            unit = self.specs["level_units"][0]
            LOGGER.error(f"{self.name}: Unit not supported, defaulting to {unit}")
            idx = 0
        else:
            idx=[u.lower() for u in self.specs["level_units"]].index(unit.lower())
        self.range_check(value, self.specs["level_range"][idx])
        self.connection.gpib_send_command(f"LE{value:.1f}{self.specs["level_units_cmd"][idx]}")
        self._output_level = value
        self._output_unit = unit
        self.on_property_changed("ouput_level", (value, unit))

    @property
    def stereo_mode(self) -> StereoModes:
        return self._stereo_mode

    @stereo_mode.setter
    def stereo_mode(self, smode: StereoModes) -> None:
        if smode.upper() not in [u for u in self.specs["stereo_settings"]]:
            LOGGER.error(f"{self.name}: Stereo mode {smode} not supported, defaulting to MONO")
            smode = "MONO"
        self.connection.gpib_send_command(f"MS{self.specs["stereo_settings"][smode.upper()]}")
        self._stereo_mode = StereoModes(smode)
        self.on_property_changed("stereo_mode", smode.upper())

    @property
    def pilot_level(self) -> float:
        return self._pilot_level

    @pilot_level.setter
    def pilot_level(self, percent) -> None:
        min_pl, max_pl = self.specs["pilot_range"]
        if not (min_pl <= percent <= max_pl):
            raise ValueError(f"Nivel piloto fuera de rango ({min_pl}–{max_pl}%)")
        self.connection.gpib_send_command(f"PL{percent}")
        self._pilot_level = percent
        self.on_property_changed("pilot_level", percent)

    def set_EMF(self, state: bool):
        if state:
            self.connection.gpib_send_command("EMON")
        else:
            self.connection.gpib_send_command("EMOF")

    def connect_to_generator(self):
        """
        Connects to RF generator in the _gpib_address_ through USB port _com_port_.

        If connection was succsessfull, _isConnected_ is set to _True_
        """
        # self.connection.port = self.com_port
        with self._lock:
            LOGGER.info(f"{self.name}: Connecting to generator")
            if self.connection.gpib_connect(self.find_gpib_address):
                return True
            else:
                self.close()
                return False

    def store_preset(self, address):
        if not (0 <= address <= 99):
            raise ValueError("Dirección de preset fuera de rango (0–99)")
        self.connection.gpib_send_command(f"ST{address:02d}")

    def recall_preset(self, address):
        if not (0 <= address <= 99):
            raise ValueError("Dirección de preset fuera de rango (0–99)")
        self.connection.gpib_send_command(f"RC{address:02d}")

    def close(self):
        self.connection.close()
    
    def range_check(self, value, min_max_tuple : tuple) -> bool:
        """
        Mantains 'value' between the given range in the fomrat (minimum, maximum). Returns 'False' if the value was out of range
        """
        if value < min_max_tuple[0]:
            value = min_max_tuple[0]
            return False
        elif value > min_max_tuple[1]: 
            value = min_max_tuple[1]
            return False
        else: return True
    
    def on_start(self):
        return self.connect_to_generator()
    
    def on_stop(self):
        self.close()
        return True
    
    def on_property_changed(self, name, value):
        return super().on_property_changed(name, value)

    def on_input_received(self, port_name, data):
        super().on_input_received(port_name, data)
        try:
            cfg = json.loads(data)
        except json.JSONDecodeError:
            pass
        
        #TODO: add config parser
        mode = cfg.get("mode")
        freq = cfg.get("frequency")
        modulation = cfg.get("modulation")
        out_level = cfg.get("amplitude")
        out_unit = cfg.get("amplitude format")

        # if mode != None:
        #     self.mode = mode
        if freq != None:
            self.frequency_mhz = freq
        if modulation != None:
            self.modulation = modulation
        if (out_level != None) and (out_unit != None):
            self.output_level = (out_level, out_unit)
        




# generator=PanasonicRFGenerator('COM5', 15)

# """
# Frecuencia
# FM
# MONO
# PILOT OFF
# MOD = 75 kHZ
# AMP = 40mV
# """
# generator.frequency_mhz = 98.2
#     # generator._fm_deviation = None
# generator.output_level = (40, 'dBm')
# generator.fm_deviation = 75
# generator.stereo_mode = "mono"
# # generator.output_level = (40, 'MV')
# generator.close()