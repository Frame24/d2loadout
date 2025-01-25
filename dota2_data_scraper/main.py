import subprocess
import argparse
import sys

# Проверка используемого Python-интерпретатора
print(f"Используется Python: {sys.executable}")

# Проверка установки Selenium в текущем окружении
try:
    import selenium
    print(f"Selenium установлен, версия: {selenium.__version__}")
except ImportError:
    print("❌ Selenium не найден. Установите его с помощью 'pip install selenium'.")
    sys.exit(1)

def run_script(script_name):
    """Функция для запуска указанного скрипта с использованием текущего интерпретатора Python."""
    python_executable = sys.executable  # Используем текущий интерпретатор из виртуального окружения
    try:
        result = subprocess.run(
            [python_executable, "-m", script_name],
            text=True,
            stdout=subprocess.PIPE,  # Подавляем вывод в консоль
            stderr=subprocess.PIPE  # Перехватываем ошибки
        )
        if result.returncode == 0:
            print(f"✅ {script_name} выполнен успешно.")
        else:
            print(f"❌ Ошибка при выполнении {script_name}:\n{result.stderr}")
    except Exception as e:
        print(f"❌ Ошибка при запуске {script_name}: {e}")

# Настройка аргументов командной строки
parser = argparse.ArgumentParser(description="Запуск скриптов обработки данных")
parser.add_argument("--scraper", action="store_true", help="Запуск run_scraper.py")
parser.add_argument("--facets", action="store_true", help="Запуск run_facet_scraper.py")
parser.add_argument("--config", action="store_true", help="Запуск run_config_processor.py")

args = parser.parse_args()

# Определяем, какой скрипт запускать
if args.scraper:
    run_script("scripts.run_scraper")
elif args.facets:
    run_script("scripts.run_facet_scraper")
elif args.config:
    run_script("scripts.run_config_processor")
else:
    print("Запуск всех скриптов по порядку...")
    scripts = [
        "scripts.run_scraper",
        "scripts.run_facet_scraper",
        "scripts.run_config_processor",
    ]
    for script in scripts:
        run_script(script)

print("Все процессы завершены.")
