# coding:utf-8
from PyQt5.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """ Signal bus """
    micaEnableChanged = pyqtSignal(bool)
    supportSignal = pyqtSignal()
    voiceRegistered = pyqtSignal()  # 音色注册完成信号
    voiceDeleted = pyqtSignal()     # 音色删除完成信号
    historyGenerated = pyqtSignal() # 新历史记录生成信号


signalBus = SignalBus()
