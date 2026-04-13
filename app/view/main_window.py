# coding:utf-8
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import QApplication

from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen, SystemThemeListener, isDarkTheme)
from qfluentwidgets import FluentIcon as FIF

from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.view.home_interface import HomeInterface
from app.view.synthesis_interface import SynthesisInterface
from app.view.logs_interface import LogsInterface
from app.view.setting_interface import SettingInterface


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.initWindow()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # create sub interface
        self.homeInterface = HomeInterface(self)
        self.synthesisInterface = SynthesisInterface(self)
        self.logsInterface = LogsInterface(self)
        self.settingInterface = SettingInterface(self)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        self.connectSignalToSlot()

        # add items to navigation interface
        self.initNavigation()
        self.splashScreen.finish()

        # start theme listener
        self.themeListener.start()

    def connectSignalToSlot(self):
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)

    def initNavigation(self):
        # add navigation items
        self.addSubInterface(self.homeInterface, FIF.HOME, "首页")
        self.addSubInterface(self.synthesisInterface, FIF.MUSIC, "语音合成")
        self.addSubInterface(self.logsInterface, FIF.CHAT, "服务器日志")
        
        self.addSubInterface(
            self.settingInterface, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(960, 780)
        self.setMinimumWidth(760)
        self.setWindowTitle('VoxCPM2 GUI')

        self.setMicaEffectEnabled(True)

        # create splash screen
        self.splashScreen = SplashScreen(QIcon(":/icons/images/logo.png"), self)
        self.splashScreen.setIconSize(self.splashScreen.iconSize())
        self.splashScreen.raise_()

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

        # 对齐参考案例：通过设置配置项触发主题初始化
        cfg.set(cfg.themeMode, cfg.get(cfg.themeMode))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())

    def closeEvent(self, e):
        self.themeListener.terminate()
        self.themeListener.deleteLater()
        super().closeEvent(e)

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()

        # retry mica effect
        if self.isMicaEffectEnabled():
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))
