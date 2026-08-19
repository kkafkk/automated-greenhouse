from smbus2 import SMBus  # Библиотека для работы с I2C

# Адрес устройства на шине I2C
DEVICE_ADDRESS = 0x48
# Регистр для чтения данных освещенности
AIN2 = 0x42

def get_light_lux():
    try:
        # Инициализация шины I2C
        with SMBus(1) as bus:
            # Запрос данных с датчика
            bus.write_byte(DEVICE_ADDRESS, AIN2)
            bus.read_byte(DEVICE_ADDRESS)  # Первое чтение для инициализации
            raw = bus.read_byte(DEVICE_ADDRESS)  # Чтение данных

            # Инверсия значения (датчик возвращает обратное значение)
            inverted = 255 - raw

            # Корректировка значения с учетом смещения
            lux_raw = inverted - 20

            # Ограничение минимального значения
            if lux_raw < 0:
                lux_raw = 0

            # Преобразование в люксы
            lux = lux_raw * 4.0

            # Округление результата
            return round(lux, 1)
    except Exception as e:
        print(f"Ошибка датчика: {e}")
        return None