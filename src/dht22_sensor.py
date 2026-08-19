import adafruit_dht # Библиотека для работы с датчиками DHT
import board
import time
# Пин, к которому подключен датчик DHT22
DHT_PIN = board.D19
# Инициализация датчика DHT22
dht_device = adafruit_dht.DHT22(DHT_PIN)

def get_temperature_humidity():
    try:
        # Чтение данных с датчика
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        
        if temperature is not None and humidity is not None:
            return temperature, humidity
        else:
            return None, None
    except RuntimeError as error:
         # Ошибки чтения (например, датчик не отвечает)
        print(f"Ошибка чтения: {error.args[0]}")
        return None, None
    except Exception as error:
        dht_device.exit()
        raise error