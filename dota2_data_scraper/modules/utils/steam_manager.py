"""
Модуль для работы с Steam директориями
"""

import os
import json
import shutil
import logging
import winreg
import win32api
import win32com.client
from datetime import datetime
from typing import List, Optional


logger = logging.getLogger(__name__)


class SteamManager:
    """Класс для работы с Steam директориями и копирования конфигураций"""

    def __init__(self):
        self.steam_path = None
        self.config_dirs = []

    def find_steam_path(self) -> Optional[str]:
        """
        Поиск пути к Steam

        Returns:
            Путь к Steam или None если не найден
        """
        try:
            logger.info("Поиск Steam директории...")

            # Метод 1: Через ярлык в Start Menu
            path1 = f"{os.getenv('APPDATA')}\\Microsoft\\Windows\\Start Menu\\Programs\\Steam\\Steam.lnk"
            if os.path.exists(path1):
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(path1)
                steam_path = os.path.dirname(shortcut.Targetpath)
                if os.path.exists(steam_path):
                    logger.info(f"Steam найден через ярлык: {steam_path}")
                    return steam_path

            # Метод 2: Через реестр (WOW6432Node)
            try:
                key = winreg.OpenKeyEx(
                    winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Valve\Steam"
                )
                install_path = winreg.QueryValueEx(key, "InstallPath")[0]
                winreg.CloseKey(key)
                if os.path.exists(install_path):
                    logger.info(f"Steam найден через реестр (WOW64): {install_path}")
                    return install_path
            except Exception:
                pass

            # Метод 3: Через реестр (обычный)
            try:
                key = winreg.OpenKeyEx(
                    winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"
                )
                install_path = winreg.QueryValueEx(key, "InstallPath")[0]
                winreg.CloseKey(key)
                if os.path.exists(install_path):
                    logger.info(f"Steam найден через реестр: {install_path}")
                    return install_path
            except Exception:
                pass

            # Метод 4: Поиск по стандартным путям
            possible_paths = [
                r"Steam\steam.exe",
                r"Program Files\Steam\steam.exe",
                r"Program Files (x86)\Steam\steam.exe",
            ]

            for drive in win32api.GetLogicalDriveStrings().split("\000")[:-1]:
                drive = drive.replace(":\\", "")
                for path in possible_paths:
                    full_path = f"{drive}:\\{path}"
                    if os.path.exists(full_path):
                        steam_path = os.path.dirname(full_path)
                        logger.info(f"Steam найден по стандартному пути: {steam_path}")
                        return steam_path

            logger.warning("Steam директория не найдена")
            return None

        except Exception as e:
            logger.error(f"Ошибка при поиске Steam: {e}")
            return None

    def find_config_dirs(self, steam_path: str) -> List[str]:
        """
        Поиск директорий с конфигурациями Dota 2

        Args:
            steam_path: Путь к Steam

        Returns:
            Список путей к директориям конфигураций
        """
        try:
            logger.info("Поиск директорий конфигураций Dota 2...")

            userdata_dir = os.path.join(steam_path, "userdata")
            if not os.path.exists(userdata_dir):
                logger.warning(f"Директория userdata не найдена: {userdata_dir}")
                return []

            config_dirs = []

            # Проходим по всем пользователям
            for user_id in os.listdir(userdata_dir):
                config_path = os.path.join(
                    userdata_dir, user_id, "570", "remote", "cfg"
                )
                if os.path.isdir(config_path):
                    config_dirs.append(config_path)
                    logger.info(f"Найдена директория конфигурации: {config_path}")

            if not config_dirs:
                logger.warning("Директории конфигураций Dota 2 не найдены")

            return config_dirs

        except Exception as e:
            logger.error(f"Ошибка при поиске директорий конфигураций: {e}")
            return []

    def backup_existing_config(self, config_dir: str):
        """
        Создание резервной копии существующей конфигурации

        Args:
            config_dir: Директория с конфигурацией
        """
        try:
            config_file = os.path.join(config_dir, "hero_grid_config.json")
            if not os.path.exists(config_file):
                return

            # Создаем папку для резервных копий
            old_grid_dir = os.path.join(config_dir, "old_grid")
            os.makedirs(old_grid_dir, exist_ok=True)

            # Создаем имя файла с датой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(
                old_grid_dir, f"hero_grid_config_{timestamp}.json"
            )

            # Копируем файл
            shutil.copy2(config_file, backup_file)
            logger.info(f"Создана резервная копия: {backup_file}")

        except Exception as e:
            logger.warning(f"Не удалось создать резервную копию в {config_dir}: {e}")

    def copy_config_to_steam(self, config_file_path: str) -> bool:
        """
        Копирование конфигурации в Steam директории

        Args:
            config_file_path: Путь к файлу конфигурации

        Returns:
            True если успешно скопировано
        """
        try:
            logger.info("Начало копирования конфигурации в Steam...")

            if not os.path.exists(config_file_path):
                logger.error(f"Файл конфигурации не найден: {config_file_path}")
                return False

            # Ищем Steam
            self.steam_path = self.find_steam_path()
            if not self.steam_path:
                logger.error("Steam не найден, пропускаем копирование")
                return False

            # Ищем директории конфигураций
            self.config_dirs = self.find_config_dirs(self.steam_path)
            if not self.config_dirs:
                logger.error("Директории конфигураций Dota 2 не найдены")
                return False

            # Копируем в каждую директорию
            success_count = 0
            for config_dir in self.config_dirs:
                try:
                    # Создаем резервную копию
                    self.backup_existing_config(config_dir)

                    # Копируем новую конфигурацию
                    target_file = os.path.join(config_dir, "hero_grid_config.json")
                    shutil.copy2(config_file_path, target_file)
                    success_count += 1
                    logger.info(f"Конфигурация скопирована в: {config_dir}")

                except Exception as e:
                    logger.warning(f"Не удалось скопировать в {config_dir}: {e}")

            if success_count > 0:
                logger.info(
                    f"✅ Конфигурация скопирована в {success_count} директорий Steam"
                )
                return True
            else:
                logger.error(
                    "❌ Не удалось скопировать конфигурацию ни в одну директорию"
                )
                return False

        except Exception as e:
            logger.error(f"Ошибка при копировании конфигурации: {e}")
            return False
