import logging
from workbench.contracts.enums import RadioModes, StereoModes
from .base_node import mirror_ports, BaseNode
from NodeGraphQt.base.node import NodePropWidgetEnum
from serial.tools.list_ports import comports
from workbench.core.blocks.rf_gen_blocks import PanasonicRFGenerator

LOGGER = logging.getLogger(__name__)

class RFGeneratorNode(BaseNode):
    __identifier__ = 'Mirgor'
    NODE_NAME = 'Panasonic RF Generator'

    def __init__(self):
        super().__init__()
        self._view_model = None
        self.av_ports = []
        self.add_input('config')
        self.scan_usb()

    def bind_view_model(self, view_model):
        self._view_model = view_model
        supp_models = list(self._view_model.model.model_specs.keys())
        # Create UI properties from the model's properties
        self.create_property(
            'usb_ports',
            items = self.av_ports,
            value = self.av_ports[0],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select generator usb port"
        )

        self.create_property(
            'find_gpib_address',
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            widget_tooltip="Scans addresses 0-30 on start. This is a relatively slow process"
        )

        self.create_property(
            'gpib_address',
            value = 0,
            range = (0, 30),
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            widget_tooltip="Select generator GPIB address"
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
            range=self._view_model.model.model_specs[self._view_model.model.generator_model]['freq_range']
        )

        # self.create_property(
        #     'am_depth',
        #     value= 30,
        #     widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
        #     widget_tooltip="Select generator AM depth",
        #     range=self._view_model.model.model_specs[self._view_model.model.generator_model]['am_range']
        # )

        # self.create_property(
        #     'fm_deviation',
        #     value=30,
        #     widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
        #     widget_tooltip="Select generator FM deviation",
        #     range=self._view_model.model.model_specs[self._view_model.model.generator_model]['fm_range']
        # )

        self.create_property(
            'modulation',
            value = 30,
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            widget_tooltip="Select generator modulation",
            range=self._view_model.model.model_specs[self._view_model.model.generator_model]['am_range']
        )

        self.create_property(
            'stereo_mode',
            items = [item.value for item in StereoModes],
            value = [item.value for item in StereoModes][0],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select stereo mode",
        )

        self.create_property(
            'amplitude_format',
            items = self._view_model.model.model_specs[self._view_model.model.generator_model]['level_units'],
            value = self._view_model.model.model_specs[self._view_model.model.generator_model]['level_units'][0],
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip="Select ouput format",
        )
        
        self.create_property(
            'amplitude',
            value=40,
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            widget_tooltip="Select output level",
            range=self._view_model.model.model_specs[self._view_model.model.generator_model]['level_range'][0]
        )
        # TODO agregar el resto de las propiedades

    def set_property(self, name, value):
        super().set_property(name, value)
        if name == "generator_model":
            specs = self._view_model.model.model_specs[self.get_property('generator_model')]
            self.set_property_attrs('frequency_mhz', range= specs['freq_range'])

            self.set_property_attrs('amplitude_format', items= specs['level_units'])
            self.set_property('amplitude_format', specs['level_units'][0])

        elif name == "mode":
            if value == 'AM':
                self._view_model.model.mode = RadioModes.AM
                self.set_property_attrs('modulation', range= self._view_model.model.specs['am_range'])
            elif value == 'FM':
                self._view_model.model.mode = RadioModes.FM
                self.set_property_attrs('modulation', range= self._view_model.model.specs['fm_range'])
        elif name == "modulation":
            if self.get_property('mode') == 'AM':
                self._view_model.model.am_depth = value
            elif self.get_property('mode') == 'FM':
                self._view_model.model.fm_deviation = value
        elif name == 'amplitude':
            self._view_model.model.output_level = (value, self.get_property('amplitude_format'))
        elif name == "usb_ports":
            self._view_model.model.com_port = value.split(':')[0]

    def scan_usb(self):
        self.av_ports = ["Select port"]
        for port, desc, hwid in sorted(comports()):
            print("{}: {} [{}]".format(port, desc, hwid))
            if 'USB' in desc:
                self.av_ports.append(f'{port}: {desc}')
        # if self.av_ports == []:
        #     self.av_ports.append("No USB ports found")
        # else: self.set_property("com_port", self.av_ports[0])

    def set_property_attrs(self, name, *, items=None, range=None,
                           widget_type=None, tooltip=None, tab=None):
        """
        Cambia metadatos (attrs) de una property custom ya creada:
        - items (para QCOMBO_BOX)
        - range (para SLIDER)
        - widget_type, tooltip, tab

        NOTA: si el nodo ya está en un graph, esto se guarda como
        'common properties' del tipo de nodo (afecta a TODOS los nodos de ese type).
        """
        LOGGER.info(f'Changing attr {name}: items {items}, range {range}')
        if not self.model.is_custom_property(name):
            raise KeyError(f'La property "{name}" no existe o no es custom.')

        # Defaults parecidos a add_property()
        if widget_type is None:
            widget_type = self.model.get_widget_type(name) or NodePropWidgetEnum.HIDDEN.value
        if tab is None:
            tab = "Properties"

        # Caso 2: el nodo ya está en un graph -> common properties
        attrs = {
            self.model.type_: {
                name: {
                    "widget_type": widget_type,
                    "tab": tab
                }
            }
        }
        if items is not None:
            attrs[self.model.type_][name]["items"] = items
        if range is not None:
            attrs[self.model.type_][name]["range"] = range
        if tooltip is not None:
            attrs[self.model.type_][name]["tooltip"] = tooltip

        # Esto actualiza el dict existente con .update()
        self.model._graph_model.set_node_common_properties(attrs)
        self.graph.property_cfg_changed.emit(self, name)

        # Sugerencia de refresco visual (depende de tu UI)
        self.view.draw_node()




# @mirror_ports(PanasonicRFGenerator)
# NOTE: Tried with CUSTOM_PARAMETERS but couldn't make QDOUBLESPINBOX to work 
# (loses actual value somewhere and tries to do setValue(NoneType))
class RFGeneratorNode2(BaseNode):
    __identifier__ = 'Mirgor'
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
            self._view_model.model.generator_model = value
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
        if name == "generator_model":
            # print(self.get_view_model())
            pass
        elif name == "usb port":
            pass
