"""
资源路径工具 - 适配开发环境与 PyInstaller 打包环境
"""
import sys
from pathlib import Path


def get_resource_path():
    """
    获取项目根目录路径
    - 开发环境：基于 __file__ 计算
    - PyInstaller 打包环境：基于 sys.executable 所在目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包环境
        base_dir = Path(sys.executable).parent
    else:
        # 开发环境
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
    
    return base_dir
