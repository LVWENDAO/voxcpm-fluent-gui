# coding:utf-8
from PyQt5.QtCore import Qt, QTimer, QUrl, QFileSystemWatcher
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QInputDialog
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from pathlib import Path
import json, shutil, hashlib, time

from qfluentwidgets import (
    ScrollArea, CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel, 
    PushButton, PrimaryPushButton, FluentIcon as FIF, InfoBar, TransparentToolButton,
    LineEdit, MessageBoxBase, SubtitleLabel
)

class RegisterDialog(MessageBoxBase):
    """ 注册音色弹窗 """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('注册音色', self)
        self.nameLineEdit = LineEdit(self)
        self.nameLineEdit.setPlaceholderText('请输入音色名称...')
        self.nameLineEdit.setClearButtonEnabled(True)

        # 添加控件到布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.nameLineEdit)

        # 自定义按钮文字
        self.yesButton.setText('确认注册')
        self.cancelButton.setText('取消')

        self.widget.setMinimumWidth(350)

    @property
    def name(self):
        return self.nameLineEdit.text().strip()


class HistoryCard(CardWidget):
    def __init__(self, data, parent_interface=None):
        super().__init__(parent_interface)
        self.data = data
        self.history_id = data.get("id", "")
        self.parent_interface = parent_interface
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # 标题与时长
        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel(self.data.get("text", "")[:40] + "..."))
        header.addStretch()
        header.addWidget(CaptionLabel(f"{self.data.get('duration', 0):.2f}s"))
        layout.addLayout(header)
        
        # 按钮
        btns = QHBoxLayout()
        playBtn = PushButton(FIF.PLAY, "播放")
        playBtn.clicked.connect(lambda: self.parent_interface.onPlay(self.history_id))
        btns.addWidget(playBtn)
        
        if not self.data.get("registered"):
            regBtn = PrimaryPushButton(FIF.SAVE, "注册为音色")
            regBtn.clicked.connect(lambda: self.parent_interface.onRegister(self.history_id))
            btns.addWidget(regBtn)
        
        delBtn = PushButton(FIF.DELETE, "删除")
        delBtn.clicked.connect(lambda: self.parent_interface.onDelete(self.history_id))
        btns.addWidget(delBtn)
        btns.addStretch()
        layout.addLayout(btns)

class HistoryInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyInterface")
        
        # 初始化播放器 (PyQt5 风格)
        self.player = QMediaPlayer()
        
        # 初始化文件系统监听器
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.__onDirectoryChanged)
        
        self.view = QWidget()
        self.mainLayout = QVBoxLayout(self.view)
        self.cardsLayout = QVBoxLayout()
        self.cardsLayout.setAlignment(Qt.AlignTop)
        
        base_dir = Path(__file__).resolve().parent.parent.parent.parent  # 修正：多跳一层到根目录
        self.history_dir = base_dir / "outputs" / "generation_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # 开始监听历史文件夹
        self.watcher.addPath(str(self.history_dir))
        
        # 标题栏
        titleRow = QHBoxLayout()
        titleRow.addWidget(StrongBodyLabel("生成历史"))
        titleRow.addStretch()
        
        self.mainLayout.addLayout(titleRow)
        self.mainLayout.addLayout(self.cardsLayout)
        self.mainLayout.addStretch()
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.viewport().setStyleSheet("background-color: transparent;")
        
        QTimer.singleShot(500, self.loadHistory)

    def __onDirectoryChanged(self, path):
        """当文件夹内容变化时自动刷新"""
        # 增加一点延迟，确保文件写入完成
        QTimer.singleShot(200, self.loadHistory)

    def loadHistory(self):
        # 清空旧卡片
        while self.cardsLayout.count():
            item = self.cardsLayout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
            
        if not self.history_dir.exists():
            self.history_dir.mkdir(parents=True, exist_ok=True)
            
        folders = sorted([f for f in self.history_dir.iterdir() if f.is_dir()], reverse=True)
        
        if not folders:
            self.cardsLayout.addWidget(BodyLabel("暂无历史记录"))
            return
            
        for folder in folders:
            meta_file = folder / "meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.cardsLayout.addWidget(HistoryCard(data, self))
                except Exception:
                    pass

    def onPlay(self, history_id):
        audio_path = self.history_dir / history_id / "audio.wav"
        if audio_path.exists():
            # PyQt5 使用 setMedia + QMediaContent
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(audio_path))))
            self.player.play()
            InfoBar.success(title='播放', content=f"正在播放: {history_id}", parent=self)
        else:
            InfoBar.error(title='错误', content="音频文件不存在", parent=self)

    def onRegister(self, history_id):
        w = RegisterDialog(self.window())
        if not w.exec():
            return
        
        name = w.name
        if not name:
            InfoBar.warning(title='提示', content="名称不能为空", parent=self)
            return
        
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        history_folder = base_dir / "outputs" / "generation_history" / history_id
        
        # 1. 读取历史元数据
        meta_file = history_folder / "meta.json"
        if not meta_file.exists():
            InfoBar.error(title='错误', content="元数据文件缺失", parent=self)
            return
            
        with open(meta_file, 'r', encoding='utf-8') as f:
            history_meta = json.load(f)
            
        try:
            # 2. 生成 ID 并复制完整文件
            voice_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8]
            voice_cache_dir = base_dir / "outputs" / "voice_cache"
            voice_folder = voice_cache_dir / voice_id
            voice_folder.mkdir(parents=True, exist_ok=True)
            
            # 复制缓存文件
            cache_src = history_folder / "cache.pt"
            if cache_src.exists():
                shutil.copy2(str(cache_src), str(voice_folder / "cache.pt"))
            
            # 复制音频文件（用于预览）
            audio_src = history_folder / "audio.wav"
            if audio_src.exists():
                shutil.copy2(str(audio_src), str(voice_folder / "preview.wav"))
            
            # 3. 构建并保存音色元数据
            voice_meta = {
                "name": name,
                "id": voice_id,
                "created_at": history_meta.get('timestamp', ''),
                "prompt_text": history_meta.get('text', ''),
                "config": {
                    "seed": history_meta.get('seed', ''),
                    "inference_timesteps": history_meta.get('inference_timesteps', 32),
                    "cfg_value": history_meta.get('cfg_value', 4.0)
                },
                "files": {
                    "cache": str(voice_folder / "cache.pt"),
                    "preview": str(voice_folder / "preview.wav") if audio_src.exists() else None
                }
            }
            
            db_path = voice_cache_dir / "voices_db.json"
            db = {}
            if db_path.exists():
                with open(db_path, 'r', encoding='utf-8') as f: 
                    db = json.load(f)
            
            db[voice_id] = voice_meta
            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
            
            # 4. 标记历史为已注册
            history_meta['registered'] = True
            with open(meta_file, 'w', encoding='utf-8') as f: 
                json.dump(history_meta, f)
            
            InfoBar.success(title='成功', content=f"已注册至音色库: {name}", parent=self)
            self.loadHistory()
            
            # 5. 触发信号通知合成界面刷新
            from app.common.signal_bus import signalBus
            signalBus.voiceRegistered.emit()
        except Exception as e:
            InfoBar.error(title='错误', content=str(e), parent=self)

    def onDelete(self, history_id):
        folder = self.history_dir / history_id
        if folder.exists():
            shutil.rmtree(folder)
            self.loadHistory()
            InfoBar.success(title='成功', content="记录已删除", parent=self)
