# coding:utf-8
from PyQt5.QtCore import Qt, QTimer, QUrl, QFileSystemWatcher
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from pathlib import Path
import json, shutil

from qfluentwidgets import (
    ScrollArea, CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel, 
    PushButton, PrimaryPushButton, FluentIcon as FIF, InfoBar, TransparentToolButton,
    LineEdit, MessageBoxBase, SubtitleLabel, IconWidget
)

class RenameDialog(MessageBoxBase):
    """重命名对话框"""
    def __init__(self, current_name, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('重命名音色', self)
        self.nameLineEdit = LineEdit(self)
        self.nameLineEdit.setText(current_name)
        self.nameLineEdit.setPlaceholderText("请输入新的音色名称")
        
        # 布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.nameLineEdit)
        self.viewLayout.setSpacing(10)
        
        # 设置按钮文本
        self.yesButton.setText('确定')
        self.cancelButton.setText('取消')
        
        # 自动聚焦
        self.nameLineEdit.setFocus()

    @property
    def name(self):
        return self.nameLineEdit.text().strip()


class VoiceCard(CardWidget):
    def __init__(self, voice_data, parent_interface=None):
        super().__init__(parent_interface)
        self.voice_data = voice_data
        self.voice_id = voice_data.get("id", "")
        self.parent_interface = parent_interface
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # 标题行
        header = QHBoxLayout()
        self.iconWidget = IconWidget(FIF.ALBUM, self)
        self.iconWidget.setFixedSize(24, 24)
        header.addWidget(self.iconWidget)
        header.addWidget(StrongBodyLabel(self.voice_data.get("name", "未命名音色")))
        header.addStretch()
        header.addWidget(CaptionLabel(f"ID: {self.voice_id}"))
        layout.addLayout(header)
        
        # 参数展示
        params = QHBoxLayout()
        config = self.voice_data.get("config", {})
        seed = config.get("seed", "N/A")
        steps = config.get("inference_timesteps", "N/A")
        cfg = config.get("cfg_value", "N/A")
        
        params.addWidget(CaptionLabel(f"Seed: {seed}"))
        params.addWidget(CaptionLabel(f"Steps: {steps}"))
        params.addWidget(CaptionLabel(f"CFG: {cfg}"))
        params.addStretch()
        layout.addLayout(params)
        
        # 按钮行
        btns = QHBoxLayout()
        playBtn = PushButton(FIF.PLAY, "试听")
        playBtn.clicked.connect(lambda: self.parent_interface.onPlay(self.voice_id))
        btns.addWidget(playBtn)
        
        renameBtn = PushButton(FIF.EDIT, "重命名")
        renameBtn.clicked.connect(lambda: self.parent_interface.onRename(self.voice_id))
        btns.addWidget(renameBtn)
        
        delBtn = PushButton(FIF.DELETE, "删除")
        delBtn.clicked.connect(lambda: self.parent_interface.onDelete(self.voice_id))
        btns.addWidget(delBtn)
        btns.addStretch()
        layout.addLayout(btns)


class VoiceLibraryInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("voiceLibraryInterface")
        
        # 初始化播放器
        self.player = QMediaPlayer()
        
        # 初始化文件系统监听器
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.__onDirectoryChanged)
        
        self.view = QWidget()
        self.mainLayout = QVBoxLayout(self.view)
        self.cardsLayout = QVBoxLayout()
        self.cardsLayout.setAlignment(Qt.AlignTop)
        
        # 路径配置
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.voice_cache_dir = base_dir / "voice_cache"
        self.voice_cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.voice_cache_dir / "voices_db.json"
        
        # 开始监听
        self.watcher.addPath(str(self.voice_cache_dir))
        
        # 标题栏
        titleRow = QHBoxLayout()
        titleRow.addWidget(StrongBodyLabel("音色库管理"))
        titleRow.addStretch()
        
        self.mainLayout.addLayout(titleRow)
        self.mainLayout.addLayout(self.cardsLayout)
        self.mainLayout.addStretch()
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.viewport().setStyleSheet("background-color: transparent;")
        
        QTimer.singleShot(500, self.loadVoices)

    def __onDirectoryChanged(self, path):
        """当文件夹内容变化时自动刷新"""
        QTimer.singleShot(200, self.loadVoices)

    def loadVoices(self):
        # 清空旧卡片
        while self.cardsLayout.count():
            item = self.cardsLayout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
            
        if not self.db_path.exists():
            self.cardsLayout.addWidget(BodyLabel("暂无音色，请在生成历史中注册"))
            return
            
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                voices = json.load(f)
            
            if not voices:
                self.cardsLayout.addWidget(BodyLabel("暂无音色，请在生成历史中注册"))
                return
                
            for voice_id, voice_data in voices.items():
                self.cardsLayout.addWidget(VoiceCard(voice_data, self))
        except Exception as e:
            print(f"[VoiceLibrary] Error loading voices: {e}")
            self.cardsLayout.addWidget(BodyLabel("加载失败"))

    def onPlay(self, voice_id):
        """播放音色预览音频"""
        preview_path = self.voice_cache_dir / voice_id / "preview.wav"
        if preview_path.exists():
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(preview_path))))
            self.player.play()
            InfoBar.success(title='播放', content=f"正在试听: {voice_id}", parent=self)
        else:
            InfoBar.warning(title='提示', content="该音色暂无预览音频", parent=self)

    def onRename(self, voice_id):
        """重命名音色"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            if voice_id not in db:
                InfoBar.warning(title='提示', content="音色不存在", parent=self)
                return
            
            current_name = db[voice_id].get("name", "未命名音色")
            dialog = RenameDialog(current_name, self)
            if dialog.exec():
                new_name = dialog.name
                if not new_name:
                    InfoBar.warning(title='提示', content="名称不能为空", parent=self)
                    return
                
                # 更新数据库
                db[voice_id]["name"] = new_name
                with open(self.db_path, 'w', encoding='utf-8') as f:
                    json.dump(db, f, ensure_ascii=False, indent=4)
                
                InfoBar.success(title='成功', content=f"已重命名为: {new_name}", parent=self)
                self.loadVoices()
        except Exception as e:
            InfoBar.error(title='错误', content=str(e), parent=self)

    def onDelete(self, voice_id):
        """删除音色"""
        try:
            # 1. 读取数据库
            with open(self.db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            if voice_id not in db:
                InfoBar.warning(title='提示', content="音色不存在", parent=self)
                return
                
            # 2. 删除物理文件
            voice_folder = self.voice_cache_dir / voice_id
            if voice_folder.exists():
                shutil.rmtree(voice_folder)
            
            # 3. 更新数据库
            del db[voice_id]
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
            
            InfoBar.success(title='成功', content="音色已删除", parent=self)
            self.loadVoices()
            
            # 触发信号通知其他界面刷新
            from app.common.signal_bus import signalBus
            signalBus.voiceRegistered.emit()  # 复用此信号刷新合成界面的下拉列表
            signalBus.historyGenerated.emit()  # 通知历史界面同步状态
        except Exception as e:
            InfoBar.error(title='错误', content=str(e), parent=self)
