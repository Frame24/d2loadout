import threading

def quit_driver(driver):
    """
    Функция завершения работы драйвера браузера в фоновом потоке.
    """
    def cleanup():
        if driver.service.process:
            driver.quit()
    
    threading.Thread(target=cleanup).start()
