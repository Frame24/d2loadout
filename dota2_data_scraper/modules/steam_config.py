import os
import winreg
import win32api
import win32com.client
import json
from datetime import datetime

def read_reg(ep, p=r"", k=''):
    """
    Чтение значения из реестра Windows.
    """
    try:
        key = winreg.OpenKeyEx(ep, p)
        value, _ = winreg.QueryValueEx(key, k)
        winreg.CloseKey(key)
        return value
    except Exception:
        return None

def find_steam_path():
    """
    Поиск установки Steam через ярлык и реестр.
    """
    path1 = "{}\\Microsoft\\Windows\\Start Menu\\Programs\\Steam\\Steam.lnk".format(os.getenv('APPDATA'))
    
    if os.path.exists(path1):
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(path1)
        path1_res = shortcut.Targetpath
    else:
        path1_res = None

    path2 = str(read_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Valve\Steam", 'InstallPath')) + r"\steam.exe"
    path3 = str(read_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", 'InstallPath')) + r"\steam.exe"

    # Проверка существования путей
    if not os.path.exists(path2):
        path2 = None
    if not os.path.exists(path3):
        path3 = None

    possible_paths = [
        r"X:\Steam\steam.exe",
        r"X:\Program Files\Steam\steam.exe",
        r"X:\Program Files (x86)\Steam\steam.exe"
    ]

    valid_paths = []

    for drive in win32api.GetLogicalDriveStrings().split('\000')[:-1]:
        for path in possible_paths:
            full_path = path.replace("X", drive.replace(':\\', ''))
            if os.path.exists(full_path):
                valid_paths.append(full_path)

    return valid_paths[0] if valid_paths else None

def get_dota_config_dirs():
    """
    Получает пути к конфигурационным файлам Dota 2.
    """
    steam_dir = find_steam_path()
    if not steam_dir:
        return []

    steam_dir = os.path.join(os.path.dirname(steam_dir), "userdata")
    
    dirs_to_check = [
        os.path.join(steam_dir, id, "570", "remote", "cfg")
        for id in os.listdir(steam_dir)
    ]
    
    return [dir for dir in dirs_to_check if os.path.isdir(dir)]

def backup_and_save_config(config):
    """
    Архивирует старый конфиг и сохраняет новый в папке Dota 2.
    """
    cfg_dirs = get_dota_config_dirs()

    for dir in cfg_dirs:
        old_grid_dir = os.path.join(dir, "old_grid")
        os.makedirs(old_grid_dir, exist_ok=True)

        current_config_path = os.path.join(dir, "hero_grid_config.json")

        if os.path.exists(current_config_path):
            timestamp = datetime.now().strftime("%Y%m%d")
            old_config_path = os.path.join(old_grid_dir, f"hero_grid_config_{timestamp}.json")

            if os.path.exists(old_config_path):
                os.remove(old_config_path)

            os.rename(current_config_path, old_config_path)

        with open(current_config_path, "w") as f:
            json.dump(config, f)

    print("Конфигурации Dota 2 обновлены.")
