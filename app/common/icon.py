# coding:utf-8
from enum import Enum
from qfluentwidgets import getIconColor, Theme


class Icon(Enum):
    """ Custom icons """

    HOME = "Home"
    SYNTHESIS = "Music"
    LOGS = "Chat"
    SETTINGS = "Settings"
    INFO = "Info"

    def path(self, theme=Theme.AUTO):
        """ Get icon path """
        return f':/icons/images/icons/{self.value}_{getIconColor(theme)}.svg'
