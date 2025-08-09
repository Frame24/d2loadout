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

    def get_hero_facets_mapping(self) -> Dict[str, Dict[str, int]]:
        try:
            self.logger.info("Получение фасетов из Dotabuff repo-*.js...")
            # 0) ENV override
            env_repo = os.environ.get("DOTABUFF_REPO_JS_URL")
            if env_repo:
                self.logger.info(
                    f"Использую DOTABUFF_REPO_JS_URL из окружения: {env_repo}"
                )
                js_text = self._fetch_url(env_repo, referer="https://www.dotabuff.com/")
            else:
                try:
                    repo_js_url = self._discover_dotabuff_repo_js_http()
                    js_text = self._fetch_url(
                        repo_js_url, referer="https://www.dotabuff.com/"
                    )
                except Exception as e_http:
                    self.logger.warning(
                        f"HTTP-доступ к repo js не удался ({e_http}). Пробуем через Selenium..."
                    )
                    repo_js_url, js_text = self._fetch_repo_js_via_selenium()

            facets = self._extract_facets_from_repo(js_text)
            if not facets:
                self.logger.error("Не удалось извлечь facets из repo js")
                # Переходим на фолбек через D2PT facetData
                raise RuntimeError("Empty facets from repo js")
            hero_id_to_name = self._load_d2pt_hero_id_to_name()
            mapping = self._build_mapping(facets, hero_id_to_name)
            self.hero_facets_cache = mapping
            self.logger.info(f"✅ Получены фасеты для {len(mapping)} героев (Dotabuff)")
            return mapping
        except Exception as e:
            self.logger.warning(f"Dotabuff недоступен, фолбек на D2PT facetData: {e}")
            try:
                mapping = self._build_mapping_from_d2pt_facets()
                if mapping:
                    self.hero_facets_cache = mapping
                    self.logger.info(
                        f"✅ Получены фасеты для {len(mapping)} героев (D2PT facetData)"
                    )
                else:
                    self.logger.error("Не удалось получить фасеты через D2PT facetData")
                return mapping
            except Exception as e2:
                self.logger.error(f"Ошибка фолбека через D2PT facetData: {e2}")
                return {}

    def _discover_dotabuff_repo_js_http(self) -> str:
        # Пробуем главную, а не страницу героя
        root_url = "https://www.dotabuff.com/"
        html = self._fetch_url(root_url, referer="https://www.dotabuff.com/")
        return self._extract_repo_js_url_from_html(html)

    def _extract_repo_js_url_from_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if src.startswith("/static/repo-") and src.endswith(".js"):
                return f"https://www.dotabuff.com{src}"
        m = re.search(r"<script[^>]+src=\"(/static/repo-[^\"]+\.js)\"", html)
        if m:
            return f"https://www.dotabuff.com{m.group(1)}"
        raise RuntimeError("Не удалось найти ссылку на repo-*.js на главной Dotabuff")

    def _fetch_repo_js_via_selenium(self) -> Tuple[str, str]:
        with ScrapingManager(headless=True) as manager:
            # 1) идем на главную
            root_url = "https://www.dotabuff.com/"
            manager.navigate_to_page_basic(root_url)
            # 2) пробуем получить список скриптов через JS
            repo_js_url = None
            try:
                scripts: List[str] = manager.driver.execute_script(
                    "return Array.from(document.scripts).map(s=>s.src).filter(Boolean);"
                )
                for s in scripts:
                    if "/static/repo-" in s and s.endswith(".js"):
                        repo_js_url = (
                            s
                            if s.startswith("http")
                            else f"https://www.dotabuff.com{s}"
                        )
                        break
            except Exception:
                pass
            # 3) если не нашли — через Performance API
            if not repo_js_url:
                try:
                    resources: List[dict] = manager.driver.execute_script(
                        "return performance.getEntriesByType('resource').map(r=>r.name);"
                    )
                    for name in resources:
                        if "/static/repo-" in name and name.endswith(".js"):
                            repo_js_url = name
                            break
                except Exception:
                    pass
            if not repo_js_url:
                # 4) последняя попытка — открыть страницу героя и повторить
                hero_url = "https://www.dotabuff.com/heroes/natures-prophet"
                manager.navigate_to_page_basic(hero_url)
                try:
                    scripts: List[str] = manager.driver.execute_script(
                        "return Array.from(document.scripts).map(s=>s.src).filter(Boolean);"
                    )
                    for s in scripts:
                        if "/static/repo-" in s and s.endswith(".js"):
                            repo_js_url = (
                                s
                                if s.startswith("http")
                                else f"https://www.dotabuff.com{s}"
                            )
                            break
                except Exception:
                    pass
            if not repo_js_url:
                raise RuntimeError("Не удалось найти repo-*.js через Selenium")
            # 5) загружаем сам файл и читаем innerText
            manager.navigate_to_page_basic(repo_js_url)
            try:
                js_text = manager.driver.execute_script(
                    "return document.body.innerText || document.body.textContent || '';"
                )
            except Exception:
                js_text = manager.get_page_source()
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
        m = re.search(r"const\s+f\s*=\s*JSON\.parse\(`(\[.*?\])`\)", js_text, re.DOTALL)
        if not m:
            return []
        import json

        raw = m.group(1)
        facets = json.loads(raw)
        valid = [x for x in facets if not x.get("deprecated")]
        return valid

    def _load_d2pt_hero_id_to_name(self) -> Dict[int, str]:
        # https://dota2protracker.com/api/heroes/list -> [{displayName, hero_id}, ...]
        url = "https://dota2protracker.com/api/heroes/list"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            mapping: Dict[int, str] = {}
            for it in data:
                hid = it.get("hero_id")
                name = it.get("displayName")
                if isinstance(hid, int) and isinstance(name, str):
                    mapping[hid] = name
            return mapping
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить hero_id→name из D2PT: {e}")
            return {}

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

    def _load_d2pt_hero_display_names(self) -> List[str]:
        """Загружает displayName героев из D2PT API"""
        url = "https://dota2protracker.com/api/heroes/list"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            names: List[str] = []
            for it in data:
                name = it.get("displayName")
                if isinstance(name, str) and name:
                    names.append(name)
            return names
        except Exception:
            return []

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
                r"\g<pre>" "\g<key>" ":",
                s,
            )
            # Одинарные кавычки -> двойные
            s = re.sub(r"'", '"', s)
            # Удаляем запятые перед закрывающей скобкой
            s = re.sub(r",\s*([}\]])", r"\1", s)
            return json.loads(s)
        except Exception:
            return None

    def _parse_facetdata_from_hero_page(self, hero_name: str) -> List[dict]:
        """Возвращает список фасетов (dict) для героя из hero page (facetData)"""
        url = f"https://dota2protracker.com/hero/{quote(hero_name)}"
        try:
            html = self._fetch_url(url, referer="https://dota2protracker.com/")
            # Ищем JS-объект facetData: {...}}
            m = re.search(r"facetData:\s*({.*?})\s*\}\s*,", html, re.DOTALL)
            if not m:
                return []
            js_obj_text = m.group(1)
            data = self._try_parse_js_object(js_obj_text)
            if isinstance(data, dict):
                # Структура: ключ -> {id, localized_name, facets: [...]}
                # Собираем список фасетов (не deprecated)
                collected: List[dict] = []
                for _, value in data.items():
                    for fac in (
                        value.get("facets", []) if isinstance(value, dict) else []
                    ):
                        if not fac.get("deprecated"):
                            collected.append(fac)
                return collected
            # Фолбек: извлечение через regex имен фасетов из блока facets:[...]
            collected: List[dict] = []
            for facets_block in re.findall(
                r"facets\s*:\s*\[(.*?)\]", js_obj_text, re.DOTALL
            ):
                # Находим отдельные объекты фасетов и вытаскиваем name и deprecated
                for obj_txt in re.findall(r"\{(.*?)\}", facets_block, re.DOTALL):
                    # deprecated
                    dep_m = re.search(r"deprecated\s*:\s*(true|false)", obj_txt)
                    is_dep = dep_m and dep_m.group(1) == "true"
                    if is_dep:
                        continue
                    name_m = re.search(r"name\s*:\s*['\"]([^'\"]+)['\"]", obj_txt)
                    if name_m:
                        collected.append({"name": name_m.group(1)})
            return collected
        except Exception:
            return []

    def get_name_to_order_for_hero(self, hero_name: str) -> Dict[str, int]:
        """Возвращает маппинг имя фасета -> порядковый номер для конкретного героя.
        Пытается использовать кеш/общий маппинг, затем парсит страницу героя при необходимости.
        """
        # Если общий кеш уже есть и в нем есть нужный герой
        if self.hero_facets_cache and hero_name in self.hero_facets_cache:
            return self.hero_facets_cache.get(hero_name, {})

        # Пробуем получить общий маппинг (может сработать в этот раз)
        try:
            mapping = self.get_hero_facets_mapping()
            if mapping and hero_name in mapping:
                return mapping.get(hero_name, {})
        except Exception:
            pass

        # Парсим только страницу конкретного героя
        facets = self._parse_facetdata_from_hero_page(hero_name)
        if not facets:
            return {}
        # Упорядочиваем как есть (или по hero_variant/id если присутствуют)
        try:
            facets.sort(
                key=lambda x: (x.get("hero_variant", 9999), x.get("id", 999999))
            )
        except Exception:
            pass
        name_to_order: Dict[str, int] = {}
        order = 1
        for fac in facets:
            fname = fac.get("name")
            if isinstance(fname, str) and fname.strip() and fname not in name_to_order:
                name_to_order[fname] = order
                order += 1
        # Кладем в кеш частично
        if name_to_order:
            self.hero_facets_cache[hero_name] = name_to_order
        return name_to_order

    def _build_mapping_from_d2pt_facets(self) -> Dict[str, Dict[str, int]]:
        """Строит маппинг name->order по facetData со страниц героев D2PT"""
        result: Dict[str, Dict[str, int]] = {}
        # Список имен героев (displayName)
        names = self._load_d2pt_hero_display_names()
        if not names:
            return result
        for hero_name in names:
            facets = self._parse_facetdata_from_hero_page(hero_name)
            if not facets:
                continue
            # Сортировать по hero_variant и id при наличии, иначе по порядку появления
            try:
                facets.sort(
                    key=lambda x: (x.get("hero_variant", 9999), x.get("id", 999999))
                )
            except Exception:
                pass
            name_to_order: Dict[str, int] = {}
            order = 1
            for fac in facets:
                fname = fac.get("name")
                if not isinstance(fname, str) or not fname.strip():
                    # фолбек по описанию
                    alias = self._alias_from_description(fac.get("description"))
                    fname = alias or f"Facet {order}"
                if fname not in name_to_order:
                    name_to_order[fname] = order
                    order += 1
            if name_to_order:
                result[hero_name] = name_to_order
        return result

    def get_facet_number_for_hero(self, hero_name: str, facet_name: str) -> int:
        if not self.hero_facets_cache:
            self.hero_facets_cache = self.get_hero_facets_mapping()
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
