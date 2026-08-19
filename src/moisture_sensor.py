import smbus2
import time

class SoilSensor:
    def __init__(self, address=0x48, channel=1):
         # Инициализация шины I2C
        self.bus = smbus2.SMBus(1)
        # Адрес устройства на шине I2C
        self.address = address
        # Канал ADC для считывания данных
        self.channel = channel

        # Значения для калибровки датчика влажности почвы
        self.DRY_VALUE = 165  # Значение для сухой почвы
        self.WET_VALUE = 80   # Значение для влажной почвы  
    #Чтение необработанных данных с датчика
    def get_raw_value(self):
        try:

            self.bus.write_byte(self.address, 0x40 + self.channel)
            self.bus.read_byte(self.address)
            return self.bus.read_byte(self.address)
        except Exception as e:
            print(f"Ошибка чтения I2C: {e}")
            return None

    def get_moisture_percentage(self):
        """Влажность в процентах (0-100%)"""
        raw = self.get_raw_value()
        if raw is None: return 0
        

        # Преобразование полученных данных в проценты
        percentage = ((self.DRY_VALUE - raw) / (self.DRY_VALUE - self.WET_VALUE)) * 100

        # Ограничение диапазона значений от 0 до 100
        return max(0, min(100, round(percentage, 1)))

    def get_status_text(self, percentage):
        """Текстовое описание состояния влажности почвы"""
        if percentage < 30:
            return "❌ Почва слишком сухая! Нужно полить."
        elif 30 <= percentage <= 70:
            return "✅ Влажность в норме."
        else:
            return "🌊 Слишком много воды!"
