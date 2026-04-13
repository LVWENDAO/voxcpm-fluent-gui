# coding:utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

from qfluentwidgets import ScrollArea
from app.common.style_sheet import StyleSheet


class SynthesisInterface(ScrollArea):
    """ Synthesis interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.label = QLabel("语音合成占位符 - 图标系统已就绪", self)
        self.label.setAlignment(Qt.AlignCenter)

        self.__initWidget()

    def __initWidget(self):
        self.view.setObjectName('view')
        self.setObjectName('synthesisInterface')
        StyleSheet.SYNTHESIS_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 0, 0, 0)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.addWidget(self.label)
        self.view.setObjectName('view')
