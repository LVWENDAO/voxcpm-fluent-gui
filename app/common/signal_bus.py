# coding:utf-8
from PyQt5.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """ Signal bus """
    micaEnableChanged = pyqtSignal(bool)
    supportSignal = pyqtSignal()
    voiceRegistered = pyqtSignal()  # 音色注册完成信号


signalBus = SignalBus()
