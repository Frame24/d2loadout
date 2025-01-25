import getpass
import os
import sys
import time
from win32com.client import Dispatch

def add_to_startup():
    """
    Добавляет ярлык текущего исполняемого файла в автозагрузку Windows.
    """
    USER_NAME = getpass.getuser()
    bat_path = rf'C:\Users\{USER_NAME}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\{os.path.basename(sys.executable)}.lnk'
    target = sys.executable

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(bat_path)
    shortcut.Targetpath = target
    shortcut.save()
    print("Программа добавлена в автозагрузку!")

    for remaining in range(2, 0, -1):
        time.sleep(1)
