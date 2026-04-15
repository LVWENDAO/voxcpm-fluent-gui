# coding:utf-8
from PyQt5.QtCore import Qt, QUrl, QObject, QEvent, QProcess, QTimer, QFileSystemWatcher
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, 
                             QLabel, QSizePolicy, QToolTip, QGridLayout)
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import (ScrollArea, CardWidget, TitleLabel, CaptionLabel, 
                            TextEdit, PlainTextEdit, Slider, SwitchButton, PrimaryPushButton, PushButton,
                            FluentIcon as FIF, InfoBar, InfoBarPosition, TransparentToolButton,
                            BodyLabel, StrongBodyLabel, ProgressRing, ToolTipFilter,
                            IndeterminateProgressBar, isDarkTheme, qconfig, PillPushButton, LineEdit, ComboBox)
from qfluentwidgets.multimedia import StandardMediaPlayBar

from app.common.style_sheet import StyleSheet




class PerformanceMonitorCard(CardWidget):
    """性能监视器卡片 - 图形化展示版"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = StrongBodyLabel("性能监视器")
        
        # 监控项容器
        monitorsLayout = QHBoxLayout()
        monitorsLayout.setSpacing(20)

        # 1. GPU 监控
        self.gpuRing = ProgressRing()
        self.gpuRing.setFixedSize(60, 60)
        self.gpuRing.setTextVisible(True)
        self.gpuInfo = CaptionLabel("GPU: --%")
        gpuLayout = QVBoxLayout()
        gpuLayout.setAlignment(Qt.AlignCenter)
        gpuLayout.addWidget(self.gpuRing, 0, Qt.AlignHCenter)
        gpuLayout.addWidget(self.gpuInfo, 0, Qt.AlignHCenter)
        monitorsLayout.addLayout(gpuLayout)
        monitorsLayout.addStretch(1) # 均分空间

        # 2. 显存监控
        self.vramRing = ProgressRing()
        self.vramRing.setFixedSize(60, 60)
        self.vramRing.setTextVisible(False)
        self.vramInfo = CaptionLabel("显存: -- / -- GB")
        vramLayout = QVBoxLayout()
        vramLayout.setAlignment(Qt.AlignCenter)
        vramLayout.addWidget(self.vramRing, 0, Qt.AlignHCenter)
        vramLayout.addWidget(self.vramInfo, 0, Qt.AlignHCenter)
        monitorsLayout.addLayout(vramLayout)
        monitorsLayout.addStretch(1) # 均分空间

        # 3. 内存监控
        self.ramRing = ProgressRing()
        self.ramRing.setFixedSize(60, 60)
        self.ramRing.setTextVisible(False)
        self.ramInfo = CaptionLabel("内存: -- / -- GB")
        ramLayout = QVBoxLayout()
        ramLayout.setAlignment(Qt.AlignCenter)
        ramLayout.addWidget(self.ramRing, 0, Qt.AlignHCenter)
        ramLayout.addWidget(self.ramInfo, 0, Qt.AlignHCenter)
        monitorsLayout.addLayout(ramLayout)
        monitorsLayout.addStretch(1) # 均分空间

        layout.addWidget(title)
        layout.addLayout(monitorsLayout)

        # 模拟数据更新
        from PyQt5.QtCore import QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.__update_stats)
        self.timer.start(2000)

    def __update_stats(self):
        """更新真实性能监控数据"""
        try:
            import psutil
            # 1. 内存监控
            mem = psutil.virtual_memory()
            ram_used = mem.used / (1024**3)
            ram_total = mem.total / (1024**3)
            self.ramRing.setValue(int(mem.percent))
            self.ramInfo.setText(f"内存: {ram_used:.1f} / {ram_total:.1f} GB")

            # 2. GPU 监控 (NVIDIA)
            try:
                import pynvml as nvml
                nvml.nvmlInit()
                handle = nvml.nvmlDeviceGetHandleByIndex(0)
                
                # 显存
                info = nvml.nvmlDeviceGetMemoryInfo(handle)
                vram_used = info.used / (1024**3)
                vram_total = info.total / (1024**3)
                self.vramRing.setValue(int((vram_used / vram_total) * 100))
                self.vramInfo.setText(f"显存: {vram_used:.1f} / {vram_total:.1f} GB")
                
                # GPU 利用率
                gpu_util = nvml.nvmlDeviceGetUtilizationRates(handle).gpu
                self.gpuRing.setValue(gpu_util)
                self.gpuInfo.setText(f"GPU: {gpu_util}%")
                
                nvml.nvmlShutdown()
            except Exception:
                self.gpuInfo.setText("GPU: N/A")
                self.vramInfo.setText("显存: N/A")
        except ImportError:
            self.ramInfo.setText("请安装 psutil")


class ServerLogCard(CardWidget):
    """服务器运行日志卡片"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        headerLayout = QHBoxLayout()
        title = StrongBodyLabel("服务器日志")
        self.clearBtn = TransparentToolButton(FIF.DELETE)
        self.clearBtn.setFixedSize(32, 32)
        self.clearBtn.clicked.connect(self.clear_logs)
        headerLayout.addWidget(title)
        headerLayout.addStretch()
        headerLayout.addWidget(self.clearBtn)

        self.logArea = TextEdit()  # 使用TextEdit而不是PlainTextEdit，因为需要append方法
        self.logArea.setReadOnly(True)
        self.logArea.setMaximumHeight(200)
        # 移除硬编码样式，使用 qfluentwidgets 默认样式以适配主题

        layout.addLayout(headerLayout)
        layout.addWidget(self.logArea)

    def append_log(self, text):
        self.logArea.append(text.strip())
        # 自动滚动到底部
        scrollbar = self.logArea.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        self.logArea.clear()


