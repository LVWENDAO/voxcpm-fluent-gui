# coding:utf-8
"""
标签管理界面
垂直列表布局：一行一个分类，分类内横向展示所有标签
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
import json
from pathlib import Path

from qfluentwidgets import (
    ScrollArea, FlowLayout, PillPushButton, LineEdit, PushButton,
    PrimaryPushButton, ComboBox, StrongBodyLabel, BodyLabel, CaptionLabel,
    InfoBar, FluentIcon as FIF, RoundMenu, Action, TransparentToolButton,
    MessageBoxBase, SubtitleLabel, SearchLineEdit, isDarkTheme, setTheme, SegmentedWidget, TabBar, TabCloseButtonDisplayMode, ToolButton,
    SimpleCardWidget
)
from app.common.resource_utils import get_resource_path


class InputDialog(MessageBoxBase):
    """通用输入对话框"""
    def __init__(self, title, placeholder="", parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.inputLineEdit = LineEdit(self)
        self.inputLineEdit.setPlaceholderText(placeholder)
        
        # 调整布局边距，避免标题被裁剪
        self.viewLayout.setContentsMargins(24, 16, 24, 24)
        self.viewLayout.setSpacing(12)
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.inputLineEdit)
        
        self.yesButton.setText('确定')
        self.cancelButton.setText('取消')
        
        self.widget.setMinimumWidth(350)
        
        self.inputLineEdit.setFocus()
    
    @property
    def text(self):
        return self.inputLineEdit.text().strip()


class AddTagDialog(MessageBoxBase):
    """添加标签对话框（含分类选择）"""
    def __init__(self, categories, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('添加新标签', self)
        
        # 调整布局边距，避免标题被裁剪
        self.viewLayout.setContentsMargins(24, 16, 24, 24)
        self.viewLayout.setSpacing(12)
        
        # 分类选择
        catLayout = QHBoxLayout()
        catLayout.addWidget(BodyLabel("选择分类:"))
        self.catCombo = ComboBox()
        self.catCombo.addItems(categories)
        self.catCombo.setMinimumWidth(200)
        catLayout.addWidget(self.catCombo)
        catLayout.addStretch()
        
        # 标签文本输入
        textLayout = QHBoxLayout()
        textLayout.addWidget(BodyLabel("标签文本:"))
        self.textInput = LineEdit()
        self.textInput.setPlaceholderText("例如：年轻女声、欢快")
        self.textInput.setMinimumWidth(250)
        textLayout.addWidget(self.textInput)
        textLayout.addStretch()
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(catLayout)
        self.viewLayout.addLayout(textLayout)
        
        self.yesButton.setText('添加')
        self.cancelButton.setText('取消')
        
        self.textInput.setFocus()
    
    @property
    def category(self):
        return self.catCombo.currentText()
    
    @property
    def text(self):
        return self.textInput.text().strip()


class EditTagDialog(MessageBoxBase):
    """编辑标签对话框"""
    def __init__(self, old_text, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('编辑标签', self)
        
        # 调整布局边距，避免标题被裁剪
        self.viewLayout.setContentsMargins(24, 16, 24, 24)
        self.viewLayout.setSpacing(12)
        
        textLayout = QHBoxLayout()
        textLayout.addWidget(BodyLabel("标签文本:"))
        self.textInput = LineEdit()
        self.textInput.setText(old_text)
        self.textInput.setMinimumWidth(250)
        textLayout.addWidget(self.textInput)
        textLayout.addStretch()
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(textLayout)
        
        self.yesButton.setText('确定')
        self.cancelButton.setText('取消')
        
        self.textInput.setFocus()
    
    @property
    def text(self):
        return self.textInput.text().strip()


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
        base_dir = get_resource_path()
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
        
        # 工具栏
        toolbarLayout = QHBoxLayout()
        self.addCategoryBtn = PrimaryPushButton(FIF.ADD, "添加分类", self)
        self.addCategoryBtn.clicked.connect(self.__on_add_category)
        toolbarLayout.addWidget(self.addCategoryBtn)
        
        toolbarLayout.addStretch()
        
        self.searchBox = SearchLineEdit()
        self.searchBox.setPlaceholderText("搜索标签...")
        self.searchBox.setFixedWidth(240)
        self.searchBox.textChanged.connect(self.__on_search)
        toolbarLayout.addWidget(self.searchBox)
        
        self.mainLayout.addLayout(toolbarLayout)
        
        # 标签展示区域（使用 Fluent ScrollArea）
        self.scrollArea = ScrollArea(self)
        self.scrollArea.setObjectName("scrollArea")
        
        # 内容容器
        self.contentWidget = QWidget()
        self.contentWidget.setObjectName("contentWidget")
        self.contentLayout = QVBoxLayout(self.contentWidget)
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(12)
        
        self.scrollArea.setWidget(self.contentWidget)
        self.scrollArea.setWidgetResizable(True)
        self.mainLayout.addWidget(self.scrollArea, 1)
        
        # 底部统计
        statsLayout = QHBoxLayout()
        self.statsLabel = CaptionLabel("", self)
        statsLayout.addWidget(self.statsLabel)
        statsLayout.addStretch()
        self.mainLayout.addLayout(statsLayout)
        
        # 加载QSS样式
        from app.common.style_sheet import StyleSheet
        StyleSheet.TAG_MANAGER_INTERFACE.apply(self)
        
        # 设置滚动区域和内容容器背景透明（参考 synthesis_interface 的实现）
        self.scrollArea.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.scrollArea.viewport().setStyleSheet("background-color: transparent;")
        self.contentWidget.setStyleSheet("background-color: transparent;")
    
    def __load_config(self):
        """加载配置"""
        if not self.config_file.exists():
            self.__create_default_config()
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.tags_config = json.load(f)
            
            self.__refresh_all_tags()
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
        self.__refresh_all_tags()
    
    def __save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.tags_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            InfoBar.error(title='错误', content=f"保存配置失败: {str(e)}", parent=self)
    
    def __refresh_all_tags(self, search_text=''):
        """刷新所有分类和标签（垂直列表布局）"""
        # 清空现有内容
        while self.contentLayout.count():
            item = self.contentLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                # 递归清除子布局
                sub_layout = item.layout()
                while sub_layout.count():
                    sub_item = sub_layout.takeAt(0)
                    sub_widget = sub_item.widget()
                    if sub_widget:
                        sub_widget.deleteLater()
        
        total_tags = 0
        
        # 遍历所有分类
        for category_name, category_data in self.tags_config.items():
            tags = category_data.get('tags', [])
            
            # 搜索过滤
            if search_text:
                filtered_tags = [t for t in tags if search_text.lower() in t.get('text', '').lower()]
                if not filtered_tags:
                    continue  # 跳过没有匹配标签的分类
                tags = filtered_tags
            
            total_tags += len(tags)
            
            # 创建分类容器（使用 SimpleCardWidget 实现主题适配）
            category_card = SimpleCardWidget(self)
            category_card.setObjectName("categoryCard")
            category_layout = QVBoxLayout(category_card)
            category_layout.setContentsMargins(16, 12, 16, 12)
            category_layout.setSpacing(8)
            
            # 分类标题行
            title_layout = QHBoxLayout()
            category_title = StrongBodyLabel(category_name, self)
            title_layout.addWidget(category_title)
            title_layout.addStretch()
            
            # 添加标签按钮（在分类工具栏上）
            add_tag_btn = PushButton(FIF.ADD, "添加标签", self)
            add_tag_btn.clicked.connect(lambda checked, cat=category_name: self.__on_add_tag_to_category(cat))
            title_layout.addWidget(add_tag_btn)
            
            # 分类操作按钮
            edit_btn = ToolButton(FIF.EDIT, self)
            edit_btn.setToolTip("编辑分类")
            edit_btn.clicked.connect(lambda checked, cat=category_name: self.__on_category_edited(cat, ""))
            title_layout.addWidget(edit_btn)
            
            delete_btn = ToolButton(FIF.DELETE, self)
            delete_btn.setToolTip("删除分类")
            delete_btn.clicked.connect(lambda checked, cat=category_name: self.__on_category_deleted(cat))
            title_layout.addWidget(delete_btn)
            
            category_layout.addLayout(title_layout)
            
            # 标签容器（横向流式布局）
            tags_widget = QWidget(self)
            tags_layout = FlowLayout(tags_widget, needAni=False)
            tags_layout.setSpacing(8)
            tags_layout.setContentsMargins(0, 0, 0, 0)
            
            # 添加标签按钮
            for tag_data in tags:
                tag_btn = PillPushButton(tag_data['text'], self)
                tag_btn.setProperty("tag_text", tag_data['text'])
                
                # 右键菜单
                tag_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                tag_btn.customContextMenuRequested.connect(
                    lambda pos, t=tag_data['text']: self.__show_tag_context_menu(pos, t)
                )
                
                tags_layout.addWidget(tag_btn)
            
            if not tags:
                empty_label = CaptionLabel("暂无标签，点击“添加标签”创建", self)
                empty_label.setObjectName("emptyTagLabel")
                empty_label.setProperty("isBody", True)
                tags_layout.addWidget(empty_label)
            
            category_layout.addWidget(tags_widget)
            self.contentLayout.addWidget(category_card)
        
        # 添加弹性空间
        self.contentLayout.addStretch()
        
        # 更新统计
        self.statsLabel.setText(f"共 {len(self.tags_config)} 个分类，{total_tags} 个标签")
    
    def __show_tag_context_menu(self, pos, tag_text):
        """显示标签右键菜单"""
        sender = self.sender()
        if not sender:
            return
        
        menu = RoundMenu(parent=self)
        editAction = Action(FIF.EDIT, "编辑标签")
        deleteAction = Action(FIF.DELETE, "删除标签")
        
        editAction.triggered.connect(lambda: self.__on_tag_edited(tag_text, ""))
        deleteAction.triggered.connect(lambda: self.__on_tag_deleted(tag_text))
        
        menu.addAction(editAction)
        menu.addAction(deleteAction)
        menu.exec(sender.mapToGlobal(pos))
    
    def __on_add_category(self):
        """添加分类"""
        dialog = InputDialog("添加新分类", "例如：音色类型、情感风格", self)
        
        if dialog.exec():
            name = dialog.text
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
            self.__refresh_all_tags()
            
            InfoBar.success(title='成功', content=f"已添加分类: {name}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_category_edited(self, old_name, _):
        """编辑分类"""
        dialog = InputDialog("编辑分类", "例如：音色类型、情感风格", self)
        dialog.inputLineEdit.setText(old_name)
        
        if dialog.exec():
            new_name = dialog.text
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
            self.__refresh_all_tags()
            
            InfoBar.success(title='成功', content=f"已重命名分类: {old_name} → {new_name}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_category_deleted(self, category_name):
        """删除分类"""
        from qfluentwidgets import MessageBox
        w = MessageBox("确认删除", f"确定要删除分类「{category_name}」及其所有标签吗？", self.window())
        w.yesButton.setText("删除")
        w.cancelButton.setText("取消")
        
        if w.exec():
            del self.tags_config[category_name]
            
            self.__save_config()
            self.__refresh_all_tags()
            
            InfoBar.success(title='成功', content=f"已删除分类: {category_name}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_add_tag_to_category(self, category):
        """向指定分类添加标签"""
        dialog = InputDialog("添加新标签", "例如：年轻女声、欢快", self)
        
        if dialog.exec():
            text = dialog.text
            if not text:
                InfoBar.warning(title='提示', content="标签文本不能为空", parent=self)
                return
            
            tags = self.tags_config[category].get('tags', [])
            
            # 检查重复
            if any(t['text'] == text for t in tags):
                InfoBar.warning(title='提示', content="该标签已存在", parent=self)
                return
            
            tags.append({"text": text, "icon": None})
            self.tags_config[category]['tags'] = tags
            
            self.__save_config()
            self.__refresh_all_tags()
            
            InfoBar.success(title='成功', content=f"已添加标签: {text}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_add_tag(self):
        """添加标签"""
        if not self.tags_config:
            InfoBar.warning(title='提示', content="请先添加一个分类", parent=self)
            return
        
        dialog = AddTagDialog(list(self.tags_config.keys()), self)
        
        if dialog.exec():
            category = dialog.category
            text = dialog.text
            if not text:
                InfoBar.warning(title='提示', content="标签文本不能为空", parent=self)
                return
            
            tags = self.tags_config[category].get('tags', [])
            
            # 检查重复
            if any(t['text'] == text for t in tags):
                InfoBar.warning(title='提示', content="该标签已存在", parent=self)
                return
            
            tags.append({"text": text, "icon": None})
            self.tags_config[category]['tags'] = tags
            
            self.__save_config()
            self.__refresh_all_tags()
            
            InfoBar.success(title='成功', content=f"已添加标签: {text}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_tag_edited(self, old_text, _):
        """编辑标签"""
        # 找到标签所属的分类
        category = None
        for cat_name, cat_data in self.tags_config.items():
            if any(t['text'] == old_text for t in cat_data.get('tags', [])):
                category = cat_name
                break
        
        if not category:
            return
        
        dialog = EditTagDialog(old_text, self)
        
        if dialog.exec():
            new_text = dialog.text
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
            self.__refresh_all_tags()
            
            InfoBar.success(title='成功', content=f"已更新标签: {new_text}", parent=self)
            self.tagsUpdated.emit()
    
    def __on_tag_deleted(self, tag_text):
        """删除标签"""
        # 找到标签所属的分类
        category = None
        for cat_name, cat_data in self.tags_config.items():
            if any(t['text'] == tag_text for t in cat_data.get('tags', [])):
                category = cat_name
                break
        
        if not category:
            return
        
        tags = self.tags_config[category].get('tags', [])
        self.tags_config[category]['tags'] = [t for t in tags if t['text'] != tag_text]
        
        self.__save_config()
        self.__refresh_all_tags()
        
        InfoBar.success(title='成功', content=f"已删除标签: {tag_text}", parent=self)
        self.tagsUpdated.emit()
    
    def __on_search(self, text):
        """搜索标签"""
        self.__refresh_all_tags(text)
    
    def get_tags_config(self):
        """获取标签配置（供合成界面使用）"""
        return self.tags_config
