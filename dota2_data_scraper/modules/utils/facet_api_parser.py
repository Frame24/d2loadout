"""
Парсер фасетов героев из Dotabuff (repo-*.js) + сопоставление hero_id→имя через D2PT
"""

import logging
import re
import os
import requests
from typing import Dict, List, Optional, Tuple

from ..core.scraping_manager import ScrapingManager
from bs4 import BeautifulSoup
import json
from urllib.parse import quote


class FacetAPIParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.hero_facets_cache: Dict[str, Dict[str, int]] = {}

    def get_hero_facets_mapping(
        self, debug_dotabuff: bool = False, manager=None, headless: bool = True
    ) -> Dict[str, Dict[str, int]]:
        # Всегда используем только Dotabuff
        self.logger.info("Получение фасетов через Dotabuff...")
        try:
            mapping = self._try_dotabuff_facets(manager, headless=headless)
            if mapping:
                self.logger.info(
                    f"✅ Получены фасеты через Dotabuff для {len(mapping)} героев"
                )
                self.hero_facets_cache = mapping
                return mapping
            else:
                raise RuntimeError("Dotabuff не вернул данные")
        except Exception as e:
            self.logger.error(f"Ошибка при получении фасетов через Dotabuff: {e}")
            raise

    def _discover_dotabuff_repo_js_http(self) -> str:
        # Пробуем сначала страницу героя (более надежно)
        hero_urls = [
            "https://www.dotabuff.com/heroes/juggernaut",
            "https://www.dotabuff.com/heroes/anti-mage", 
            "https://www.dotabuff.com/heroes/pudge"
        ]

        for hero_url in hero_urls:
            try:
                html = self._fetch_url(hero_url, referer="https://www.dotabuff.com/")
                repo_url = self._extract_repo_js_url_from_html(html)
                if repo_url:
                    return repo_url
            except Exception as e:
                self.logger.debug(f"Не удалось получить repo с {hero_url}: {e}")
                continue

        # Фолбек на главную
        root_url = "https://www.dotabuff.com/"
        html = self._fetch_url(root_url, referer="https://www.dotabuff.com/")
        return self._extract_repo_js_url_from_html(html)

    def _extract_repo_js_url_from_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if src.startswith("/static/repo-") and src.endswith(".js"):
                return f"https://www.dotabuff.com{src}"

        # Более широкая регулярка для поиска repo-*.js
        patterns = [
            r'<script[^>]+src=["\'](/static/repo-[^"\']+\.js)["\']',
            r'src=["\'](/static/repo-[^"\']+\.js)["\']',
            r'"/static/repo-[^"]+\.js"',
            r"'/static/repo-[^']+\.js'",
            r'/static/repo-[a-zA-Z0-9_-]+\.js'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match.startswith('/static/repo-') and match.endswith('.js'):
                    return f"https://www.dotabuff.com{match}"

        raise RuntimeError("Не удалось найти ссылку на repo-*.js на главной Dotabuff")

    def _fetch_repo_js_via_selenium(self) -> Tuple[str, str]:
        with ScrapingManager(headless=True) as manager:
            # 1) идем на страницу героя (более надежно)
            hero_urls = [
                "https://www.dotabuff.com/heroes/juggernaut",
                "https://www.dotabuff.com/heroes/anti-mage",
                "https://www.dotabuff.com/heroes/pudge"
            ]

            repo_js_url = None
            for hero_url in hero_urls:
                try:
                    self.logger.debug(f"Переходим на {hero_url}")
                    manager.navigate_to_page_basic(hero_url)

                    # Ждем загрузки всех ресурсов
                    import time
                    time.sleep(3)

                    # 2) Получаем ВСЕ загруженные ресурсы и ищем repo файлы
                    try:
                        # Все ресурсы
                        all_resources = manager.driver.execute_script("""
                            return performance.getEntriesByType('resource')
                                .map(r => r.name)
                                .filter(name => name.includes('/static/') && name.endsWith('.js'));
                        """)

                        self.logger.debug(f"Найдено {len(all_resources)} JS файлов в /static/")
                        for resource in all_resources:
                            self.logger.debug(f"  - {resource}")

                        # Ищем repo файлы
                        repo_resources = [r for r in all_resources if '/static/repo-' in r]
                        if repo_resources:
                            repo_js_url = repo_resources[0]
                            self.logger.debug(f"Найден repo через Performance API: {repo_js_url}")
                            break
                    except Exception as e:
                        self.logger.debug(f"Performance API не сработал: {e}")

                    # 3) Альтернативно - через список скриптов
                    try:
                        scripts = manager.driver.execute_script(
                            "return Array.from(document.scripts).map(s=>s.src).filter(Boolean);"
                        )
                        self.logger.debug(f"Найдено {len(scripts)} скриптов")
                        for s in scripts:
                            self.logger.debug(f"  - {s}")
                            if "/static/repo-" in s and s.endswith(".js"):
                                repo_js_url = s if s.startswith("http") else f"https://www.dotabuff.com{s}"
                                self.logger.debug(f"Найден repo через scripts: {repo_js_url}")
                                break
                        if repo_js_url:
                            break
                    except Exception as e:
                        self.logger.debug(f"Scripts API не сработал: {e}")

                    # 4) Пробуем найти в HTML страницы
                    try:
                        page_source = manager.get_page_source()
                        import re
                        repo_matches = re.findall(r'/static/repo-[^"\']+\.js', page_source)
                        if repo_matches:
                            repo_js_url = f"https://www.dotabuff.com{repo_matches[0]}"
                            self.logger.debug(f"Найден repo в HTML: {repo_js_url}")
                            break
                    except Exception as e:
                        self.logger.debug(f"HTML поиск не сработал: {e}")

                except Exception as e:
                    self.logger.debug(f"Ошибка на {hero_url}: {e}")
                    continue

            if not repo_js_url:
                raise RuntimeError("Не удалось найти repo-*.js через Selenium")

            # 4) Загружаем содержимое repo файла
            self.logger.debug(f"Загружаем содержимое {repo_js_url}")
            manager.navigate_to_page_basic(repo_js_url)

            try:
                js_text = manager.driver.execute_script(
                    "return document.body.innerText || document.body.textContent || '';"
                )
            except Exception:
                js_text = manager.get_page_source()

            self.logger.debug(f"Получено {len(js_text)} символов из repo файла")
            return repo_js_url, js_text

    def _fetch_url(
        self, url: str, referer: Optional[str] = None, timeout: int = 15
    ) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            "Accept": "text/html,application/json,application/javascript,*/*;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        if referer:
            headers["Referer"] = referer
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    def _extract_facets_from_repo(self, js_text: str) -> List[dict]:
        # Более гибкие паттерны для поиска JSON с фасетами
        patterns = [
            r"const\s+f\s*=\s*JSON\.parse\(`(\[.*?\])`\)",
            r"JSON\.parse\(`(\[.*?\])`\)",
            r"const\s+\w+\s*=\s*(\[.*?\])",
            r"facets?\s*:\s*(\[.*?\])",
            r"f\s*=\s*(\[.*?\])"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, js_text, re.DOTALL)
            for match in matches:
                try:
                    import json
                    facets = json.loads(match)
                    if isinstance(facets, list) and len(facets) > 0:
                        valid = [x for x in facets if not x.get("deprecated")]
                        if valid:
                            self.logger.debug(f"Найдено {len(valid)} фасетов через паттерн: {pattern[:50]}...")
                            return valid
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.debug(f"Ошибка парсинга JSON для паттерна {pattern[:30]}: {e}")
                    continue

        self.logger.warning("Не удалось найти валидные фасеты в JS")
        return []

    def _build_mapping(
        self, facets: List[dict], hero_id_to_name: Dict[int, str]
    ) -> Dict[str, Dict[str, int]]:
        # Группируем по hero_id, сортируем по hero_variant и id, нумеруем 1..n
        by_hero: Dict[int, List[dict]] = {}
        for f in facets:
            hid = f.get("hero_id")
            if not isinstance(hid, int):
                continue
            by_hero.setdefault(hid, []).append(f)
        result: Dict[str, Dict[str, int]] = {}
        for hid, lst in by_hero.items():
            lst.sort(key=lambda x: (x.get("hero_variant", 9999), x.get("id", 999999)))
            hero_name = hero_id_to_name.get(hid)
            if not hero_name:
                # Фолбек по слагу героя (anti-mage-1-..., до первой -<цифра>-)
                hero_name = (
                    self._name_from_slug(lst[0].get("slug", "")) or f"Hero {hid}"
                )
            name_to_order: Dict[str, int] = {}
            order = 1
            for fac in lst:
                name = fac.get("name")
                if not isinstance(name, str) or not name.strip():
                    # последний фолбек — короткий алиас из description
                    alias = self._alias_from_description(fac.get("description"))
                    name = alias or f"Facet {order}"
                if name not in name_to_order:
                    name_to_order[name] = order
                    order += 1
            result[hero_name] = name_to_order
        return result

    def _name_from_slug(self, slug: str) -> Optional[str]:
        # slug вида: "anti-mage-1-magebanes-mirror" → hero part: "anti-mage"
        m = re.match(r"^([a-z0-9-]+)-\d+-", slug or "")
        hero_slug = m.group(1) if m else None
        if not hero_slug:
            return None
        # Примитивная нормализация: дефисы → пробелы, титл-кейс, специальные случаи
        special = {
            "natures-prophet": "Nature's Prophet",
            "queens-of-pain": "Queen of Pain",
            "anti-mage": "Anti-Mage",
            "wraith-king": "Wraith King",
        }
        if hero_slug in special:
            return special[hero_slug]
        parts = hero_slug.split("-")
        return " ".join(w.capitalize() for w in parts)

    def _alias_from_description(self, desc: Optional[str]) -> Optional[str]:
        if not isinstance(desc, str):
            return None
        s = desc.strip()
        s = re.sub(r"[\[\](){}%0-9]+", " ", s)
        s = re.sub(r"[,:.;!?]", " ", s)
        words = [w for w in s.split() if len(w) > 2]
        stop = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "into",
            "over",
            "your",
            "you",
            "when",
            "that",
            "this",
            "upon",
            "more",
            "less",
            "per",
            "each",
            "every",
            "also",
            "are",
            "can",
            "will",
            "have",
            "has",
            "while",
            "based",
            "than",
            "time",
            "area",
            "deal",
            "deals",
            "damage",
            "bonus",
            "attack",
            "attacks",
            "spell",
            "spells",
            "enemy",
            "enemies",
            "allies",
            "units",
            "hero",
            "heroes",
            "applies",
            "grants",
            "increases",
            "reduced",
            "targets",
            "nearby",
            "around",
            "gains",
            "gain",
            "casts",
            "casting",
        }
        picked: List[str] = []
        for w in words:
            lw = w.lower()
            if lw in stop:
                continue
            picked.append(w.capitalize())
            if len(picked) >= 3:
                break
        return " ".join(picked) if picked else None

    def _try_parse_js_object(self, js_obj_text: str) -> Optional[dict]:
        """Пытается распарсить JS-объект в dict: сначала json5, затем грубая нормализация"""
        # Попытка через json5, если установлен
        try:
            import json5  # type: ignore

            return json5.loads(js_obj_text)
        except Exception:
            pass

        # Грубая нормализация: кавычки вокруг ключей, одинарные кавычки -> двойные, удаление запятых перед \}
        try:
            s = js_obj_text
            # Удаляем новые строки для стабильности
            s = s.replace("\n", " ")
            # Добавляем кавычки вокруг ключей простого вида
            s = re.sub(
                r"(?P<pre>[{,\s])(?P<key>[A-Za-z0-9_]+)\s*:",
                r"\g<pre>\"\g<key>\":",
                s,
            )
            # Одинарные кавычки -> двойные
            s = re.sub(r"'", '"', s)
            # Удаляем запятые перед закрывающей скобкой
            s = re.sub(r",\s*([}\]])", r"\1", s)
            return json.loads(s)
        except Exception:
            return None

    def get_name_to_order_for_hero(self, hero_name: str) -> Dict[str, int]:
        """Возвращает маппинг имя фасета -> порядковый номер для конкретного героя."""
        # Если общий кеш уже есть и в нем есть нужный герой
        if self.hero_facets_cache and hero_name in self.hero_facets_cache:
            return self.hero_facets_cache.get(hero_name, {})

        # Пробуем получить общий маппинг
        try:
            mapping = self.get_hero_facets_mapping(headless=True)
            if mapping and hero_name in mapping:
                return mapping.get(hero_name, {})
        except Exception:
            pass

        return {}

    def _build_mapping_from_facets(
        self, facets: List[dict]
    ) -> Dict[str, Dict[str, int]]:
        """Строит маппинг напрямую из фасетов Dotabuff"""
        # Группируем по hero_id, сортируем по hero_variant и id, нумеруем 1..n
        by_hero: Dict[int, List[dict]] = {}
        for f in facets:
            hid = f.get("hero_id")
            if not isinstance(hid, int):
                continue
            by_hero.setdefault(hid, []).append(f)

        result: Dict[str, Dict[str, int]] = {}
        for hid, lst in by_hero.items():
            lst.sort(key=lambda x: (x.get("hero_variant", 9999), x.get("id", 999999)))

            # Получаем имя героя из slug
            hero_name = None
            if lst:
                slug = lst[0].get("slug", "")
                hero_name = self._name_from_slug(slug)

            if not hero_name:
                hero_name = f"Hero {hid}"

            name_to_order: Dict[str, int] = {}
            order = 1
            for fac in lst:
                name = fac.get("name")
                if not isinstance(name, str) or not name.strip():
                    # фолбек по описанию
                    alias = self._alias_from_description(fac.get("description"))
                    name = alias or f"Facet {order}"
                if name not in name_to_order:
                    name_to_order[name] = order
                    order += 1
            result[hero_name] = name_to_order
        return result

    def get_facet_number_for_hero(self, hero_name: str, facet_name: str) -> int:
        if not self.hero_facets_cache:
            self.hero_facets_cache = self.get_hero_facets_mapping(headless=True)
        hero_facets = self.hero_facets_cache.get(hero_name, {})
        if facet_name in hero_facets:
            return hero_facets[facet_name]
        for known, num in hero_facets.items():
            if (
                facet_name.lower() in known.lower()
                or known.lower() in facet_name.lower()
            ):
                return num
        return 1

    def _try_dotabuff_facets(self, manager=None, headless: bool = True) -> Dict[str, Dict[str, int]]:
        """Получение фасетов через Dotabuff - только одна страница Nature's Prophet"""
        from ..core.scraping_manager import ScrapingManager

        if manager is None:
            self.logger.info("Запуск Selenium для Dotabuff...")
            with ScrapingManager(headless=headless) as manager:
                return self._try_dotabuff_facets(manager, headless=headless)
        else:
            # Используем переданный manager
            # Прямо идем на страницу Nature's Prophet
            hero_url = "https://www.dotabuff.com/heroes/natures-prophet"
            self.logger.info(f"Переход на страницу героя: {hero_url}")
            manager.navigate_to_page_basic(hero_url)

            # Ждем загрузки страницы и всех ресурсов
            import time

            time.sleep(5)

            # Проверяем, прошли ли мы Cloudflare challenge
            if (
                "Just a moment" in manager.driver.title
                or "Checking your browser" in manager.get_page_source()
            ):
                self.logger.info("Обнаружен Cloudflare challenge, ждем...")
                time.sleep(10)

                if "Just a moment" in manager.driver.title:
                    raise RuntimeError("Не удалось пройти Cloudflare challenge")

            # Получаем все загруженные ресурсы через JavaScript
            self.logger.info("Поиск repo скрипта...")
            all_resources = manager.driver.execute_script(
                """
                return performance.getEntriesByType('resource')
                    .map(r => r.name)
                    .filter(name => name.includes('/static/') && name.endsWith('.js'));
            """
            )

            self.logger.info(f"Найдено {len(all_resources)} JS файлов в /static/")

            # Ищем repo файлы
            repo_resources = [r for r in all_resources if "/static/repo-" in r]
            if not repo_resources:
                raise RuntimeError("Repo скрипт не найден в Network запросах")

            repo_js_url = repo_resources[0]
            self.logger.info(f"Найден repo скрипт: {repo_js_url}")

            # Загружаем содержимое repo скрипта
            self.logger.info(f"Загружаем содержимое: {repo_js_url}")
            manager.navigate_to_page_basic(repo_js_url)

            # Получаем содержимое JS файла
            js_content = manager.get_page_source()
            self.logger.info(f"Получен JS контент размером {len(js_content)} символов")

            # Парсим фасеты из JS
            facets = self._extract_facets_from_repo(js_content)
            if not facets:
                raise RuntimeError("Не удалось извлечь фасеты из JS")

            self.logger.info(f"Найдено {len(facets)} фасетов в JS")

            # Строим маппинг напрямую из фасетов
            mapping = self._build_mapping_from_facets(facets)
            return mapping
