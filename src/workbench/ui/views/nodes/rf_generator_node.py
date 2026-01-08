import logging
from workbench.contracts.enums import RadioModes, StereoModes
from .base_node import mirror_ports, BaseNode
from NodeGraphQt.base.node import NodePropWidgetEnum
from serial.tools.list_ports import comports
from workbench.core.blocks.rf_gen_blocks import PanasonicRFGenerator

LOGGER = logging.getLogger(__name__)


@mirror_ports(PanasonicRFGenerator)
class RFGeneratorNode(BaseNode):
    __identifier__ = 'CustomBlocks'
    NODE_NAME = 'Panasonic RF Generator'

    def __init__(self):
        super().__init__()
        # self.backend = PanasonicRFGenerator()
        self._view_model = None
        self.av_ports = []
        self.scan_usb()

    def bind_view_model(self, view_model):
        self._view_model = view_model
        supp_models = list(self._view_model.model.model_specs.keys())
        # Create UI properties from the model's properties
        # self.create_property(
        #     "cutoff_freq",
        #     self._view_model.model.cutoff_freq,
        #     widget_type=...
        # )
        
        #TODO que aparezcan los puertos usb habilitados
        self.create_property(
            'usb_ports',
            items = self.av_ports,
            value = self.av_ports[0],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select generator usb port"
        )

        self.create_property(
            'generator_model',
            items = supp_models,
            value = supp_models[0],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select generator model"
        )

        self.create_property(
            'mode',
            items = [item.value for item in RadioModes],
            value = [item.value for item in RadioModes][0],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select generator mode",
        )
        #TODO Ver si se puede cambiar el step del spinbox
        self.create_property(
            'frequency_mhz',
            value = 98.1,
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            widget_tooltip="Select generator frequency",
            range=self._view_model.model.model_specs[self._view_model.model.gen_model]['freq_range']
        )

        self.create_property(
            'am_depth',
            value= 30,
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            widget_tooltip="Select generator AM depth",
            range=self._view_model.model.model_specs[self._view_model.model.gen_model]['am_range']
        )

        self.create_property(
            'fm_deviation',
            value=30,
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            widget_tooltip="Select generator FM deviation",
            range=self._view_model.model.model_specs[self._view_model.model.gen_model]['fm_range']
        )
        self.create_property(
            'stereo_mode',
            items = [item.value for item in StereoModes],
            value = [item.value for item in StereoModes][0],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select stereo mode",
        )
        # TODO agregar el resto de las propiedades

        # TODO: Agregar boton para escanear puertos usb
        # NOTE No pude agregar boton en propiedades, pero si en el nodo
        # self.add_button('scan_ports', text='Scan')
        # self.get_widget('scan_ports').value_changed.connect(self.scan_usb)

    def set_property(self, name, value):
        # print(f"set_property: {name}, {value}")
        super().set_property(name, value)
        # Push property changes from the UI to the model
        # setattr(self._view_model.model, name, value)
        if name == "generator_model":
            self._view_model.model.gen_model = value
        elif name == "mode":
            if value == 'AM':
                self._view_model.model.mode = PanasonicRFGenerator.RFModes.AM
            elif value == 'FM':
                self._view_model.model.mode = PanasonicRFGenerator.RFModes.FM
        elif name == "frequency_mhz":
            self._view_model.model.frequency_mhz = float(value)
        elif name == "stereo_mode":
            self._view_model.model.stereo_mode = value

    def scan_usb(self):
        self.av_ports = []
        for port, desc, hwid in sorted(comports()):
            print("{}: {} [{}]".format(port, desc, hwid))
            if 'USB' in desc:
                self.av_ports.append(f'{port}: {desc}')
        if self.av_ports == []:
            self.av_ports.append("No USB ports found")



