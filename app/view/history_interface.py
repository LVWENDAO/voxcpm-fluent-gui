# coding:utf-8
from PyQt5.QtCore import Qt, QTimer, QUrl, QFileSystemWatcher, QSize, QPoint
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QFileDialog
from PyQt5.QtGui import QIcon
from pathlib import Path
import json, shutil, hashlib, time

from qfluentwidgets import (
    TableWidget, StrongBodyLabel, BodyLabel, CaptionLabel, 
    PushButton, PrimaryPushButton, FluentIcon as FIF, InfoBar,
    LineEdit, MessageBoxBase, SubtitleLabel, IconWidget, RoundMenu, Action
)
from qfluentwidgets.multimedia import StandardMediaPlayBar

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


class HistoryInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyInterface")
        
        # 主布局
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(16, 16, 16, 16)
        self.mainLayout.setSpacing(12)
        
        # 标题栏
        titleRow = QHBoxLayout()
        titleRow.addWidget(StrongBodyLabel("生成历史"))
        titleRow.addStretch()
        
        clearAllBtn = PushButton(FIF.DELETE, "清理所有记录")
        clearAllBtn.clicked.connect(self.onClearAll)
        titleRow.addWidget(clearAllBtn)
        
        self.mainLayout.addLayout(titleRow)
        
        # 音频列表表格
        self.tableView = TableWidget(self)
        self.tableView.setBorderVisible(True)
        self.tableView.setBorderRadius(8)
        self.tableView.setWordWrap(False)
        self.tableView.setColumnCount(4)
        self.tableView.setHorizontalHeaderLabels(['文本内容', '时长', '生成时间', '状态'])
        self.tableView.verticalHeader().hide()
        self.tableView.setSelectionBehavior(TableWidget.SelectRows)
        self.tableView.setSelectionMode(TableWidget.SingleSelection)
        self.tableView.setEditTriggers(TableWidget.NoEditTriggers)
        
        # 列宽设置
        self.tableView.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableView.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tableView.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tableView.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.tableView.setColumnWidth(1, 80)
        self.tableView.setColumnWidth(2, 150)
        self.tableView.setColumnWidth(3, 100)
        
        self.tableView.cellDoubleClicked.connect(self.onPlaySelected)
        
        self.mainLayout.addWidget(self.tableView)
        
        # 底部播放控制栏
        self.playBar = StandardMediaPlayBar(self)
        
        # 注册到全局音频管理器
        from app.common.audio_manager import audioManager
        audioManager.register_player(self.playBar)
        
        self.mainLayout.addWidget(self.playBar)
        
        # 路径配置
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.history_dir = base_dir / "outputs" / "generation_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件系统监听
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.__onDirectoryChanged)
        self.watcher.addPath(str(self.history_dir))
        
        # 右键菜单
        self.tableView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableView.customContextMenuRequested.connect(self.showContextMenu)
        
        # 信号监听
        from app.common.signal_bus import signalBus
        signalBus.voiceRegistered.connect(self.__onVoiceStatusChanged)
        signalBus.voiceDeleted.connect(self.__onVoiceStatusChanged)
        signalBus.historyGenerated.connect(self.loadHistory)
        
        # 启动加载
        QTimer.singleShot(500, self.loadHistory)

    def __onDirectoryChanged(self, path):
        """当文件夹内容变化时自动刷新"""
        QTimer.singleShot(500, self.loadHistory)

    def __onVoiceStatusChanged(self):
        """响应音色库变动信号，刷新表格"""
        self.loadHistory()

    def loadHistory(self):
        """加载历史记录到表格"""
        self.tableView.setRowCount(0)  # 清空表格
        
        if not self.history_dir.exists():
            self.history_dir.mkdir(parents=True, exist_ok=True)
            return
            
        folders = sorted([f for f in self.history_dir.iterdir() if f.is_dir()], reverse=True)
        
        if not folders:
            return
            
        self.tableView.setRowCount(len(folders))
        
        for row, folder in enumerate(folders):
            meta_file = folder / "meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 文本内容
                    text = data.get("text", "")[:50]
                    if len(data.get("text", "")) > 50:
                        text += "..."
                    self.tableView.setItem(row, 0, QTableWidgetItem(text))
                    self.tableView.item(row, 0).setData(Qt.UserRole, data.get("id", ""))
                    
                    # 时长
                    duration = data.get('duration', 0)
                    self.tableView.setItem(row, 1, QTableWidgetItem(f"{duration:.2f}s"))
                    
                    # 生成时间
                    timestamp = data.get('timestamp', '')
                    self.tableView.setItem(row, 2, QTableWidgetItem(timestamp))
                    
                    # 注册状态
                    is_registered = data.get('registered_voice_id') and self._is_voice_valid(data.get('registered_voice_id'))
                    status_item = QTableWidgetItem("✓ 已注册" if is_registered else "未注册")
                    status_item.setForeground(Qt.green if is_registered else Qt.gray)
                    self.tableView.setItem(row, 3, status_item)
                    
                except Exception as e:
                    print(f"[History] Error loading {folder}: {e}")

    def _is_voice_valid(self, voice_id):
        """检查音色是否在数据库中"""
        if not voice_id:
            return False
        try:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            db_path = base_dir / "voice_cache" / "voices_db.json"
            if not db_path.exists():
                return False
            with open(db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            return voice_id in db
        except:
            return False

    def onPlaySelected(self, row, column):
        """双击播放选中的音频"""
        history_id = self.tableView.item(row, 0).data(Qt.UserRole)
        if history_id:
            self.onPlay(history_id)

    def onPlay(self, history_id):
        """播放音频"""
        audio_path = self.history_dir / history_id / "audio.wav"
        if audio_path.exists():
            from PyQt5.QtMultimedia import QMediaContent
            self.playBar.player.setSource(QUrl.fromLocalFile(str(audio_path)))
            self.playBar.play()
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
            voice_cache_dir = base_dir / "voice_cache"  # 独立于 outputs
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
            
            # 4. 标记历史并记录关联的 voice_id
            history_meta['registered'] = True
            history_meta['registered_voice_id'] = voice_id
            with open(meta_file, 'w', encoding='utf-8') as f: 
                json.dump(history_meta, f)
            
            InfoBar.success(title='成功', content=f"已注册至音色库: {name}", parent=self)
            self.loadHistory()
            
            # 触发信号通知其他界面
            from app.common.signal_bus import signalBus
            signalBus.voiceRegistered.emit()
            signalBus.historyGenerated.emit()
        except Exception as e:
            InfoBar.error(title='错误', content=str(e), parent=self)

    def onClearAll(self):
        """清理所有历史记录"""
        # 创建确认对话框
        dialog = MessageBoxBase(self)
        dialog.titleLabel = SubtitleLabel('确认清理', self)
        dialog.contentLabel = BodyLabel('此操作将永久删除所有生成历史记录，且不可撤销。\n\n是否继续？', self)
        
        dialog.viewLayout.addWidget(dialog.titleLabel)
        dialog.viewLayout.addWidget(dialog.contentLabel)
        dialog.viewLayout.setSpacing(10)
        
        dialog.yesButton.setText('确定删除')
        dialog.cancelButton.setText('取消')
        dialog.yesButton.setStyleSheet("background-color: #e81123; color: white;")
        
        if dialog.exec():
            try:
                import shutil
                if self.history_dir.exists():
                    shutil.rmtree(self.history_dir)
                    self.history_dir.mkdir(parents=True, exist_ok=True)
                
                InfoBar.success(title='成功', content="所有历史记录已清理", parent=self)
                self.loadHistory()
            except Exception as e:
                InfoBar.error(title='错误', content=str(e), parent=self)

    def showContextMenu(self, pos):
        """显示右键菜单"""
        row = self.tableView.rowAt(pos.y())
        if row < 0:
            return
        
        history_id = self.tableView.item(row, 0).data(Qt.UserRole)
        if not history_id:
            return
        
        menu = RoundMenu(parent=self)
        
        # 播放
        playAction = Action(FIF.PLAY, "播放")
        playAction.triggered.connect(lambda: self.onPlay(history_id))
        menu.addAction(playAction)
        
        # 另存为
        saveAsAction = Action(FIF.SAVE_AS, "另存为")
        
        # 获取目标文本作为默认文件名
        folder = self.history_dir / history_id
        audio_file = folder / "audio.wav"
        default_name = f"{history_id}.wav"
        
        if audio_file.exists():
            meta_file = folder / "meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    text = data.get("text", "audio").strip()
                    # 清理文件名中的非法字符
                    for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                        text = text.replace(char, '')
                    if text:
                        default_name = text[:50] + ".wav"
                except:
                    pass
        
        def on_save_as(dname=default_name):
            # 重新获取最新数据，避免闭包变量过期
            fid = history_id
            folder = self.history_dir / fid
            audio_file = folder / "audio.wav"
            if not audio_file.exists():
                InfoBar.warning(title='提示', content="音频文件不存在", parent=self)
                return
            
            save_path, _ = QFileDialog.getSaveFileName(
                self.window(), "另存为", 
                dname, 
                "Audio Files (*.wav *.mp3 *.flac)"
            )
            if save_path:
                shutil.copy2(str(audio_file), save_path)
                InfoBar.success(title='成功', content="文件已保存", parent=self, duration=2000)
        
        saveAsAction.triggered.connect(lambda: on_save_as())
        menu.addAction(saveAsAction)
        
        # 注册
        registerAction = Action(FIF.SAVE, "注册为音色")
        registerAction.triggered.connect(lambda: self.onRegister(history_id))
        menu.addAction(registerAction)
        
        menu.addSeparator()
        
        # 删除
        deleteAction = Action(FIF.DELETE, "删除")
        deleteAction.triggered.connect(lambda: self.onDelete(history_id))
        menu.addAction(deleteAction)
        
        menu.exec(self.tableView.viewport().mapToGlobal(pos))

    def onDelete(self, history_id):
        """删除单条记录"""
        folder = self.history_dir / history_id
        if folder.exists():
            shutil.rmtree(folder)
            self.loadHistory()
            InfoBar.success(title='成功', content="记录已删除", parent=self)
