import logging
import datetime
import json
import os
import socket
import time
from waveshare_epd import epd7in5
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO


DATA_FILE = '/home/vasilisa/project/smart_mushroom_sensors.json'
TEMPLATE_PATH = 'шаблон.PNG'
CHECK_INTERVAL = 60  
# Настройка логгирования
logging.basicConfig(level=logging.INFO)

def get_ip_address():
    """текущий IP-адрес"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1 (Нет сети)"

#Отрисовка данных на e-Paper дисплее
def get_data_from_json():
    if os.path.exists(DATA_FILE):
        try:
            mtime = os.path.getmtime(DATA_FILE)
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f), mtime
        except Exception as e:
            logging.error(f"Ошибка чтения JSON: {e}")
     # Возврат данных по умолчанию, если файл отсутствует или нечитаем
    return {
        "температура": "--",
        "влажность": "--",
        "влажность_почвы": "--",
        "co2": "--",
        "освещенность": "--",
        "время": "Нет данных"
    }, 0

def draw_and_update(data, ip_addr):
    try:
        epd = epd7in5.EPD()
        epd.init() 
        
        try:
            image = Image.open(TEMPLATE_PATH).convert('1')
        except FileNotFoundError:
            logging.error(f"Файл '{TEMPLATE_PATH}' не найден!")
            image = Image.new('1', (epd.width, epd.height), 255)

        draw = ImageDraw.Draw(image)


        try:
            font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 35)
            font_data = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
            font_link = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
        except:
            font_title = font_data = font_link = ImageFont.load_default()

        # Отрисовка заголовка
        draw.text((50, 30), "МОНИТОРИНГ ТЕПЛИЦЫ", font=font_title, fill=0)
        draw.line((55, 80, 500, 80), fill=0, width=3) 

        # Отрисовка данных с датчиков
        draw.text((44, 95), f" Температура: {data.get('температура', '--')} °C", font=font_data, fill=0)
        draw.text((44, 130), f" Влажность: {data.get('влажность', '--')} %", font=font_data, fill=0)
        draw.text((44, 165), f" Почва: {data.get('влажность_почвы', '--')} %", font=font_data, fill=0)
        draw.text((50, 200), f"☁ CO2: {data.get('co2', '--')} ppm", font=font_data, fill=0)
        draw.text((50, 235), f"☀ Свет: {data.get('освещенность', '--')} lm", font=font_data, fill=0)

        # Отрисовка времени замера
        draw.text((52, 270), f"Время замера: {data.get('время', 'Нет данных')}", font=font_link, fill=0)

        # Отрисовка ссылки на сайт управления
        draw.rectangle((40, 400, 550, 450), outline=0, width=2) 
        draw.text((52, 310), "Сайт управления:", font=font_data, fill=0)
        draw.text((53, 345), f"http://{ip_addr}:8000", font=font_link, fill=0)

        # Логгирование и вывод на дисплей
        logging.info(f"Отрисовка... (IP: {ip_addr})")
        epd.display(epd.getbuffer(image))
        
        # Перевод дисплея в спящий режим
        epd.sleep()
        logging.info("Дисплей в спящем режиме.")

    except Exception as e:
        logging.error(f"Ошибка экрана: {e}")
#Основной цикл программы
def main():
    logging.info("Ожидание подключения к сети...")
    
    last_mtime = 0
    last_ip = ""
    
    logging.info("Скрипт мониторинга запущен. Ожидание данных...")

    while True:
        current_data, current_mtime = get_data_from_json()
        current_ip = get_ip_address()


        if current_mtime > last_mtime or current_ip != last_ip:
            if current_ip != last_ip:
                logging.info(f"Смена IP: {last_ip} -> {current_ip}")
            else:
                logging.info("JSON файл обновился")

            draw_and_update(current_data, current_ip)
            

            last_mtime = current_mtime
            last_ip = current_ip
        
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Скрипт остановлен пользователем")
        GPIO.cleanup()
