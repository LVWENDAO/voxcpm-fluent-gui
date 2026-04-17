# coding:utf-8
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import (ScrollArea, CardWidget, StrongBodyLabel, BodyLabel, 
                            CaptionLabel, HyperlinkButton, FluentIcon as FIF,
                            TransparentToolButton, setTheme, Theme)

from app.common.style_sheet import StyleSheet


class ContributorCard(CardWidget):
    """贡献者卡片组件"""
    
    def __init__(self, avatar_path, title, description, links, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # 左侧头像
        self.avatarLabel = QLabel()
        self.avatarLabel.setFixedSize(64, 64)
        self.avatarLabel.setScaledContents(False)  # 禁用自动拉伸
        self.avatarLabel.setStyleSheet("border-radius: 32px;")
        self.avatarLabel.setAlignment(Qt.AlignCenter)  # 居中显示
        
        # 重写 paintEvent 实现等比例裁切
        original_paintEvent = self.avatarLabel.paintEvent
        def custom_paintEvent(event):
            original_paintEvent(event)
            if not self.avatarLabel.pixmap().isNull():
                from PyQt5.QtGui import QPainter
                painter = QPainter(self.avatarLabel)
                painter.setRenderHint(QPainter.Antialiasing)
                # 创建圆形裁剪路径
                from PyQt5.QtGui import QPainterPath
                path = QPainterPath()
                path.addEllipse(0, 0, 64, 64)
                painter.setClipPath(path)
                # 等比例缩放并居中绘制
                pixmap = self.avatarLabel.pixmap()
                scaled = pixmap.scaled(64, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                x = (64 - scaled.width()) // 2
                y = (64 - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
        self.avatarLabel.paintEvent = custom_paintEvent
        
        # 加载头像
        pixmap = QPixmap(avatar_path)
        if not pixmap.isNull():
            self.avatarLabel.setPixmap(pixmap)
        else:
            # 使用默认图标
            self.avatarLabel.setStyleSheet("background-color: palette(mid); border-radius: 32px;")
        
        layout.addWidget(self.avatarLabel, 0, Qt.AlignVCenter)
        
        # 右侧信息
        infoLayout = QVBoxLayout()
        infoLayout.setSpacing(6)
        
        # 标题
        self.titleLabel = StrongBodyLabel(title)
        infoLayout.addWidget(self.titleLabel)
        
        # 描述
        self.descLabel = BodyLabel(description)
        self.descLabel.setWordWrap(True)
        infoLayout.addWidget(self.descLabel)
        
        # 链接按钮
        linksLayout = QHBoxLayout()
        linksLayout.setSpacing(12)
        linksLayout.setContentsMargins(0, 4, 0, 0)
        
        for link_text, link_url in links:
            btn = HyperlinkButton(url=link_url, text=link_text)
            linksLayout.addWidget(btn)
        
        linksLayout.addStretch()
        infoLayout.addLayout(linksLayout)
        
        layout.addLayout(infoLayout, 1)


class AboutInterface(ScrollArea):
    """关于界面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget()
        self.vBoxLayout = QVBoxLayout(self.view)

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        self.view.setObjectName('view')
        self.setObjectName('aboutInterface')
        
        # 强制透明背景以适配主题
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.viewport().setStyleSheet("background-color: transparent;")
        self.view.setStyleSheet("background-color: transparent;")
        
        StyleSheet.ABOUT_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

    def __initLayout(self):
        self.vBoxLayout.setContentsMargins(32, 32, 32, 32)
        self.vBoxLayout.setSpacing(20)

        # 标题
        titleLabel = StrongBodyLabel("关于 VoxCPM2 GUI", self)
        self.vBoxLayout.addWidget(titleLabel)

        # 导入资源
        import app.resource_rc
        
        # 1. VOXCPM 官方
        officialCard = ContributorCard(
            avatar_path=":/images/github.png",
            title="VoxCPM 官方",
            description="新一代语音克隆模型，提供强大的语音合成与克隆能力",
            links=[
                ("GitHub", "https://github.com/OpenBMB/VoxCPM"),
                ("文档", "https://voxcpm.readthedocs.io/zh-cn/latest/models/voxcpm2.html")
            ],
            parent=self.view
        )
        self.vBoxLayout.addWidget(officialCard)

        # 2. GUI 组件贡献者
        guiCard = ContributorCard(
            avatar_path=":/images/github.png",
            title="GUI 组件贡献者",
            description="提供 PyQt-Fluent-Widgets 核心 UI 组件与 Fluent Design 实现",
            links=[
                ("Qt Fluent", "https://github.com/Fairy-Oracle-Sanctuary/Qt-Fluent-Widgets"),
                ("PyQt Fluent", "https://github.com/zhiyiYo/PyQt-Fluent-Widgets")
            ],
            parent=self.view
        )
        self.vBoxLayout.addWidget(guiCard)

        # 3. 构建者（你）
        builderCard = ContributorCard(
            avatar_path=":/images/github.png",
            title="XDAOX",
            description="VoxCPM2 GUI 独立构建者，负责项目整合与界面开发",
            links=[
                ("GitHub", "https://github.com/LVWENDAO")
            ],
            parent=self.view
        )
        self.vBoxLayout.addWidget(builderCard)

        self.vBoxLayout.addStretch(1)
