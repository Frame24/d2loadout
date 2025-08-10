@echo off
setlocal enabledelayedexpansion

:: Заголовок
echo ================================================================
echo                   Dota 2 Loadout Generator
echo           Автоматический сбор данных и создание
echo              конфигураций для Dota 2
echo ================================================================
echo.

:: Переход в корневую директорию проекта (если bat файл запущен из подпапки)
if exist "..\requirements.txt" (
    cd ..
)

:: Проверка наличия Python
echo Проверяем наличие Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo.
    echo Пожалуйста, установите Python 3.8+ с официального сайта:
    echo    https://www.python.org/downloads/
    echo.
    echo При установке обязательно отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo OK: Python !PYTHON_VERSION! найден
)

:: Проверка наличия виртуального окружения
echo.
echo Проверяем виртуальное окружение...
if not exist ".venv" (
    echo Создаем виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo ОШИБКА: Ошибка создания виртуального окружения
        pause
        exit /b 1
    )
    echo OK: Виртуальное окружение создано
) else (
    echo OK: Виртуальное окружение найдено
)

:: Активация виртуального окружения
echo.
echo Активируем виртуальное окружение...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ОШИБКА: Ошибка активации виртуального окружения
    pause
    exit /b 1
)

:: Проверка и установка зависимостей
echo.
echo Проверяем зависимости...
python -c "import selenium" >nul 2>&1
if errorlevel 1 (
    echo Устанавливаем необходимые библиотеки...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ОШИБКА: Ошибка установки зависимостей
        pause
        exit /b 1
    )
    echo OK: Зависимости установлены
) else (
    echo OK: Все зависимости уже установлены
)

:: Проверка наличия Chrome
echo.
echo Проверяем наличие Google Chrome...
where chrome >nul 2>&1
if errorlevel 1 (
    :: Проверяем стандартные пути установки Chrome
    if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
        echo OK: Google Chrome найден
    ) else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
        echo OK: Google Chrome найден
    ) else if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
        echo OK: Google Chrome найден
    ) else (
        echo ВНИМАНИЕ: Google Chrome не найден
        echo Пожалуйста, установите Google Chrome с официального сайта:
        echo    https://www.google.com/chrome/
        echo.
        echo Chrome необходим для автоматического сбора данных
        echo Вы также можете продолжить - ChromeDriver загрузится автоматически
        echo.
        set /p choice="Продолжить без Chrome? (y/n): "
        if /i "!choice!" neq "y" (
            pause
            exit /b 1
        )
    )
) else (
    echo OK: Google Chrome найден
)

:: Запуск основного скрипта
echo.
echo ================================================================
echo Запускаем сбор данных...
echo ================================================================
echo.

:: Запуск в тихом режиме
python dota2_data_scraper\main.py --quiet

:: Проверка результата
if errorlevel 1 (
    echo.
    echo ОШИБКА: Процесс завершился с ошибками
    echo Для диагностики запустите: python dota2_data_scraper\main.py --no-headless
    echo.
) else (
    echo.
    echo ================================================================
    echo Запустите Dota 2 и проверьте новые конфигурации героев!
    echo ================================================================
)

echo.
echo Нажмите любую клавишу для выхода...
pause >nul 