@mirror_ports(PanasonicRFGenerator)
# NOTE: Tried with CUSTOM_PARAMETERS but couldn't make QDOUBLESPINBOX to work 
# (loses actual value somewhere and tries to do setValue(NoneType))
class RFGeneratorNode2(BaseNode):
    __identifier__ = 'CustomBlocks'
    NODE_NAME = 'Panasonic RF Generator'
    supp_models = list(PanasonicRFGenerator.model_specs.keys())
    

    # def _get_usb_devices():
    #     av_ports = []
    #     for port, desc, hwid in sorted(comports()):
    #         print("{}: {} [{}]".format(port, desc, hwid))
    #         if 'USB' in desc:
    #             av_ports.append(f'{port}: {desc}')
    #     if av_ports == []:
    #         av_ports.append("No USB ports found")
    #     LOGGER.debug(f"input_devices: {av_ports}")
    #     print(av_ports)
    #     return av_ports

    CUSTOM_PROPERTIES = {
        # "usb port": {
        #     # "items_source": "_get_usb_devices",
        #     "default_value": "NOT",
        #     "default_items": "_get_usb_devices",
        #     "widget_type": NodePropWidgetEnum.QCOMBO_BOX.value,
        #     "widget_tooltip": "Select generator usb port",
        # },
        # "generator model":{
        #     "default_value": supp_models[0],
        #     "default_items": supp_models,
        #     "widget_type": NodePropWidgetEnum.QCOMBO_BOX.value,
        #     "widget_tooltip": "Select generator usb port",
        # },
        # "radio mode":{
        #     "default_value": [item.value for item in RadioModes][0],
        #     "default_items": [item.value for item in RadioModes],
        #     "widget_type": NodePropWidgetEnum.QCOMBO_BOX.value,
        #     "widget_tooltip": "Select generator radio mode",
        # },
        # #TODO Ver si se puede cambiar el step del spinbox
        "frequency_mhz": {
            "range": (0, 50.0),
            "default_value": 1.0,
            "widget_type": NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            "widget_tooltip": "Set the calibration factor",
        }
    
        # "AM depth": {},
        # self.create_property(
        #     'am_depth',
        #     value= 30,
        #     widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
        #     widget_tooltip="Select generator AM depth",
        #     range=self._view_model.model.model_specs[self._view_model.model.gen_model]['am_range']
        # )
        # "FM deviation": {}
        # self.create_property(
        #     'fm_deviation',
        #     value=30,
        #     widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
        #     widget_tooltip="Select generator FM deviation",
        #     range=self._view_model.model.model_specs[self._view_model.model.gen_model]['fm_range']
        # )
    }
#TODO: scan devices when block is places
#TODO: put other properties on CUSTOM_PROPERTIES
    def _get_usb_devices(self):
        if self._view_model is None:
            LOGGER.warning("No viewmodel binded. Returning default value")
            return []
        
        av_ports = []
        for port, desc, hwid in sorted(comports()):
            print("{}: {} [{}]".format(port, desc, hwid))
            if 'USB' in desc:
                av_ports.append(f'{port}: {desc}')
        if av_ports == []:
            av_ports.append("No USB ports found")
        LOGGER.debug(f"input_devices: {av_ports}")
        print(av_ports)
        return av_ports

    def set_property(self, name, value):
        # print(f"set_property: {name}, {value}")
        super().set_property(name, value)
        # Push property changes from the UI to the model
        # setattr(self._view_model.model, name, value)
        if name == "generator model":
            self._view_model.model.gen_model = value
        elif name == "radio mode":
            if value == 'AM':
                self._view_model.model.mode = PanasonicRFGenerator.RFModes.AM
            elif value == 'FM':
                self._view_model.model.mode = PanasonicRFGenerator.RFModes.FM
        elif name == "frequency mhz":
            self._view_model.model.frequency_mhz = float(value)

    
    def on_view_model_property_changed(self, name, value):
        # print(f'name is {name}, {value}')
        super().on_view_model_property_changed(name, value)
        if name == "gen_model":
            # print(self.get_view_model())
            pass
        elif name == "usb port":
            pass
