# coding:utf-8
import os
import sys

# 导入编译后的资源文件，注册 :/qss/... 路径
import resources

from PyQt5.QtCore import Qt, QTranslator
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator

from app.common.config import cfg
from app.view.main_window import MainWindow


# enable dpi scale
if cfg.get(cfg.dpiScale) == "Auto":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
else:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# create application
app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

# 加载思源黑体（解决 OpenType 警告）
font_id = QFontDatabase.addApplicationFont(':/fonts/SourceHanSansSC-VF.ttf')
if font_id != -1:
    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
    app.setFont(QFont(font_family))

# Windows-specific: Set AppUserModelID to ensure taskbar icon displays correctly
if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.voxcpm2.gui")

# 设置应用程序图标（使用 Qt 资源系统）
from PyQt5.QtGui import QIcon
app.setWindowIcon(QIcon(':/images/logo.png'))

# internationalization (optional for now)
locale = cfg.get(cfg.language).value if hasattr(cfg, 'language') else None
if locale:
    translator = FluentTranslator(locale)
    app.installTranslator(translator)

# create main window
w = MainWindow()
w.show()

# start system theme listener
w.themeListener.start()

app.exec_()
