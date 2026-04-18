# coding:utf-8
"""
全局音频管理器
统一管理所有界面的音频播放，实现音量同步和播放互斥
"""
from PyQt5.QtCore import QObject
from PyQt5.QtMultimedia import QMediaPlayer


class GlobalAudioManager(QObject):
    """全局音频管理器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__initialized = False
        return cls._instance
    
    def __init__(self):
        if self.__initialized:
            return
        super().__init__()
        self.__initialized = True
        
        # 注册的所有播放器实例
        self.players = []
        
        # 当前正在播放的播放器
        self.current_player = None
        
        # 从配置文件加载音量和静音状态
        from app.common.config import cfg
        self.global_volume = cfg.get(cfg.globalVolume)
        self.global_muted = cfg.get(cfg.globalMuted)
        
        # 从信号总线导入
        from app.common.signal_bus import signalBus
        self.signalBus = signalBus
        
        # 连接全局信号
        self.signalBus.audioPlayRequested.connect(self._on_play_requested)
        self.signalBus.volumeChanged.connect(self._on_volume_changed)
        self.signalBus.mutedChanged.connect(self._on_muted_changed)
    
    def register_player(self, playBar):
        """注册播放器到全局管理器"""
        if playBar not in self.players:
            self.players.append(playBar)
            
            # 设置初始音量和静音状态
            playBar.player.setVolume(self.global_volume)
            playBar.player.setMuted(self.global_muted)
            
            # 监听播放器的音量和静音变化
            playBar.volumeButton.volumeChanged.connect(
                lambda vol, pb=playBar: self._on_local_volume_changed(pb, vol)
            )
            playBar.volumeButton.mutedChanged.connect(
                lambda muted, pb=playBar: self._on_local_muted_changed(pb, muted)
            )
            
            # 补充 qfluentwidgets 缺失的 stateChanged 信号监听
            # 确保其他播放器暂停时，按钮图标能正确更新
            playBar.player.stateChanged.connect(
                lambda state, pb=playBar: pb.playButton.setPlay(state == QMediaPlayer.PlayingState)
            )
            
            # 包装底层 player.play() 方法，拦截所有播放请求
            # 这能确保 togglePlayState、直接调用 playBar.play() 都能触发互斥
            original_player_play = playBar.player.play
            def wrapped_player_play():
                # 发送播放请求，暂停其他播放器
                self.signalBus.audioPlayRequested.emit(playBar)
                original_player_play()
            playBar.player.play = wrapped_player_play
    
    def _on_play_requested(self, requesting_player):
        """处理播放请求 - 暂停其他播放器"""
        for player in self.players:
            if player != requesting_player and player.player.isPlaying():
                player.pause()
    
    def _on_local_volume_changed(self, playBar, volume):
        """本地音量变化时同步到全局"""
        # 避免循环触发
        if volume != self.global_volume:
            self.global_volume = volume
            # 保存到配置文件
            from app.common.config import cfg
            cfg.set(cfg.globalVolume, volume)
            # 同步到其他播放器
            for player in self.players:
                if player != playBar:
                    player.player.setVolume(volume)
    
    def _on_local_muted_changed(self, playBar, muted):
        """本地静音变化时同步到全局"""
        # 避免循环触发
        if muted != self.global_muted:
            self.global_muted = muted
            # 保存到配置文件
            from app.common.config import cfg
            cfg.set(cfg.globalMuted, muted)
            # 同步到其他播放器
            for player in self.players:
                if player != playBar:
                    player.player.setMuted(muted)
    
    def _on_volume_changed(self, volume):
        """全局音量变化信号处理"""
        self.global_volume = volume
        # 保存到配置文件
        from app.common.config import cfg
        cfg.set(cfg.globalVolume, volume)
        for player in self.players:
            player.player.setVolume(volume)
    
    def _on_muted_changed(self, muted):
        """全局静音变化信号处理"""
        self.global_muted = muted
        # 保存到配置文件
        from app.common.config import cfg
        cfg.set(cfg.globalMuted, muted)
        for player in self.players:
            player.player.setMuted(muted)
    
    def set_global_volume(self, volume):
        """设置全局音量"""
        self.global_volume = volume
        # 保存到配置文件
        from app.common.config import cfg
        cfg.set(cfg.globalVolume, volume)
        self.signalBus.volumeChanged.emit(volume)
    
    def set_global_muted(self, muted):
        """设置全局静音"""
        self.global_muted = muted
        # 保存到配置文件
        from app.common.config import cfg
        cfg.set(cfg.globalMuted, muted)
        self.signalBus.mutedChanged.emit(muted)
    
    def stop_all(self):
        """停止所有播放器"""
        for player in self.players:
            player.stop()
        self.current_player = None
    
    def pause_all(self):
        """暂停所有播放器"""
        for player in self.players:
            if player.player.isPlaying():
                player.pause()


# 创建全局实例
audioManager = GlobalAudioManager()
