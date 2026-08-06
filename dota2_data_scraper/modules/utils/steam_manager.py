"""
Модуль для работы с Steam директориями
"""

import os
import json
import shutil
import logging
import string
import winreg
from datetime import datetime
from typing import List, Optional


logger = logging.getLogger(__name__)


def _registry_install_path(key_path: str) -> Optional[str]:
    """Читает InstallPath Steam из HKLM без pywin32."""
    try:
        key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path)
        try:
            install_path = winreg.QueryValueEx(key, "InstallPath")[0]
        finally:
            winreg.CloseKey(key)
        if install_path and os.path.isdir(install_path):
            return install_path
    except OSError:
        pass
    return None


def _iter_drive_roots():
    """Корни существующих дисков (C:\\, D:\\, ...)."""
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            yield root


class SteamManager:
    """Класс для работы с Steam директориями и копирования конфигураций"""

    def __init__(self):
        self.steam_path = None
        self.config_dirs = []

    @staticmethod
    def _extract_userdata_id(config_dir: str) -> Optional[str]:
        """
        Пытается извлечь Steam userdata id из пути вида:
          <steam_path>\\userdata\\<id>\\570\\remote\\cfg
        """
        try:
            norm = os.path.normpath(config_dir)
            parts = norm.split(os.sep)
            # Ищем сегмент "userdata" и берем следующий как id
            for i, p in enumerate(parts):
                if p.lower() == "userdata" and i + 1 < len(parts):
                    candidate = parts[i + 1]
                    return candidate if candidate else None
        except Exception:
            return None
        return None

    @staticmethod
    def _project_export_dir() -> str:
        # Дублируем в папку проекта, рядом с configs/
        return os.path.join("configs", "steam_exports")

    def _export_to_project(
        self,
        *,
        source_config_file_path: str,
        config_dir: str,
        steam_target_file: str,
    ) -> None:
        """
        Дублирует конфиг в папку проекта для диагностики.

        Пишем две копии:
        - latest: configs/steam_exports/<userdata>/hero_grid_config.json
        - snapshot: configs/steam_exports/<userdata>/old_grid/hero_grid_config_<timestamp>.json
        """
        try:
            userdata_id = self._extract_userdata_id(config_dir) or "unknown_userdata"
            export_root = os.path.join(self._project_export_dir(), userdata_id)
            os.makedirs(export_root, exist_ok=True)

            # latest
            latest_path = os.path.join(export_root, "hero_grid_config.json")
            shutil.copy2(source_config_file_path, latest_path)

            # snapshot
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_old = os.path.join(export_root, "old_grid")
            os.makedirs(export_old, exist_ok=True)
            snapshot_path = os.path.join(export_old, f"hero_grid_config_{ts}.json")
            shutil.copy2(source_config_file_path, snapshot_path)

            # диагностический файл: что и куда копировали
            meta_path = os.path.join(export_root, "last_copy.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp": ts,
                        "source_config_file_path": os.path.abspath(source_config_file_path),
                        "steam_target_file": os.path.abspath(steam_target_file),
                        "steam_config_dir": os.path.abspath(config_dir),
                        "userdata_id": userdata_id,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            logger.info(
                "Экспорт в проект: %s (latest) + %s (snapshot)",
                latest_path,
                snapshot_path,
            )
        except Exception as e:
            logger.warning("Не удалось экспортировать конфиг в проект: %s", e)

    def find_steam_path(self) -> Optional[str]:
        """
        Поиск пути к Steam (stdlib only: winreg + обход дисков).

        Returns:
            Путь к Steam или None если не найден
        """
        try:
            logger.info("Поиск Steam директории...")

            for key_path, label in (
                (r"SOFTWARE\Wow6432Node\Valve\Steam", "реестр WOW64"),
                (r"SOFTWARE\Valve\Steam", "реестр"),
            ):
                install_path = _registry_install_path(key_path)
                if install_path:
                    logger.info(f"Steam найден через {label}: {install_path}")
                    return install_path

            # Типичные пути без перебора всех дисков
            env_candidates = [
                os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Steam"),
                os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Steam"),
                r"C:\Steam",
                r"D:\Steam",
            ]
            for steam_path in env_candidates:
                if os.path.isfile(os.path.join(steam_path, "steam.exe")):
                    logger.info(f"Steam найден по стандартному пути: {steam_path}")
                    return steam_path

            relative_exe = [
                os.path.join("Steam", "steam.exe"),
                os.path.join("Program Files", "Steam", "steam.exe"),
                os.path.join("Program Files (x86)", "Steam", "steam.exe"),
            ]
            for root in _iter_drive_roots():
                for rel in relative_exe:
                    full_exe = os.path.join(root, rel)
                    if os.path.isfile(full_exe):
                        steam_path = os.path.dirname(full_exe)
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

                    # Дублируем для диагностики в папку проекта
                    self._export_to_project(
                        source_config_file_path=config_file_path,
                        config_dir=config_dir,
                        steam_target_file=target_file,
                    )

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
