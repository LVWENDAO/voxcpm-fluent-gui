# coding:utf-8
from PyQt5.QtCore import Qt, QTimer, QUrl
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
        
        self.view = QWidget()
        self.mainLayout = QVBoxLayout(self.view)
        self.cardsLayout = QVBoxLayout()
        self.cardsLayout.setAlignment(Qt.AlignTop)
        
        base_dir = Path(__file__).resolve().parent.parent.parent.parent  # 修正：多跳一层到根目录
        self.history_dir = base_dir / "outputs" / "generation_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # 标题栏
        titleRow = QHBoxLayout()
        titleRow.addWidget(StrongBodyLabel("生成历史"))
        titleRow.addStretch()
        refreshBtn = TransparentToolButton(FIF.SYNC)
        refreshBtn.clicked.connect(self.loadHistory)
        titleRow.addWidget(refreshBtn)
        
        self.mainLayout.addLayout(titleRow)
        self.mainLayout.addLayout(self.cardsLayout)
        self.mainLayout.addStretch()
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.viewport().setStyleSheet("background-color: transparent;")
        
        QTimer.singleShot(500, self.loadHistory)

    def loadHistory(self):
        print(f"[History Debug] Starting to load history from: {self.history_dir}")
        
        # 清空旧卡片
        while self.cardsLayout.count():
            item = self.cardsLayout.takeAt(0)
            if item.widget(): 
                print(f"[History Debug] Deleting widget: {item.widget()}")
                item.widget().deleteLater()
            
        if not self.history_dir.exists():
            print(f"[History Debug] Directory does not exist: {self.history_dir}")
            self.history_dir.mkdir(parents=True, exist_ok=True)
            
        folders = sorted([f for f in self.history_dir.iterdir() if f.is_dir()], reverse=True)
        print(f"[History Debug] Found {len(folders)} history folders")
        
        if not folders:
            print("[History Debug] No history records found, showing empty label")
            self.cardsLayout.addWidget(BodyLabel("暂无历史记录"))
            return
            
        for folder in folders:
            meta_file = folder / "meta.json"
            print(f"[History Debug] Checking folder: {folder.name}, meta exists: {meta_file.exists()}")
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"[History Debug] Loaded meta for: {data.get('id')}")
                    self.cardsLayout.addWidget(HistoryCard(data, self))
                except Exception as e:
                    print(f"[History Debug] Error loading meta for {folder.name}: {e}")

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
        
        base_dir = Path(__file__).resolve().parent.parent.parent
        history_folder = base_dir / "outputs" / "generation_history" / history_id
        cache_src = history_folder / "cache.pt"
        
        if not cache_src.exists():
            InfoBar.error(title='错误', content="缓存文件缺失", parent=self)
            return
            
        try:
            # 1. 生成 ID 并复制文件
            voice_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8]
            voice_cache_dir = base_dir / "outputs" / "voice_cache"
            cache_dst = voice_cache_dir / f"{voice_id}.pt"
            shutil.copy2(str(cache_src), str(cache_dst))
            
            # 2. 更新 voices_db.json
            db_path = voice_cache_dir / "voices_db.json"
            db = {}
            if db_path.exists():
                with open(db_path, 'r', encoding='utf-8') as f: db = json.load(f)
            
            db[voice_id] = {"name": name, "path": str(cache_dst)}
            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=4)
            
            # 3. 标记历史为已注册
            meta_file = history_folder / "meta.json"
            with open(meta_file, 'r', encoding='utf-8') as f: data = json.load(f)
            data['registered'] = True
            with open(meta_file, 'w', encoding='utf-8') as f: json.dump(data, f)
            
            InfoBar.success(title='成功', content="已注册至音色库", parent=self)
            self.loadHistory()
            
            # 4. 触发信号通知合成界面刷新
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