class SynthesisInterface(ScrollArea):
    """ Synthesis interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget()
        self.mainLayout = QHBoxLayout(self.view)

        # 初始化文件系统监听器（监听音色库变化）
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.__onVoiceDirectoryChanged)
        
        self.__initWidget()
        self.__initLayout()
        
        # 监听音色注册信号，实现跨页面同步
        from app.common.signal_bus import signalBus
        signalBus.voiceRegistered.connect(self.__onLoadVoices)
        
        # 启动时加载音色并开始监听
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        voice_cache_dir = base_dir / "voice_cache"  # 修正路径，与音色库界面保持一致
        voice_cache_dir.mkdir(parents=True, exist_ok=True)
        self.watcher.addPath(str(voice_cache_dir))
        QTimer.singleShot(500, self.__onLoadVoices)

    def __initWidget(self):
        self.view.setObjectName('view')
        self.setObjectName('synthesisInterface')
        
        # 强制透明背景以适配主题
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.viewport().setStyleSheet("background-color: transparent;")
        self.view.setStyleSheet("background-color: transparent;")
        
        # 初始化网络管理器与服务器地址
        self.network_manager = QNetworkAccessManager(self)
        self.server_url = "http://127.0.0.1:8000"
        
        StyleSheet.SYNTHESIS_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

    def __initLayout(self):
        self.mainLayout.setContentsMargins(16, 16, 16, 16)
        self.mainLayout.setSpacing(16)

        # --- 左列：系统状态与参数 (50%) ---
        leftWidget = QWidget()
        leftLayout = QVBoxLayout(leftWidget)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(12)
        leftWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 1. 服务器控制卡 (置顶)
        self.serverCard = CardWidget()
        serverLayout = QVBoxLayout(self.serverCard)
        serverLayout.setContentsMargins(16, 12, 16, 12) # 减小内边距
        serverLayout.setSpacing(8)

        serverHeader = QHBoxLayout()
        # 服务器状态标签
        statusLabel = CaptionLabel("服务器状态：")
        self.statusIndicator = QLabel("● 离线")
        self.statusIndicator.setStyleSheet("color: #808080; font-size: 14px;")
        self.startServerBtn = PushButton(FIF.PLAY, "启动服务")
        self.startServerBtn.setFixedWidth(140)
        self.startServerBtn.clicked.connect(self.__toggle_server)
        serverHeader.addWidget(statusLabel)
        serverHeader.addWidget(self.statusIndicator)
        serverHeader.addStretch()
        serverHeader.addWidget(self.startServerBtn)

        # 添加服务器启动进度条（初始隐藏）
        self.serverProgressBar = IndeterminateProgressBar(self)
        self.serverProgressBar.setFixedHeight(3)
        self.serverProgressBar.setVisible(False)

        self.serverLogCard = ServerLogCard()
        # 优化日志卡片内部间距
        self.serverLogCard.layout().setContentsMargins(16, 8, 16, 8)
        self.serverLogCard.logArea.setMaximumHeight(120) # 限制高度

        serverLayout.addLayout(serverHeader)
        serverLayout.addWidget(self.serverProgressBar)
        serverLayout.addWidget(self.serverLogCard)

        # 初始化 QProcess
        self.serverProcess = QProcess(self)
        self.serverProcess.readyReadStandardOutput.connect(self.__on_server_output)
        self.serverProcess.readyReadStandardError.connect(self.__on_server_output)
        self.serverProcess.finished.connect(self.__on_server_finished)

        # 2. 参考音频卡
        refCard = CardWidget()
        refLayout = QVBoxLayout(refCard)
        refLayout.setContentsMargins(16, 12, 16, 12)
        refLayout.setSpacing(8)
        
        refTitle = StrongBodyLabel("参考音频（可选）")
        
        # 上传按钮和清空按钮的水平布局
        uploadLayout = QHBoxLayout()
        self.uploadBtn = PushButton(FIF.FOLDER_ADD, "上传参考音频")
        self.uploadBtn.setToolTip("上传参考音频以实现声音克隆，支持 WAV/MP3/FLAC 格式")
        self.uploadBtn.installEventFilter(ToolTipFilter(self.uploadBtn))
        self.uploadBtn.clicked.connect(self.__onUploadRef)
        
        # 清空按钮（始终显示）
        self.clearAudioBtn = TransparentToolButton(FIF.DELETE)
        self.clearAudioBtn.setFixedSize(32, 32)
        self.clearAudioBtn.setToolTip("清空当前选择的音频文件（需确认）")
        self.clearAudioBtn.installEventFilter(ToolTipFilter(self.clearAudioBtn))
        self.clearAudioBtn.clicked.connect(self.__onClearAudio)
        
        uploadLayout.addWidget(self.uploadBtn, 1)  # 1表示扩展填充
        uploadLayout.addWidget(self.clearAudioBtn)
        uploadLayout.addStretch()
        
        ultimateLayout = QHBoxLayout()
        self.ultimateSwitch = SwitchButton()
        self.ultimateSwitch.setOnText("开启")
        self.ultimateSwitch.setOffText("关闭")
        self.ultimateSwitch.setToolTip("开启后将使用参考音频的完整声学特征进行极致还原，需填写 ASR 文本")
        self.ultimateSwitch.installEventFilter(ToolTipFilter(self.ultimateSwitch))
        self.ultimateSwitch.checkedChanged.connect(self.__onUltimateModeChanged)
        ultimateLabel = CaptionLabel("极致克隆模式")
        ultimateLayout.addWidget(self.ultimateSwitch)
        ultimateLayout.addWidget(ultimateLabel)
        ultimateLayout.addStretch(1)
        
        refLayout.addWidget(refTitle)
        refLayout.addLayout(uploadLayout)
        
        # ASR 文本输入框 (始终显示)
        self.asrInput = PlainTextEdit()
        self.asrInput.setPlaceholderText("参考音频对应的文本内容（用于声音克隆）...")
        self.asrInput.setMaximumHeight(60)
        refLayout.addWidget(self.asrInput)

        refLayout.addLayout(ultimateLayout)

        # 3. 控制指令卡 (高度自适应)
        promptCard = CardWidget()
        promptLayout = QVBoxLayout(promptCard)
        promptLayout.setContentsMargins(16, 12, 16, 12)
        promptLayout.setSpacing(8)
        
        promptTitle = StrongBodyLabel("控制指令（可选）")
        self.promptInput = PlainTextEdit()
        self.promptInput.setPlaceholderText("如：年轻女性，温柔甜美 / A warm young woman")
        self.promptInput.setMaximumHeight(60)  # 限制为最多两行文本高度
        self.promptInput.setToolTip("通过文字描述生成目标音色，无需参考音频")
        self.promptInput.installEventFilter(ToolTipFilter(self.promptInput))
        
        # 增加禁用态提示支持：通过临时替换文本实现
        self.promptOriginalText = ""
        # 添加选中的标签集合
        self.selected_tags = set()
        
        promptLayout.addWidget(promptTitle)
        promptLayout.addWidget(self.promptInput)
        
        # 添加快捷标签按钮组 - 使用网格布局 (3x3)
        tagsLayout = QGridLayout()
        tagsLayout.setSpacing(8)
        
        # 基础音色标签
        self.tagYoungFemale = PillPushButton("年轻女性，温柔甜美")
        self.tagMatureMale = PillPushButton("成熟男性，沉稳有力") 
        self.tagChildVoice = PillPushButton("儿童声音，活泼可爱")
        
        # 情感风格标签
        self.tagCheerful = PillPushButton("更欢快、语速稍快")
        self.tagSerious = PillPushButton("严肃认真，语速适中")
        self.tagGentle = PillPushButton("温柔舒缓，轻声细语")
        
        # 方言特色标签
        self.tagNortheast = PillPushButton("东北话")
        self.tagSichuan = PillPushButton("四川话")
        
        # 连接按钮点击事件 - 添加/移除文本模式
        self.tagYoungFemale.clicked.connect(lambda: self.__toggle_prompt_text("年轻女性，温柔甜美"))
        self.tagMatureMale.clicked.connect(lambda: self.__toggle_prompt_text("成熟男性，沉稳有力"))
        self.tagChildVoice.clicked.connect(lambda: self.__toggle_prompt_text("儿童声音，活泼可爱"))
        self.tagCheerful.clicked.connect(lambda: self.__toggle_prompt_text("更欢快、语速稍快"))
        self.tagSerious.clicked.connect(lambda: self.__toggle_prompt_text("严肃认真，语速适中"))
        self.tagGentle.clicked.connect(lambda: self.__toggle_prompt_text("温柔舒缓，轻声细语"))
        self.tagNortheast.clicked.connect(lambda: self.__toggle_prompt_text("东北话"))
        self.tagSichuan.clicked.connect(lambda: self.__toggle_prompt_text("四川话"))
        
        # 添加标签到网格布局 (3列布局)
        tagsLayout.addWidget(self.tagYoungFemale, 0, 0)
        tagsLayout.addWidget(self.tagMatureMale, 0, 1)
        tagsLayout.addWidget(self.tagChildVoice, 0, 2)
        tagsLayout.addWidget(self.tagCheerful, 1, 0)
        tagsLayout.addWidget(self.tagSerious, 1, 1)
        tagsLayout.addWidget(self.tagGentle, 1, 2)
        tagsLayout.addWidget(self.tagNortheast, 2, 0)
        tagsLayout.addWidget(self.tagSichuan, 2, 1)
        # 第2行第2列留空以保持平衡
        
        promptLayout.addLayout(tagsLayout)

        # 3. 音色管理卡
        voiceCard = CardWidget()
        voiceLayout = QVBoxLayout(voiceCard)
        voiceLayout.setContentsMargins(16, 12, 16, 12)
        voiceLayout.setSpacing(8)
        
        voiceTitle = StrongBodyLabel("音色库")
        
        # 注册区域
        regLayout = QHBoxLayout()
        self.voiceNameInput = LineEdit()
        self.voiceNameInput.setPlaceholderText("输入音色名称")
        self.registerVoiceBtn = PushButton(FIF.SAVE, "注册")
        self.registerVoiceBtn.clicked.connect(self.__onRegisterVoice)
        regLayout.addWidget(self.voiceNameInput)
        regLayout.addWidget(self.registerVoiceBtn)
        
        # 选择区域（下拉即生效）
        self.voiceComboBox = ComboBox()
        self.voiceComboBox.setPlaceholderText("不使用音色缓存（传统推理）")
        self.voiceComboBox.currentIndexChanged.connect(self.__onVoiceChanged)
        
        voiceLayout.addWidget(voiceTitle)
        voiceLayout.addLayout(regLayout)
        voiceLayout.addWidget(self.voiceComboBox)

        leftLayout.addWidget(self.serverCard)
        leftLayout.addWidget(refCard)
        leftLayout.addWidget(promptCard)
        leftLayout.addWidget(voiceCard)
        leftLayout.addStretch(1) # 仅保留底部弹性空间

        # --- 右列：目标文本 + 结果展示区 (50%) ---
        rightWidget = QWidget()
        rightLayout = QVBoxLayout(rightWidget)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.setSpacing(12)
        rightWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 1. 目标文本卡
        textCard = CardWidget()
        textLayout = QVBoxLayout(textCard)
        textLayout.setContentsMargins(16, 12, 16, 12)
        textLayout.setSpacing(8)
        
        textTitle = StrongBodyLabel("目标文本")
        self.textInput = PlainTextEdit()  # 使用PlainTextEdit来过滤粘贴格式
        self.textInput.setPlaceholderText("请输入要合成的内容...")
        # 设置文本输入框的最小高度，使其与服务器卡片的日志区域高度匹配
        self.textInput.setMinimumHeight(120)
        
        textLayout.addWidget(textTitle)
        textLayout.addWidget(self.textInput)

        # 2. 高级设置卡 (移至生成按钮上方)
        advCard = CardWidget()
        advLayout = QVBoxLayout(advCard)
        advLayout.setContentsMargins(16, 12, 16, 12)
        advLayout.setSpacing(12)
        
        advTitle = StrongBodyLabel("高级设置")
        
        # CFG 和步数设置 - 水平布局
        cfgStepsLayout = QHBoxLayout()
        cfgStepsLayout.setSpacing(16)
        
        # CFG 设置
        cfgGroup = QWidget()
        cfgLayout = QVBoxLayout(cfgGroup)
        cfgLayout.setContentsMargins(0, 0, 0, 0)
        cfgLayout.setSpacing(4)
        self.cfgLabel = CaptionLabel("CFG（引导强度）: 2.0")
        self.cfgSlider = Slider(Qt.Horizontal)
        self.cfgSlider.setRange(5, 50)
        self.cfgSlider.setValue(20)
        self.cfgSlider.setToolTip("值越高越遵循控制指令，但可能影响自然度（推荐 1.5-3.0）")
        self.cfgSlider.installEventFilter(ToolTipFilter(self.cfgSlider))
        self.cfgSlider.valueChanged.connect(lambda v: self.cfgLabel.setText(f"CFG（引导强度）: {v/10:.1f}"))
        cfgLayout.addWidget(self.cfgLabel)
        cfgLayout.addWidget(self.cfgSlider)
        
        # 步数设置
        stepsGroup = QWidget()
        stepsLayout = QVBoxLayout(stepsGroup)
        stepsLayout.setContentsMargins(0, 0, 0, 0)
        stepsLayout.setSpacing(4)
        self.stepsLabel = CaptionLabel("推理步数: 10")
        self.stepsSlider = Slider(Qt.Horizontal)
        self.stepsSlider.setRange(5, 30)
        self.stepsSlider.setValue(10)
        self.stepsSlider.setToolTip("步数越多质量越高，但速度越慢（推荐 10-15）")
        self.stepsSlider.installEventFilter(ToolTipFilter(self.stepsSlider))
        self.stepsSlider.valueChanged.connect(lambda v: self.stepsLabel.setText(f"推理步数: {v}"))
        stepsLayout.addWidget(self.stepsLabel)
        stepsLayout.addWidget(self.stepsSlider)
        
        cfgStepsLayout.addWidget(cfgGroup, 1)
        cfgStepsLayout.addWidget(stepsGroup, 1)
        
        # 开关设置 - 水平布局
        switchesLayout = QHBoxLayout()
        switchesLayout.setSpacing(24)
        
        # 音频降噪开关
        denoiseLayout = QHBoxLayout()
        denoiseLayout.setSpacing(8)
        self.denoiseSwitch = SwitchButton()
        self.denoiseSwitch.setOnText("开启")
        self.denoiseSwitch.setOffText("关闭")
        self.denoiseSwitch.setChecked(False)  # 默认关闭
        self.denoiseSwitch.setToolTip("开启音频降噪以提高参考音频质量")
        self.denoiseSwitch.installEventFilter(ToolTipFilter(self.denoiseSwitch))
        denoiseLabel = CaptionLabel("音频降噪")
        denoiseLayout.addWidget(self.denoiseSwitch)
        denoiseLayout.addWidget(denoiseLabel)
        denoiseLayout.addStretch()
        
        # 文本正规范化开关
        normalizeLayout = QHBoxLayout()
        normalizeLayout.setSpacing(8)
        self.normalizeSwitch = SwitchButton()
        self.normalizeSwitch.setOnText("开启")
        self.normalizeSwitch.setOffText("关闭")
        self.normalizeSwitch.setChecked(True)  # 默认开启
        self.normalizeSwitch.setToolTip("开启文本正规范化以标准化输入文本格式")
        self.normalizeSwitch.installEventFilter(ToolTipFilter(self.normalizeSwitch))
        normalizeLabel = CaptionLabel("文本正规范化")
        normalizeLayout.addWidget(self.normalizeSwitch)
        normalizeLayout.addWidget(normalizeLabel)
        normalizeLayout.addStretch()
        
        switchesLayout.addLayout(denoiseLayout)
        switchesLayout.addLayout(normalizeLayout)
        switchesLayout.addStretch()
        
        # 随机种子设置
        seedLayout = QHBoxLayout()
        seedLayout.setSpacing(8)
        self.seedInput = LineEdit()
        self.seedInput.setPlaceholderText("留空则随机")
        self.seedInput.setFixedWidth(120)
        self.seedInput.setToolTip("固定种子可保证音色绝对一致，留空则每次随机")
        self.seedInput.installEventFilter(ToolTipFilter(self.seedInput))
        
        seedLayout.addWidget(CaptionLabel("随机种子:"))
        seedLayout.addWidget(self.seedInput)
        seedLayout.addStretch()
        
        advLayout.addWidget(advTitle)
        advLayout.addLayout(cfgStepsLayout)
        advLayout.addLayout(switchesLayout)
        advLayout.addLayout(seedLayout)

        # 3. 生成按钮
        self.generateBtn = PrimaryPushButton(FIF.PLAY, "开始生成")
        self.generateBtn.setMinimumHeight(40)
        self.generateBtn.setToolTip("开始语音合成")
        self.generateBtn.installEventFilter(ToolTipFilter(self.generateBtn))
        self.generateBtn.clicked.connect(self.__onGenerateClicked)

        # 添加推理进度条（初始隐藏）
        self.inferenceProgressBar = IndeterminateProgressBar(self)
        self.inferenceProgressBar.setFixedHeight(3)
        self.inferenceProgressBar.setVisible(False)

        # 4. 底部标准播放控制栏
        self.playBar = StandardMediaPlayBar(self)

        # 5. 性能监视器
        self.perfCard = PerformanceMonitorCard()

        rightLayout.addWidget(textCard)
        rightLayout.addWidget(advCard)
        rightLayout.addWidget(self.generateBtn)
        rightLayout.addWidget(self.inferenceProgressBar)  # 添加推理进度条
        rightLayout.addWidget(self.playBar)
        rightLayout.addWidget(self.perfCard)
        rightLayout.addStretch(1)

        self.mainLayout.addWidget(leftWidget, 1)
        self.mainLayout.addWidget(rightWidget, 1)

    def __onUploadRef(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择参考音频", "", "Audio Files (*.wav *.mp3 *.flac)")
        if path:
            self.ref_audio_path = path  # 保存参考音频路径
            self.uploadBtn.setText(f"已选择: {os.path.basename(path)}")
            self.uploadBtn.setIcon(FIF.ACCEPT)

        # 初始化网络管理器用于 HTTP 通信
        self.network_manager = QNetworkAccessManager(self)
        self.server_url = "http://127.0.0.1:8000"

    def __onClearAudio(self):
        """清空当前选择的音频文件（容错处理）"""
        if not hasattr(self, 'ref_audio_path') or not self.ref_audio_path:
            return  # 未选择音频时静默返回，不报错
        
        self.ref_audio_path = None
        self.uploadBtn.setText("上传参考音频")
        self.uploadBtn.setIcon(FIF.FOLDER_ADD)

    def __onGenerateClicked(self):
        text = self.textInput.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title='提示', 
                content="请先输入目标文本", 
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        # 获取控制指令（仅在非极致克隆模式下使用）
        control_prompt = ""
        if not self.ultimateSwitch.isChecked():
            control_prompt = self.promptInput.toPlainText().strip()
        
        # 构建最终文本（模仿官方CLI的做法：用括号包裹控制指令）
        if control_prompt:
            final_text = f"({control_prompt}){text}"
        else:
            final_text = text
        
        # 检查服务器状态
        if self.serverProcess.state() == QProcess.NotRunning:
            InfoBar.warning(
                title='提示', 
                content="服务器未启动，请先启动推理服务器", 
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        # 显示进度条
        self.inferenceProgressBar.setVisible(True)
        self.inferenceProgressBar.start()
        
        self.generateBtn.setEnabled(False)
        self.generateBtn.setText("推理中...")
        self.generateBtn.setToolTip("推理任务正在进行，请耐心等待完成")
        
        # 确定输出目录 - 始终使用 VoxCPM2 根目录下的 outputs 文件夹
        import sys
        import os
        from pathlib import Path
        
        if getattr(sys, 'frozen', False):
            # 如果是打包的exe文件，使用exe所在目录
            voxcpm2_root = Path(sys.executable).parent
        else:
            # 如果是源代码运行，向上查找直到找到 VoxCPM2 根目录
            current_dir = Path(__file__).resolve()
            # 从 synthesis_interface.py 向上查找: view -> app -> voxcpm-fluent-gui -> VoxCPM2
            voxcpm2_root = current_dir.parent.parent.parent.parent
        
        output_dir = str(voxcpm2_root / "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        # 构造请求数据
        seed_val = None
        if self.seedInput.text().strip().isdigit():
            seed_val = int(self.seedInput.text().strip())
        
        # 获取选中的 voice_id，如果是第一个选项（None）则不传
        voice_id = None
        current_index = self.voiceComboBox.currentIndex()
        if current_index > 0:  # 索引 0 是“不使用音色缓存”
            voice_id = self.voiceComboBox.itemData(current_index)

        payload = {
            "text": final_text,
            "reference_wav_path": getattr(self, 'ref_audio_path', None),
            "prompt_wav_path": getattr(self, 'ref_audio_path', None) if self.ultimateSwitch.isChecked() else None,
            "prompt_text": self.asrInput.toPlainText().strip() if self.ultimateSwitch.isChecked() else None,
            "cfg_value": self.cfgSlider.value() / 10.0,
            "inference_timesteps": self.stepsSlider.value(),
            "output_dir": output_dir,
            "denoise_enabled": self.denoiseSwitch.isChecked(),
            "normalize_text": self.normalizeSwitch.isChecked(),
            "seed": seed_val,
            "voice_id": voice_id
        }

        request = QNetworkRequest(QUrl(f"{self.server_url}/generate"))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        reply = self.network_manager.post(request, json.dumps(payload).encode())
        reply.finished.connect(lambda: self.__on_inference_finished(reply))

    def __on_inference_finished(self, reply):
        # 隐藏进度条
        self.inferenceProgressBar.stop()
        self.inferenceProgressBar.setVisible(False)
        
        self.generateBtn.setEnabled(True)
        self.generateBtn.setText("开始生成")
        self.generateBtn.setToolTip("开始语音合成，请确保已填写目标文本")
        
        if reply.error() == QNetworkReply.NoError:
            data = json.loads(reply.readAll().data())
            # 兼容两种响应格式
            if data.get("success") or data.get("status") == "success":
                audio_path = data.get('audio_path')
                history_id = data.get('history_id')  # 获取历史ID
                
                # 保存最近一次的 history_id 供首页注册使用
                self.last_history_id = history_id
                
                # 触发信号通知历史界面完整重载
                from app.common.signal_bus import signalBus
                signalBus.historyGenerated.emit()
                
                if audio_path and os.path.exists(audio_path):
                    # 使用标准播放栏加载并播放音频
                    from PyQt5.QtCore import QUrl
                    from PyQt5.QtMultimedia import QMediaContent
                    self.playBar.player.setSource(QMediaContent(QUrl.fromLocalFile(audio_path)))
                    self.playBar.play()
                    
                    # 创建自定义的成功提示
                    info_bar = InfoBar.success(
                        title='成功', 
                        content=f"音频已生成: {os.path.basename(audio_path)}", 
                        parent=self,
                        position=InfoBarPosition.BOTTOM,
                        duration=10000
                    )
                    
                    # 添加另存为按钮
                    save_as_btn = PushButton("另存为")
                    def on_save_as():
                        save_path, _ = QFileDialog.getSaveFileName(
                            self, "另存为", 
                            os.path.basename(audio_path), 
                            "Audio Files (*.wav *.mp3 *.flac)"
                        )
                        if save_path:
                            import shutil
                            shutil.copy2(audio_path, save_path)
                            InfoBar.success(title='成功', content="文件已保存", parent=self, duration=2000)
                    save_as_btn.clicked.connect(on_save_as)
                    info_bar.addWidget(save_as_btn)
                else:
                    InfoBar.warning(
                        title='警告', 
                        content="音频文件未找到或路径无效", 
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=3000
                    )
            else:
                error_msg = data.get('error') or data.get('detail', '未知错误')
                InfoBar.error(
                    title='错误', 
                    content=error_msg, 
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=-1
                )
        else:
            InfoBar.error(
                title='网络错误', 
                content="无法连接到推理服务器，请检查服务是否启动。", 
                parent=self,
                position=InfoBarPosition.TOP,
                duration=-1
            )
        
        reply.deleteLater()

    def __onRegisterVoice(self):
        """首页一键注册：直接拷贝最近一次生成的缓存"""
        name = self.voiceNameInput.text().strip()
        if not name:
            InfoBar.warning(title='提示', content="请输入音色名称", parent=self)
            return
        
        if not hasattr(self, 'last_history_id') or not self.last_history_id:
            InfoBar.warning(title='提示', content="请先进行一次语音合成", parent=self)
            return

        try:
            import shutil, hashlib, time
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            history_folder = base_dir / "outputs" / "generation_history" / self.last_history_id
            
            # 读取历史元数据
            meta_file = history_folder / "meta.json"
            if not meta_file.exists():
                InfoBar.error(title='错误', content="元数据文件缺失", parent=self)
                return
                
            with open(meta_file, 'r', encoding='utf-8') as f:
                history_meta = json.load(f)
            
            # 生成 ID 并复制完整文件
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
            
            # 构建并保存音色元数据
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
            
            # 标记历史为已注册并记录 voice_id
            history_meta['registered'] = True
            history_meta['registered_voice_id'] = voice_id
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(history_meta, f)
            
            InfoBar.success(title='成功', content=f"已注册至音色库: {name}", parent=self)
            self.voiceNameInput.clear()
            self.__onLoadVoices()
            
            # 触发信号通知历史界面完整重载
            from app.common.signal_bus import signalBus
            signalBus.historyGenerated.emit()
        except Exception as e:
            InfoBar.error(title='错误', content=str(e), parent=self)

    def __onVoiceChanged(self, index):
        """切换音色时自动加载参数并回填"""
        try:
            if index == 0:
                # 切换到无缓存模式：清空种子，启用控制指令
                self.seedInput.clear()
                self.promptInput.setEnabled(True)
                self.promptInput.setPlaceholderText("如：年轻女性，温柔甜美 / A warm young woman")
                InfoBar.info(title='提示', content="已切换至传统推理模式（不使用音色缓存）", parent=self)
                return
            
            # 选择音色后：禁用控制指令输入
            self.promptInput.setEnabled(False)
            self.promptInput.setPlaceholderText("使用音色库时不可使用控制指令")
            self.promptInput.clear()  # 清空已输入的控制指令
            
            voice_id = self.voiceComboBox.itemData(index)
            if not voice_id:
                return
            
            # 读取音色完整元数据
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            db_path = base_dir / "voice_cache" / "voices_db.json"  # 独立于 outputs
            
            if db_path.exists():
                with open(db_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                
                if voice_id in db:
                    voice_data = db[voice_id]
                    
                    # 回填 seed
                    seed = voice_data.get('config', {}).get('seed', '')
                    self.seedInput.setText(str(seed) if seed else '')
                    
                    # 回填 inference_timesteps 和 cfg_value
                    inference_timesteps = voice_data.get('config', {}).get('inference_timesteps', 32)
                    cfg_value = voice_data.get('config', {}).get('cfg_value', 4.0)
                    
                    if hasattr(self, 'inferenceTimestepsSpin'):
                        self.inferenceTimestepsSpin.setValue(inference_timesteps)
                    if hasattr(self, 'cfgValueSpin'):
                        self.cfgValueSpin.setValue(cfg_value)
                    
                    InfoBar.success(
                        title='已加载音色参数',
                        content=f"Seed: {seed} | Steps: {inference_timesteps} | CFG: {cfg_value}",
                        parent=self
                    )
        except Exception as e:
            print(f"[Voice Changed] Error: {e}")

    def __onVoiceDirectoryChanged(self, path):
        """当音色库文件夹变化时自动刷新下拉列表"""
        QTimer.singleShot(200, self.__onLoadVoices)

    def __onLoadVoices(self):
        """从本地文件系统加载音色列表（前端直读）"""
        try:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            voice_cache_dir = base_dir / "voice_cache"  # 独立于 outputs
            db_path = voice_cache_dir / "voices_db.json"
            
            if not hasattr(self, 'voiceComboBox') or not self.voiceComboBox:
                return

            # 1. 记录当前选中的音色 ID
            current_voice_id = self.voiceComboBox.currentData()
            
            # 2. 屏蔽信号，防止刷新过程触发 __onVoiceChanged
            self.voiceComboBox.blockSignals(True)
            self.voiceComboBox.clear()
            self.voiceComboBox.addItem("不使用音色缓存", userData=None)
            
            # 3. 加载新列表
            if db_path.exists():
                with open(db_path, 'r', encoding='utf-8') as f:
                    voices = json.load(f)
                for vid, vdata in voices.items():
                    self.voiceComboBox.addItem(vdata['name'], userData=vid)
            
            # 4. 恢复选中状态（如果该 ID 仍存在于列表中）
            if current_voice_id:
                index = self.voiceComboBox.findData(current_voice_id)
                if index != -1:
                    self.voiceComboBox.setCurrentIndex(index)
                
            # 5. 恢复信号
            self.voiceComboBox.blockSignals(False)
            
        except Exception as e:
            print(f"[Voice Load] Error: {e}")


    def __onUltimateModeChanged(self, checked):
        if checked:
            # 保存原文本和选中状态
            self.promptOriginalText = self.promptInput.toPlainText()
            # 从原文本重建选中状态（用于手动输入的情况）
            if self.promptOriginalText and self.promptOriginalText != "极致克隆模式下不可使用控制指令":
                # 如果有手动输入的文本，保持原样，不清空选中状态
                pass
            self.promptInput.setPlainText("极致克隆模式下不可使用控制指令")
            self.promptInput.setEnabled(False)
            
            # 极致模式下，ASR 文本框变为必填项视觉提示（可选）
            self.asrInput.setPlaceholderText("参考音频对应的文本内容（极致克隆必填）...")
        else:
            # 恢复原文本
            self.promptInput.setPlainText(self.promptOriginalText)
            self.promptInput.setEnabled(True)
            
            # 如果恢复的是通过标签设置的文本，重建选中状态
            if self.promptOriginalText and self.promptOriginalText != "极致克隆模式下不可使用控制指令":
                # 尝试从文本重建选中状态（仅当文本是由标签生成的）
                possible_tags = {
                    "年轻女性，温柔甜美", "成熟男性，沉稳有力", "儿童声音，活泼可爱",
                    "更欢快、语速稍快", "严肃认真，语速适中", "温柔舒缓，轻声细语",
                    "东北话", "四川话"
                }
                current_fragments = [frag.strip() for frag in self.promptOriginalText.split('，') if frag.strip()]
                self.selected_tags = set()
                for frag in current_fragments:
                    if frag in possible_tags:
                        self.selected_tags.add(frag)
            
            # 恢复普通模式提示
            self.asrInput.setPlaceholderText("参考音频对应的文本内容（用于声音克隆）...")

    def __toggle_prompt_text(self, text):
        """切换控制指令文本（添加或移除指定文本片段）"""
        target_text = text.strip()
        
        # 切换选中状态
        if target_text in self.selected_tags:
            self.selected_tags.remove(target_text)
        else:
            self.selected_tags.add(target_text)
        
        # 重新组合文本
        if self.selected_tags:
            new_text = '，'.join(sorted(self.selected_tags))  # 排序以保持一致性
        else:
            new_text = ''
        
        self.promptInput.setPlainText(new_text)

    def __toggle_server(self):
        if self.serverProcess.state() == QProcess.NotRunning:
            # 显示进度条
            self.serverProgressBar.setVisible(True)
            self.serverProgressBar.start()
            
            # 禁用生成按钮（防止在服务器启动过程中发送请求）
            self.generateBtn.setEnabled(False)
            self.generateBtn.setToolTip("服务器启动中，请等待...")
            
            self.startServerBtn.setEnabled(False)
            self.startServerBtn.setText("启动中...")
            self.serverLogCard.append_log("[系统] 正在初始化推理服务器...")
            
            # 检查并清理占用8000端口的残留进程
            self.__cleanup_port_8000()
            
            # 定位 voxcpm2_env 环境下的 Python 解释器和 inference_server.py
            import os, sys
            
            # 1. 确定 Python 解释器路径 (优先使用 voxcpm2_env)
            env_python = os.path.join(os.path.dirname(__file__), "..", "..", "..", "voxcpm2_env", "python.exe")
            if not os.path.exists(env_python):
                env_python = "h:/VoxCPM2/voxcpm2_env/python.exe"
            
            # 2. 确定脚本路径
            script_path = os.path.join(os.path.dirname(__file__), "..", "..", "inference_server.py")
            if not os.path.exists(script_path):
                script_path = "h:/VoxCPM2/voxcpm-fluent-gui/inference_server.py"

            if not os.path.exists(env_python) or not os.path.exists(script_path):
                self.serverLogCard.append_log("[错误] 找不到 voxcpm2_env 或 inference_server.py，请检查路径。")
                self.serverProgressBar.stop()
                self.serverProgressBar.setVisible(False)
                self.startServerBtn.setEnabled(True)
                self.startServerBtn.setText("启动服务")
                return

            self.serverLogCard.append_log(f"[系统] 使用环境: {env_python}")
            # 启动进程
            self.serverProcess.start(env_python, [script_path])
        else:
            # 隐藏进度条
            self.serverProgressBar.stop()
            self.serverProgressBar.setVisible(False)
            
            self.serverProcess.terminate()
            self.serverLogCard.append_log("[系统] 正在请求停止服务器...")
            self.startServerBtn.setEnabled(False)
            self.startServerBtn.setText("停止中...")

    def __cleanup_port_8000(self):
        """优雅地清理占用8000端口的残留VoxCPM2进程"""
        try:
            import subprocess
            import os
            
            # 获取占用8000端口的进程ID
            result = subprocess.run(
                ['netstat', '-ano'], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                return
                
            lines = result.stdout.split('\n')
            target_pid = None
            
            for line in lines:
                if ':8000' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        target_pid = parts[4]
                        break
            
            if not target_pid or not target_pid.isdigit():
                return
                
            pid = int(target_pid)
            
            # 第一层：精准匹配 - 检查是否是VoxCPM2相关的python进程
            is_voxcpm2_process = False
            process_name = ""
            
            try:
                # 获取进程详细信息
                process_info = subprocess.run(
                    ['tasklist', '/fi', f'PID eq {pid}', '/fo', 'CSV', '/nh'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if process_info.returncode == 0 and process_info.stdout.strip():
                    info_parts = process_info.stdout.strip().strip('"').split('","')
                    if len(info_parts) >= 1:
                        process_name = info_parts[0].lower()
                        
                    # 检查进程路径
                    path_result = subprocess.run(
                        ['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'ExecutablePath', '/value'],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    if path_result.returncode == 0:
                        # 解析WMIC输出 (格式: ExecutablePath=C:\path\to\exe)
                        for line in path_result.stdout.split('\n'):
                            if line.strip().startswith('ExecutablePath='):
                                exe_path = line.strip().split('=', 1)[1]
                                if exe_path and ('voxcpm2_env' in exe_path.lower() or 'voxcpm' in exe_path.lower()):
                                    is_voxcpm2_process = True
                                    break
                    
                    # 如果路径匹配失败，但确定是python进程且占用大量内存（>1GB），也认为是VoxCPM2进程
                    if not is_voxcpm2_process and 'python' in process_name:
                        if len(info_parts) >= 5:
                            try:
                                memory_kb = int(info_parts[4].replace(',', ''))
                                if memory_kb > 1024 * 1024:  # > 1GB
                                    is_voxcpm2_process = True
                            except ValueError:
                                pass
            
            except Exception as e:
                self.serverLogCard.append_log(f"[系统] 获取进程详细信息时发生错误: {str(e)}")
            
            # 执行清理
            if is_voxcpm2_process:
                try:
                    subprocess.run(
                        ['taskkill', '/pid', str(pid), '/f'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self.serverLogCard.append_log(f"[系统] 已清理VoxCPM2残留进程 PID: {pid}")
                    
                    # 弹出成功提醒
                    InfoBar.success(
                        title='清理完成',
                        content=f'已自动清理占用端口8000的残留进程 (PID: {pid})',
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=2000
                    )
                    
                except Exception as e:
                    error_msg = f"[系统] 清理进程 {pid} 失败: {str(e)}"
                    self.serverLogCard.append_log(error_msg)
                    
                    # 弹出错误提醒
                    InfoBar.error(
                        title='清理失败',
                        content='无法自动清理残留进程，请手动关闭相关程序',
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=3000
                    )
            else:
                # 不是VoxCPM2进程，但端口被占用
                warning_msg = f"[系统] 端口8000被其他进程占用 (PID: {pid}, 名称: {process_name})"
                self.serverLogCard.append_log(warning_msg)
                
                # 弹出警告提醒
                InfoBar.warning(
                    title='端口冲突',
                    content='端口8000已被其他程序占用，请关闭相关程序后重试',
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=4000
                )
                    
        except Exception as e:
            error_msg = f"[系统] 检测端口占用时发生错误: {str(e)}"
            self.serverLogCard.append_log(error_msg)
            
            InfoBar.error(
                title='检测失败',
                content='无法检测端口占用状态',
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )

    def __on_server_output(self):
        try:
            # 读取所有可用输出
            text = self.serverProcess.readAllStandardOutput().data().decode('utf-8', errors='ignore')
            error_text = self.serverProcess.readAllStandardError().data().decode('utf-8', errors='ignore')
            
            full_log = text + error_text
            if full_log:
                # 逐行处理日志
                for line in full_log.splitlines():
                    if line.strip():
                        self.serverLogCard.append_log(line)
                        
                        # 状态识别逻辑 (对齐原始 GUI 的启动成功标志)
                        if "Uvicorn running on" in line or "Application startup complete" in line:
                            # 隐藏进度条
                            self.serverProgressBar.stop()
                            self.serverProgressBar.setVisible(False)
                            
                            self.statusIndicator.setText("● 在线")
                            self.statusIndicator.setStyleSheet("color: #107C10; font-size: 14px;")
                            self.startServerBtn.setText("停止服务")
                            self.startServerBtn.setIcon(FIF.CANCEL)
                            self.startServerBtn.setEnabled(True)
                            self.serverLogCard.append_log("[系统] 服务器已就绪，可以开始合成。")
                            
                            # 弹出主题色成功提醒（顶部，自动消失）
                            InfoBar.success(
                                title='服务器启动成功',
                                content="推理服务器已就绪，可以开始语音合成",
                                parent=self,
                                position=InfoBarPosition.TOP,
                                duration=3000
                            )
                            
                            # 启用生成按钮
                            self.generateBtn.setEnabled(True)
                            self.generateBtn.setToolTip("开始语音合成，请确保已填写目标文本")
        except Exception as e:
            self.serverLogCard.append_log(f"[错误] 日志读取异常: {str(e)}")

    def __on_server_finished(self, code):
        # 隐藏进度条
        self.serverProgressBar.stop()
        self.serverProgressBar.setVisible(False)
        
        self.statusIndicator.setText("● 离线")
        self.statusIndicator.setStyleSheet("color: #808080; font-size: 14px;")
        self.startServerBtn.setText("启动服务")
        self.startServerBtn.setIcon(FIF.PLAY)
        self.startServerBtn.setEnabled(True)
        self.serverLogCard.append_log(f"[系统] 服务器进程已退出 (Code: {code})")
        
        # 禁用生成按钮
        self.generateBtn.setEnabled(False)
        self.generateBtn.setToolTip("请先启动推理服务器")
