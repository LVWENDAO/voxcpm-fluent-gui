# coding:utf-8
"""
标签管理界面
顶部：分类按钮（横向可滚动），支持添加分类
下部：当前分类下的标签，使用 FlowLayout 展示，支持添加/编辑/删除
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFileDialog
import json
from pathlib import Path

from qfluentwidgets import (
    CardWidget, FlowLayout, PillPushButton, LineEdit, PushButton, 
    PrimaryPushButton, ComboBox, StrongBodyLabel, BodyLabel, CaptionLabel,
    InfoBar, FluentIcon as FIF, RoundMenu, Action, TransparentToolButton,
    Dialog, SearchLineEdit, isDarkTheme, setTheme, SegmentedWidget, PushButton, TabBar, TabCloseButtonDisplayMode
)


class TagTabBar(QWidget):
    """标签 TabBar（用于标签展示区）"""
    
    tagEdited = pyqtSignal(str, str)    # (旧文本, 新文本)
    tagDeleted = pyqtSignal(str)        # 删除标签
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []  # 标签列表
        
        # 主布局
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        
        # TabBar
        self.tabBar = TabBar(self)
        self.tabBar.setTabMaximumWidth(120)
        self.tabBar.setScrollable(True)
        self.tabBar.setMovable(False)
        self.tabBar.setCloseButtonDisplayMode(TabCloseButtonDisplayMode.ON_HOVER)
        self.tabBar.tabCloseRequested.connect(self.__on_tag_close)
        self.tabBar.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # 绑定右键菜单
        self.tabBar.customContextMenuRequested.connect(self._show_context_menu)
        
        self.mainLayout.addWidget(self.tabBar)
    
    def addTag(self, text, icon=None):
        """添加标签"""
        if text in self.tags:
            return
        
        try:
            icon_enum = getattr(FIF, icon.upper(), FIF.TAG) if icon else FIF.TAG
        except:
            icon_enum = FIF.TAG
        
        self.tabBar.addTab(
            routeKey=text,
            text=text,
            icon=icon_enum,
            onClick=lambda: None  # 标签点击不需要特殊处理
        )
        self.tags.append(text)
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        # 遍历所有标签，找到鼠标位置对应的标签
        tag_text = None
        for i, text in enumerate(self.tags):
            tab_rect = self.tabBar.tabRect(i)
            if tab_rect.contains(pos):
                tag_text = text
                break
        
        if not tag_text:
            return
        
        menu = RoundMenu(parent=self)
        editAction = Action(FIF.EDIT, "编辑标签")
        deleteAction = Action(FIF.DELETE, "删除标签")
        
        editAction.triggered.connect(lambda: self.tagEdited.emit(tag_text, ""))
        deleteAction.triggered.connect(lambda: self.tagDeleted.emit(tag_text))
        
        menu.addAction(editAction)
        menu.addAction(deleteAction)
        menu.exec(self.tabBar.mapToGlobal(pos))
    
    def __on_tag_close(self, index):
        """标签关闭"""
        if index >= 0 and index < len(self.tags):
            tag_text = self.tags[index]
            self.tagDeleted.emit(tag_text)
    
    def removeTag(self, text):
        """删除标签"""
        if text not in self.tags:
            return
        index = self.tags.index(text)
        self.tabBar.removeTab(index)
        self.tags.remove(text)
    
    def clear(self):
        """清空所有标签"""
        while self.tabBar.count() > 0:
            self.tabBar.removeTab(0)
        self.tags.clear()


class CategorySegmentedBar(SegmentedWidget):
    """分类分段导航栏（使用 SegmentedWidget）"""
    
    categoryChanged = pyqtSignal(str)  # 分类切换信号
    categoryEdited = pyqtSignal(str, str)  # (旧名称, 新名称)
    categoryDeleted = pyqtSignal(str)  # 删除分类
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = []  # 分类列表
        self.current_category = None
        
        # 启用右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def addCategory(self, name, icon="TAG"):
        """添加分类"""
        if name in self.categories:
            return
        
        # 获取图标
        try:
            icon_enum = getattr(FIF, icon.upper(), FIF.TAG)
        except:
            icon_enum = FIF.TAG
        
        self.addItem(
            routeKey=name,
            text=name,
            icon=icon_enum,
            onClick=lambda: self.onCategoryChanged(name)
        )
        self.categories.append(name)
        
        # 自动选中第一个分类
        if not self.current_category:
            self.onCategoryChanged(name)
    
    def onCategoryChanged(self, name):
        """分类切换"""
        self.current_category = name
        self.setCurrentItem(name)
        self.categoryChanged.emit(name)
    
    def clear(self):
        """清空所有分类"""
        for name in self.categories:
            self.removeWidget(name)
        self.categories.clear()
        self.current_category = None
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        # 获取点击位置的分类
        category_name = None
        for name in self.categories:
            widget = self.widget(name)
            if widget and widget.rect().contains(widget.mapFromGlobal(self.mapToGlobal(pos))):
                category_name = name
                break
        
        if not category_name:
            return
        
        menu = RoundMenu(parent=self)
        editAction = Action(FIF.EDIT, "编辑分类")
        deleteAction = Action(FIF.DELETE, "删除分类")
        
        editAction.triggered.connect(lambda: self.categoryEdited.emit(category_name, ""))
        deleteAction.triggered.connect(lambda: self.categoryDeleted.emit(category_name))
        
        menu.addAction(editAction)
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(pos))


class TagManagerInterface(QWidget):
    """标签管理界面"""
    
    tagsUpdated = pyqtSignal()  # 标签更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tagManagerInterface")
        
        # 配置文件路径
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.config_dir = base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "tags_config.json"
        
        # 数据模型
        self.tags_config = {}  # {category_name: {icon, tags: [{text, icon}]}}
        
        self.__init_ui()
        self.__load_config()
    
    def __init_ui(self):
        """初始化UI"""
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(24, 16, 24, 24)
        self.mainLayout.setSpacing(16)
        
        # 标题
        titleLayout = QHBoxLayout()
        self.titleLabel = StrongBodyLabel("控制指令标签管理", self)
        titleLayout.addWidget(self.titleLabel)
        titleLayout.addStretch()
        self.mainLayout.addLayout(titleLayout)
        
        # 分类分段导航栏（使用 SegmentedWidget）
        self.categoryBar = CategorySegmentedBar(self)
        self.categoryBar.categoryChanged.connect(self.__on_category_changed)
        self.categoryBar.categoryEdited.connect(self.__on_category_edited)
        self.categoryBar.categoryDeleted.connect(self.__on_category_deleted)
        self.mainLayout.addWidget(self.categoryBar)
        
        # 添加分类按钮
        self.addCategoryBtn = PushButton(FIF.ADD, "添加分类", self)
        self.addCategoryBtn.clicked.connect(self.__on_add_category)
        self.mainLayout.addWidget(self.addCategoryBtn, alignment=Qt.AlignRight)
        
        # 当前分类标题
        self.currentCategoryLabel = StrongBodyLabel("未选择分类", self)
        self.mainLayout.addWidget(self.currentCategoryLabel)
        
        # 工具栏
        toolbarLayout = QHBoxLayout()
        self.addTagBtn = PrimaryPushButton(FIF.ADD, "添加标签", self)
        self.addTagBtn.clicked.connect(self.__on_add_tag)
        toolbarLayout.addWidget(self.addTagBtn)
        
        toolbarLayout.addStretch()
        
        self.searchBox = SearchLineEdit()
        self.searchBox.setPlaceholderText("搜索标签...")
        self.searchBox.setFixedWidth(240)
        self.searchBox.textChanged.connect(self.__on_search)
        toolbarLayout.addWidget(self.searchBox)
        
        self.mainLayout.addLayout(toolbarLayout)
        
        # 标签展示区域（使用 TabBar）
        self.tagCard = CardWidget(self)
        self.tagCardLayout = QVBoxLayout(self.tagCard)
        self.tagCardLayout.setContentsMargins(16, 16, 16, 16)
                
        self.tagTabBar = TagTabBar(self)
        self.tagTabBar.tagEdited.connect(self.__on_tag_edited)
        self.tagTabBar.tagDeleted.connect(self.__on_tag_deleted)
        self.tagCardLayout.addWidget(self.tagTabBar)
                
        self.mainLayout.addWidget(self.tagCard, 1)
        
        # 底部统计
        statsLayout = QHBoxLayout()
        self.statsLabel = CaptionLabel("", self)
        statsLayout.addWidget(self.statsLabel)
        statsLayout.addStretch()
        self.mainLayout.addLayout(statsLayout)
    
    def __load_config(self):
        """加载配置"""
        if not self.config_file.exists():
            self.__create_default_config()
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.tags_config = json.load(f)
            
            self.__refresh_categories()
        except Exception as e:
            InfoBar.error(title='错误', content=f"加载配置失败: {str(e)}", parent=self)
    
    def __create_default_config(self):
        """创建默认配置"""
        self.tags_config = {
            "音色类型": {
                "icon": "PEOPLE",
                "tags": [
                    {"text": "年轻女声", "icon": None},
                    {"text": "成熟男声", "icon": None},
                    {"text": "童声", "icon": None}
                ]
            },
            "情感风格": {
                "icon": "HEART",
                "tags": [
                    {"text": "欢快", "icon": None},
                    {"text": "严肃", "icon": None},
                    {"text": "温柔", "icon": None}
                ]
            },
            "地域特色": {
                "icon": "GLOBE",
                "tags": [
                    {"text": "东北腔", "icon": None},
                    {"text": "四川腔", "icon": None}
                ]
            }
        }
        
        self.__save_config()
        self.__refresh_categories()
    
    def __save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.tags_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            InfoBar.error(title='错误', content=f"保存配置失败: {str(e)}", parent=self)
    
    def __refresh_categories(self):
        """刷新分类栏"""
        self.categoryBar.clear()
        
        for category_name in self.tags_config.keys():
            self.categoryBar.addCategory(category_name)
    
    def __refresh_tags(self, category_name, search_text=''):
        """刷新标签展示"""
        if category_name not in self.tags_config:
            return
        
        category_data = self.tags_config[category_name]
        
        # 搜索过滤
        if search_text:
            tags = category_data.get('tags', [])
            tags = [t for t in tags if search_text.lower() in t.get('text', '').lower()]
        else:
            tags = category_data.get('tags', [])
        
        # 清空现有标签
        self.tagTabBar.clear()
                
        # 添加标签到 TabBar
        for tag_data in tags:
            self.tagTabBar.addTag(tag_data['text'], tag_data.get('icon'))
        
        # 更新统计
        total_tags = len(category_data.get('tags', []))
        self.statsLabel.setText(f"共 {total_tags} 个标签")
    
    def __on_category_changed(self, category_name):
        """分类切换"""
        self.currentCategoryLabel.setText(category_name)
        self.__refresh_tags(category_name)
    
    def __on_add_category(self):
        """添加分类"""
        # 使用 Dialog 输入分类名称
        dialog = Dialog("添加新分类", "请输入分类名称", self)
        input_widget = LineEdit()
        input_widget.setPlaceholderText("例如：音色类型、情感风格")
        dialog.vBoxLayout.insertWidget(1, input_widget)
        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            name = input_widget.text().strip()
            if not name:
                InfoBar.warning(title='提示', content="分类名称不能为空", parent=self)
                return
            
            if name in self.tags_config:
                InfoBar.warning(title='提示', content="该分类已存在", parent=self)
                return
            
            self.tags_config[name] = {
                "icon": "TAG",
                "tags": []
            }
            
            self.__save_config()
            self.__refresh_categories()
            
            # 自动选中新分类
            self.categoryBar.onCategoryChanged(name)
            
            InfoBar.success(title='成功', content=f"已添加分类: {name}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_category_edited(self, old_name, _):
        """编辑分类"""
        # 使用 Dialog 输入新名称
        dialog = Dialog("编辑分类", "请输入新的分类名称", self)
        input_widget = LineEdit()
        input_widget.setText(old_name)
        input_widget.setPlaceholderText("例如：音色类型、情感风格")
        dialog.vBoxLayout.insertWidget(1, input_widget)
        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            new_name = input_widget.text().strip()
            if not new_name:
                InfoBar.warning(title='提示', content="分类名称不能为空", parent=self)
                return
            
            if new_name == old_name:
                return
            
            if new_name in self.tags_config:
                InfoBar.warning(title='提示', content="该分类已存在", parent=self)
                return
            
            # 重命名分类
            self.tags_config[new_name] = self.tags_config.pop(old_name)
            
            self.__save_config()
            self.__refresh_categories()
            
            # 如果当前是被重命名的分类，更新选中状态
            if self.categoryBar.current_category == old_name:
                self.categoryBar.onCategoryChanged(new_name)
            
            InfoBar.success(title='成功', content=f"已重命名分类: {old_name} → {new_name}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_category_deleted(self, category_name):
        """删除分类"""
        # 确认删除
        dialog = Dialog("确认删除", f"确定要删除分类「{category_name}」及其所有标签吗？", self)
        dialog.yesButton.setText("删除")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            del self.tags_config[category_name]
            
            self.__save_config()
            self.__refresh_categories()
            
            # 清空标签显示
            self.tagTabBar.clear()
            self.currentCategoryLabel.setText("未选择分类")
            self.statsLabel.setText("")
            
            InfoBar.success(title='成功', content=f"已删除分类: {category_name}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_add_tag(self):
        """添加标签"""
        if not self.categoryBar.current_category:
            InfoBar.warning(title='提示', content="请先选择或添加一个分类", parent=self)
            return
        
        # 使用 Dialog 输入标签
        dialog = Dialog("添加新标签", "请填写标签信息", self)
        dialog.vBoxLayout.setSpacing(12)
        
        # 标签文本输入
        textLayout = QHBoxLayout()
        textLayout.addWidget(BodyLabel("标签文本:"))
        textInput = LineEdit()
        textInput.setPlaceholderText("例如：年轻女声、欢快")
        textInput.setMinimumWidth(250)
        textLayout.addWidget(textInput)
        textLayout.addStretch()
        dialog.vBoxLayout.addLayout(textLayout)
        
        dialog.yesButton.setText("添加")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            text = textInput.text().strip()
            if not text:
                InfoBar.warning(title='提示', content="标签文本不能为空", parent=self)
                return
            
            category = self.categoryBar.current_category
            tags = self.tags_config[category].get('tags', [])
            
            # 检查重复
            if any(t['text'] == text for t in tags):
                InfoBar.warning(title='提示', content="该标签已存在", parent=self)
                return
            
            tags.append({"text": text, "icon": None})
            self.tags_config[category]['tags'] = tags
            
            self.__save_config()
            self.__refresh_tags(category)
            
            InfoBar.success(title='成功', content=f"已添加标签: {text}", parent=self)
            self.tagsUpdated.emit()
    
    def editTag(self, tag_btn):
        """编辑标签（从 TagButton 右键菜单调用）"""
        category = self.categoryBar.current_category
        if not category:
            return
        
        old_text = tag_btn.text()
        
        # 使用 Dialog 编辑
        dialog = Dialog("编辑标签", "修改标签信息", self)
        dialog.vBoxLayout.setSpacing(12)
        
        textLayout = QHBoxLayout()
        textLayout.addWidget(BodyLabel("标签文本:"))
        textInput = LineEdit()
        textInput.setText(old_text)
        textInput.setMinimumWidth(250)
        textLayout.addWidget(textInput)
        textLayout.addStretch()
        dialog.vBoxLayout.addLayout(textLayout)
        
        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            new_text = textInput.text().strip()
            if not new_text:
                InfoBar.warning(title='提示', content="标签文本不能为空", parent=self)
                return
            
            tags = self.tags_config[category].get('tags', [])
            
            # 检查重复（排除自身）
            if any(t['text'] == new_text for t in tags if t['text'] != old_text):
                InfoBar.warning(title='提示', content="该标签已存在", parent=self)
                return
            
            # 更新标签
            for tag in tags:
                if tag['text'] == old_text:
                    tag['text'] = new_text
                    break
            
            self.__save_config()
            self.__refresh_tags(category)
            
            InfoBar.success(title='成功', content=f"已更新标签: {new_text}", parent=self)
            self.tagsUpdated.emit()
    
    def deleteTag(self, tag_btn):
        """删除标签（从 TagButton 右键菜单调用）"""
        category = self.categoryBar.current_category
        if not category:
            return
        
        text = tag_btn.text()
        
        # 确认删除
        dialog = Dialog("确认删除", f"确定要删除标签「{text}」吗？", self)
        dialog.yesButton.setText("删除")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            tags = self.tags_config[category].get('tags', [])
            self.tags_config[category]['tags'] = [t for t in tags if t['text'] != text]
            
            self.__save_config()
            self.__refresh_tags(category)
            
            InfoBar.success(title='成功', content=f"已删除标签: {text}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_tag_clicked(self, text):
        """标签点击（转发给合成界面）"""
        from app.common.signal_bus import signalBus
        signalBus.tagToggled.emit(text)
    
    def __on_tag_edited(self, old_text, _):
        """编辑标签"""
        category = self.categoryBar.current_category
        if not category:
            return
        
        # 使用 Dialog 编辑
        dialog = Dialog("编辑标签", "修改标签信息", self)
        dialog.vBoxLayout.setSpacing(12)
        
        textLayout = QHBoxLayout()
        textLayout.addWidget(BodyLabel("标签文本:"))
        textInput = LineEdit()
        textInput.setText(old_text)
        textInput.setMinimumWidth(250)
        textLayout.addWidget(textInput)
        textLayout.addStretch()
        dialog.vBoxLayout.addLayout(textLayout)
        
        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")
        
        if dialog.exec():
            new_text = textInput.text().strip()
            if not new_text:
                InfoBar.warning(title='提示', content="标签文本不能为空", parent=self)
                return
            
            tags = self.tags_config[category].get('tags', [])
            
            # 检查重复（排除自身）
            if any(t['text'] == new_text for t in tags if t['text'] != old_text):
                InfoBar.warning(title='提示', content="该标签已存在", parent=self)
                return
            
            # 更新标签
            for tag in tags:
                if tag['text'] == old_text:
                    tag['text'] = new_text
                    break
            
            self.__save_config()
            self.__refresh_tags(category)
            
            InfoBar.success(title='成功', content=f"已更新标签: {new_text}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_tag_deleted(self, tag_text):
        """删除标签"""
        category = self.categoryBar.current_category
        if not category:
            return
        
        tags = self.tags_config[category].get('tags', [])
        self.tags_config[category]['tags'] = [t for t in tags if t['text'] != tag_text]
        
        self.__save_config()
        self.__refresh_tags(category)
        
        InfoBar.success(title='成功', content=f"已删除标签: {tag_text}", parent=self)
        self.tagsUpdated.emit()
    
    def __on_search(self, text):
        """搜索标签"""
        if self.categoryBar.current_category:
            self.__refresh_tags(self.categoryBar.current_category, text)
    
    def get_tags_config(self):
        """获取标签配置（供合成界面使用）"""
        return self.tags_config
