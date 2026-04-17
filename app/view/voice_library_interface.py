# coding:utf-8
from PyQt5.QtCore import Qt, QTimer, QUrl, QFileSystemWatcher, QPoint
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView
from PyQt5.QtGui import QIcon
from pathlib import Path
import json, shutil

from qfluentwidgets import (
    TableWidget, StrongBodyLabel, BodyLabel, CaptionLabel, 
    PushButton, FluentIcon as FIF, InfoBar,
    LineEdit, MessageBoxBase, SubtitleLabel, RoundMenu, Action
)
from qfluentwidgets.multimedia import StandardMediaPlayBar

class RenameDialog(MessageBoxBase):
    """重命名对话框"""
    def __init__(self, current_name, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('重命名音色', self)
        self.nameLineEdit = LineEdit(self)
        self.nameLineEdit.setText(current_name)
        self.nameLineEdit.setPlaceholderText("请输入新的音色名称")
        
        # 调整布局边距，避免标题被裁剪
        self.viewLayout.setContentsMargins(24, 16, 24, 24)
        self.viewLayout.setSpacing(12)
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.nameLineEdit)
        
        # 设置按钮文本
        self.yesButton.setText('确定')
        self.cancelButton.setText('取消')
        
        self.widget.setMinimumWidth(350)
        
        # 自动聚焦
        self.nameLineEdit.setFocus()

    @property
    def name(self):
        return self.nameLineEdit.text().strip()


class VoiceLibraryInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("voiceLibraryInterface")
        
        # 主布局
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(16, 16, 16, 16)
        self.mainLayout.setSpacing(12)
        
        # 标题栏
        titleRow = QHBoxLayout()
        titleRow.addWidget(StrongBodyLabel("音色库管理"))
        titleRow.addStretch()
        self.mainLayout.addLayout(titleRow)
        
        # 音色列表表格
        self.tableView = TableWidget(self)
        self.tableView.setBorderVisible(True)
        self.tableView.setBorderRadius(8)
        self.tableView.setWordWrap(False)
        self.tableView.setColumnCount(5)
        self.tableView.setHorizontalHeaderLabels(['音色名称', 'ID', 'Seed', 'Steps', 'CFG'])
        self.tableView.verticalHeader().hide()
        self.tableView.setSelectionBehavior(TableWidget.SelectRows)
        self.tableView.setSelectionMode(TableWidget.SingleSelection)
        self.tableView.setEditTriggers(TableWidget.NoEditTriggers)
        
        # 列宽设置
        self.tableView.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableView.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tableView.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tableView.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.tableView.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.tableView.setColumnWidth(1, 100)
        self.tableView.setColumnWidth(2, 80)
        self.tableView.setColumnWidth(3, 60)
        self.tableView.setColumnWidth(4, 60)
        
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
        self.voice_cache_dir = base_dir / "voice_cache"
        self.voice_cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.voice_cache_dir / "voices_db.json"
        
        # 文件系统监听
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.__onDirectoryChanged)
        self.watcher.addPath(str(self.voice_cache_dir))
        
        # 右键菜单
        self.tableView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableView.customContextMenuRequested.connect(self.showContextMenu)
        
        QTimer.singleShot(500, self.loadVoices)

    def __onDirectoryChanged(self, path):
        """当文件夹内容变化时自动刷新"""
        QTimer.singleShot(200, self.loadVoices)

    def loadVoices(self):
        """加载音色到表格"""
        self.tableView.setRowCount(0)  # 清空表格
        
        if not self.db_path.exists():
            return
            
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                voices = json.load(f)
            
            if not voices:
                return
                
            self.tableView.setRowCount(len(voices))
            
            for row, (voice_id, voice_data) in enumerate(voices.items()):
                config = voice_data.get("config", {})
                
                # 音色名称
                name_item = QTableWidgetItem(voice_data.get("name", "未命名音色"))
                name_item.setData(Qt.UserRole, voice_id)
                self.tableView.setItem(row, 0, name_item)
                
                # ID
                self.tableView.setItem(row, 1, QTableWidgetItem(voice_id))
                
                # Seed
                self.tableView.setItem(row, 2, QTableWidgetItem(str(config.get("seed", "N/A"))))
                
                # Steps
                self.tableView.setItem(row, 3, QTableWidgetItem(str(config.get("inference_timesteps", "N/A"))))
                
                # CFG
                self.tableView.setItem(row, 4, QTableWidgetItem(str(config.get("cfg_value", "N/A"))))
                
        except Exception as e:
            print(f"[VoiceLibrary] Error loading voices: {e}")

    def onPlaySelected(self, row, column):
        """双击播放选中的音色"""
        voice_id = self.tableView.item(row, 0).data(Qt.UserRole)
        if voice_id:
            self.onPlay(voice_id)

    def onPlay(self, voice_id):
        """播放音色预览音频"""
        preview_path = self.voice_cache_dir / voice_id / "preview.wav"
        if preview_path.exists():
            self.playBar.player.setSource(QUrl.fromLocalFile(str(preview_path)))
            self.playBar.play()
            InfoBar.success(title='播放', content=f"正在试听: {voice_id}", parent=self)
        else:
            InfoBar.warning(title='提示', content="该音色暂无预览音频", parent=self)

    def showContextMenu(self, pos):
        """显示右键菜单"""
        row = self.tableView.rowAt(pos.y())
        if row < 0:
            return
        
        voice_id = self.tableView.item(row, 0).data(Qt.UserRole)
        if not voice_id:
            return
        
        menu = RoundMenu(parent=self)
        
        # 试听
        playAction = Action(FIF.PLAY, "试听")
        playAction.triggered.connect(lambda: self.onPlay(voice_id))
        menu.addAction(playAction)
        
        # 重命名
        renameAction = Action(FIF.EDIT, "重命名")
        renameAction.triggered.connect(lambda: self.onRename(voice_id))
        menu.addAction(renameAction)
        
        menu.addSeparator()
        
        # 删除
        deleteAction = Action(FIF.DELETE, "删除")
        deleteAction.triggered.connect(lambda: self.onDelete(voice_id))
        menu.addAction(deleteAction)
        
        menu.exec(self.tableView.viewport().mapToGlobal(pos))

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
