import board
import busio
import adafruit_pcf8591.pcf8591 as PCF
from adafruit_pcf8591.analog_in import AnalogIn

class MQ135Sensor:
    def __init__(self, r0=25.98):
        # Инициализация I2C-шины для связи с ADC (PCF8591)
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pcf = PCF.PCF8591(self.i2c)
        # Настройка аналогового входа A0 на PCF8591 для датчика MQ135
        self.adc_pin = AnalogIn(self.pcf, PCF.A0)
        # Параметры калибровки датчика
        self.R0 = r0
        self.RLOAD = 10.0
        self.V_REF = 3.3

    def get_ppm(self):
        try:
            # Считывание напряжения с датчика
            voltage = self.adc_pin.voltage
            
            # Проверка на минимальное напряжение (шум/ошибка)
            if voltage < 0.1: 
                return 415.0  # Уровень свежего воздуха
            # Ограничение максимального напряжения (защита от выбросов)
            if voltage >= self.V_REF:
                voltage = self.V_REF - 0.1
            
            # Расчет сопротивления датчика (Rs)
            rs = ((self.V_REF - voltage) * self.RLOAD) / voltage
            # Расчет отношения Rs/R0
            ratio = rs / self.R0
            # Формула для расчета концентрации CO₂ (ppm) по характеристике MQ135
            ppm_raw = 110.47 * pow(ratio, -2.862)
            # Корректировка значения (смещение на уровень чистого воздуха)
            final_ppm = ppm_raw + 415.0
            # Округление и ограничение максимального значения (5000 ppm)
            return round(min(final_ppm, 5000.0), 1)
            
        except Exception as e:
            print(f"Ошибка при чтении датчика: {e}")
            return None
# Демонстрационный блок (запускается при прямом выполнении скрипта)
if __name__ == "__main__":
    import time
    sensor = MQ135Sensor()   # Инициализация датчика с калибровочным R0
    print("Датчик готов. Начинаю замер...")
    try:
        while True:
            print(f"Концентрация CO2: {sensor.get_ppm()} ppm")
            time.sleep(2)  # Пауза между замерами
    except KeyboardInterrupt:
        print("Остановка...")
