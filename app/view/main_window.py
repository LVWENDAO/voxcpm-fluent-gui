# coding:utf-8
from PyQt5.QtCore import QUrl, Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QIcon, QDesktopServices, QColor, QPainter, QImage, QPixmap
from PyQt5.QtWidgets import QApplication

from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen, SystemThemeListener, isDarkTheme)
from qfluentwidgets import FluentIcon as FIF

from app.common.config import cfg
from app.common.icon import Icon
from app.common.signal_bus import signalBus
from app.common.style_sheet import StyleSheet
from app.view.synthesis_interface import SynthesisInterface  
from app.view.history_interface import HistoryInterface
from app.view.setting_interface import SettingInterface

# 导入资源文件（确保资源被加载）
import app.resource_rc


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.initWindow()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # create sub interface
        self.synthesisInterface = SynthesisInterface(self)
        self.historyInterface = HistoryInterface(self)
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
        self.addSubInterface(self.synthesisInterface, FIF.MUSIC, "语音合成")
        self.addSubInterface(self.historyInterface, FIF.HISTORY, "生成历史")
        
        self.addSubInterface(
            self.settingInterface, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(960, 780)
        self.setMinimumWidth(760)
        
        # 设置窗口图标（支持多分辨率以优化任务栏显示）
        icon = QIcon()
        icon.addFile(':/images/logo_16.png', QSize(16, 16))
        icon.addFile(':/images/logo_32.png', QSize(32, 32))
        icon.addFile(':/images/logo_48.png', QSize(48, 48))
        icon.addFile(':/images/logo_256.png', QSize(256, 256))
        self.setWindowIcon(icon)
        
        self.setWindowTitle('VoxCPM2 GUI')

        self.setMicaEffectEnabled(True)

        # create splash screen using window icon
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(256, 256))
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