import PyInstaller.__main__
import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 图标文件路径
icon_path = os.path.join(current_dir, 'icon.ico')

def build_gui():
    """打包GUI版本"""
    print("正在打包GUI版本...")
    PyInstaller.__main__.run([
        '.\\北大法宝图书馆自动爬虫GUI.py',
        '--name=北大法宝爬虫_GUI版',
        '--onefile',
        '--windowed',  # 窗口模式，不显示控制台
        f'--icon={icon_path}',
        '--clean',
        '--noconfirm',
    ])
    print("GUI版本打包完成！")

def build_terminal():
    """打包终端版本"""
    print("正在打包终端版本...")
    PyInstaller.__main__.run([
        '.\\北大法宝图书馆自动爬虫_终端版.py',
        '--name=北大法宝爬虫_终端版',
        '--onefile',
        # 不添加 --windowed，保留控制台
        f'--icon={icon_path}',
        '--clean',
        '--noconfirm',
    ])
    print("终端版本打包完成！")

def build_auto():
    """打包一键运行版本"""
    print("正在打包一键运行版本...")
    PyInstaller.__main__.run([
        '.\\run_auto.py',
        '--name=北大法宝爬虫_一键运行',
        '--onefile',
        f'--icon={icon_path}',
        '--clean',
        '--noconfirm',
    ])
    print("一键运行版本打包完成！")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'gui':
            build_gui()
        elif sys.argv[1] == 'terminal':
            build_terminal()
        elif sys.argv[1] == 'auto':
            build_auto()
        elif sys.argv[1] == 'all':
            build_terminal()
            build_auto()
            build_gui()
    else:
        # 默认打包终端版
        build_terminal()
    
    print("\n所有打包任务完成！")
    print("生成的EXE文件在 dist 文件夹中")
