# src/workbench/ui/views/nodes/filter_node_view.py
import logging
from .base_node import mirror_ports, BaseNode
from NodeGraphQt.base.node import NodePropWidgetEnum

from workbench.core.blocks.itu_filter import ITUFilterBlock

LOGGER = logging.getLogger(__name__)

@mirror_ports(ITUFilterBlock)
class ITUFilterNodeView(BaseNode):

    __identifier__ = 'Filter'
    
    NODE_NAME = 'ITU R 468'


class ITUFilterNodeView2(BaseNode):
    __identifier__ = 'Filter'
    NODE_NAME = 'ITU R 468'

    def __init__(self):
        super().__init__()
        self._view_model = None
        self.add_input('in')
        self.add_output('original')
        self.add_output('filtered')

    def bind_view_model(self, view_model):
        self._view_model = view_model

        # self.create_property(
        #     'coefficients',
        #     value = 513,
        #     widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
        #     widget_tooltip="Number of coefficients",
        #     range=(513, 1025)
        #     )
    
    # def set_property(self, name, value):
    #     super().set_property(name, value)
    #     # Push property changes from the UI to the model
    #     setattr(self._view_model.model, name, value)