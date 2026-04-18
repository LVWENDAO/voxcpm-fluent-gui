# coding:utf-8
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import (ScrollArea, CardWidget, StrongBodyLabel, BodyLabel, 
                            CaptionLabel, HyperlinkButton, FluentIcon as FIF,
                            TransparentToolButton, setTheme, Theme, TextBrowser,
                            SubtitleLabel)

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
        self.vBoxLayout.setSpacing(24)

        # 标题
        titleLabel = StrongBodyLabel("关于 VoxCPM2 GUI", self.view)
        self.vBoxLayout.addWidget(titleLabel)

        # 导入资源
        import app.resource_rc
        
        # 1. 贡献者卡片 - 一行三列布局
        contributorsRow = QHBoxLayout()
        contributorsRow.setSpacing(16)
        
        # VOXCPM 官方
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
        contributorsRow.addWidget(officialCard, 1)

        # GUI 组件贡献者
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
        contributorsRow.addWidget(guiCard, 1)

        # 构建者（你）
        builderCard = ContributorCard(
            avatar_path=":/images/github.png",
            title="XDAOX",
            description="VoxCPM2 GUI 独立构建者，负责项目整合与界面开发",
            links=[
                ("GitHub", "https://github.com/LVWENDAO")
            ],
            parent=self.view
        )
        contributorsRow.addWidget(builderCard, 1)
        
        self.vBoxLayout.addLayout(contributorsRow)

        # 2. 许可证与使用声明卡片 - 优化布局
        license_card = CardWidget(self.view)
        license_layout = QVBoxLayout(license_card)
        license_layout.setContentsMargins(28, 24, 28, 24)
        license_layout.setSpacing(18)
        
        # 标题区域
        headerLayout = QHBoxLayout()
        license_title = SubtitleLabel("许可证与使用声明", self.view)
        headerLayout.addWidget(license_title)
        headerLayout.addStretch()
        license_layout.addLayout(headerLayout)
        
        # 内容网格布局（两列）
        contentGrid = QHBoxLayout()
        contentGrid.setSpacing(24)
        
        # 左列：许可证信息 + 使用限制
        leftColumn = QVBoxLayout()
        leftColumn.setSpacing(14)
        
        # 许可证
        lic_section = QVBoxLayout()
        lic_section.setSpacing(6)
        lic_label = StrongBodyLabel("开源许可证", self.view)
        lic_section.addWidget(lic_label)
        license_text = BodyLabel(
            "本项目基于 VoxCPM2 构建，遵循 Apache-2.0 开源许可证。\n"
            "VoxCPM2 由 OpenBMB（面壁智能）团队开发并发布。",
            self.view
        )
        license_text.setWordWrap(True)
        lic_section.addWidget(license_text)
        leftColumn.addLayout(lic_section)
        
        # 使用范围限制
        restrict_section = QVBoxLayout()
        restrict_section.setSpacing(6)
        restrict_label = StrongBodyLabel("使用范围限制", self.view)
        restrict_section.addWidget(restrict_label)
        restriction_text = BodyLabel(
            "禁止将本软件用于以下用途：\n"
            "• 生成虚假、欺诈或误导性语音内容\n"
            "• 侵犯他人隐私权、肖像权或声音权\n"
            "• 进行非法活动或传播违法信息\n"
            "• 冒充他人身份进行诈骗或诽谤\n"
            "• 任何违反当地法律法规的行为",
            self.view
        )
        restriction_text.setWordWrap(True)
        restrict_section.addWidget(restriction_text)
        leftColumn.addLayout(restrict_section)
        
        contentGrid.addLayout(leftColumn, 1)
        
        # 右列：免责声明
        rightColumn = QVBoxLayout()
        rightColumn.setSpacing(14)
        
        disclaimer_section = QVBoxLayout()
        disclaimer_section.setSpacing(6)
        disclaimer_label = StrongBodyLabel("免责声明", self.view)
        disclaimer_section.addWidget(disclaimer_label)
        disclaimer_text = BodyLabel(
            "本软件仅供学习、研究和个人娱乐使用。\n\n"
            "使用者应自行承担因使用本软件产生的一切后果，包括但不限于：\n"
            "• 数据泄露或隐私侵权\n"
            "• 知识产权纠纷\n"
            "• 法律责任或经济损失\n\n"
            "作者不对任何直接或间接损害承担责任，包括但不限于：\n"
            "• 数据丢失或损坏\n"
            "• 业务中断或利润损失\n"
            "• 第三方索赔或法律诉讼\n\n"
            "若使用者违反上述使用限制或造成任何损害，与本项目作者及贡献者无关。",
            self.view
        )
        disclaimer_text.setWordWrap(True)
        disclaimer_section.addWidget(disclaimer_text)
        rightColumn.addLayout(disclaimer_section)
        
        contentGrid.addLayout(rightColumn, 1)
        license_layout.addLayout(contentGrid)
        
        self.vBoxLayout.addWidget(license_card)

        self.vBoxLayout.addStretch(1)
