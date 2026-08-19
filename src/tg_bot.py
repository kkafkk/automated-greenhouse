"""
Программа для управления умной теплицей с использованием Telegram-бота.
Основные функции: мониторинг датчиков, управление устройствами, оповещения.
"""
# Импорт библиотек
import asyncio
import logging
import datetime
import json
import time
import os
import RPi.GPIO as GPIO
import socket
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Импорт модулей датчиков

try:
    from dht22_sensor import get_temperature_humidity
    from moisture_sensor import SoilSensor
    from air_sensor import MQ135Sensor
    from lux_sensor import get_light_lux
except ImportError as e:
    logging.error(f"Не удалось импортировать модули датчиков: {e}")

# Глобальные переменные и константы
    
current_active_mode_name = None
LIGHT_PIN = 21
STEAM_PIN = 23
PELTIER_PIN = 26
FAN_PIN = 12
DATA_FILE = '/home/vasilisa/project/smart_mushroom_sensors.json'
CONFIG_FILE = '/home/vasilisa/project/config.json'
ALERT_RETRY_INTERVAL = 3600

last_alerts_time = {"temp": 0, "hum": 0, "co2": 0, "soil": 0, "light": 0}

# Инициализация GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([LIGHT_PIN, STEAM_PIN, PELTIER_PIN, FAN_PIN], GPIO.OUT)
GPIO.setup(LIGHT_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(STEAM_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PELTIER_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(FAN_PIN, GPIO.OUT, initial=GPIO.LOW)

# Инициализация датчиков

try:
    moisture_sensor = SoilSensor(address=0x48, channel=1)
    air_sensor = MQ135Sensor(r0=25.98)
except Exception:
    moisture_sensor = None
    air_sensor = None
    logging.warning("Датчики (Moisture/Air) не обнаружены физически.")

# Конфигурация Telegram-бота

TOKEN = '8241988636:AAHuvaF5M6PZtx7LvyiZBUYgWYtHyPUTgyo'
SCREEN_UPDATE_COOLDOWN = 60

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
admin_id = 5074387133

# Вспомогательные функции

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"
    
    
def get_current_limits():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                conf = json.load(f)
            active_mode_key = conf['current_state']['active_mode']
            return conf['modes'].get(active_mode_key)
    except: return None    


def sync_read_sensors():
    res = {"t": None, "h": None, "m": 0, "c": 0, "l": 0}
    try:
        t, h = get_temperature_humidity()
        res["t"], res["h"] = t, h
    except: pass
    try:
        if moisture_sensor: res["m"] = moisture_sensor.get_moisture_percentage()
    except: pass
    try:
        if air_sensor: res["c"] = air_sensor.get_ppm()
    except: pass
    try:
        res["l"] = get_light_lux()
    except: pass
    return res



async def update_sensors_logic():

    loop = asyncio.get_running_loop()
    now = datetime.datetime.now()
    raw = await loop.run_in_executor(None, sync_read_sensors)
    sensor_data = {
        "температура": raw["t"] if raw["t"] is not None else "--",
        "влажность": raw["h"] if raw["h"] is not None else "--",
        "влажность_почвы": raw["m"],
        "co2": raw["c"],
        "освещенность": raw["l"],
        "время": now.strftime("%H:%M:%S")
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(sensor_data, f, ensure_ascii=False, indent=2)
    return sensor_data, raw["t"], raw["h"], raw["m"], raw["c"], raw["l"], now

# Фоновый мониторинг датчиков

async def background_sensor_monitor():

    global last_alerts_time, current_active_mode_name
    while True:
        try:

            _, t, h, m, c, l, now = await update_sensors_logic()

            limits = get_current_limits()
            
            if limits:
                cur_ts = time.time()
                alerts_list = []

                new_mode_name = limits.get('name')
                if current_active_mode_name is not None and new_mode_name != current_active_mode_name:
                    change_msg = (
                        f"🔄 <b>РЕЖИМ ИЗМЕНЕН!</b>\n"
                        f"Старый режим: <s>{current_active_mode_name}</s>\n"
                        f"Новый режим: <b>{new_mode_name}</b>\n"
                        f"──────────────────\n"
                        f"🎯 Цель: {limits.get('temp_target')}°C / {limits.get('humidity_target')}%"
                    )
                    await bot.send_message(admin_id, change_msg, parse_mode="HTML")
                

                current_active_mode_name = new_mode_name

                light_h = limits.get('light_hours', 0)
                if light_h > 0 and (8 <= now.hour < 8 + light_h):
                    GPIO.output(LIGHT_PIN, GPIO.HIGH)
                else:
                    GPIO.output(LIGHT_PIN, GPIO.LOW)

                t_target = limits.get('temp_target')
                t_thresh = limits.get('temp_threshold', 2.0)
                
                if t is not None:

                    if t > (t_target + t_thresh):
                        GPIO.output(PELTIER_PIN, GPIO.HIGH)
                        GPIO.output(FAN_PIN, GPIO.HIGH)
                        if cur_ts - last_alerts_time['temp'] > ALERT_RETRY_INTERVAL:
                            alerts_list.append(f"🌡 Перегрев: {t}°C. Охлаждение ВКЛ ❄️")
                            last_alerts_time['temp'] = cur_ts
                    elif t < t_target:
                        GPIO.output(PELTIER_PIN, GPIO.LOW)
                        GPIO.output(FAN_PIN, GPIO.LOW)
                        last_alerts_time['temp'] = 0


                h_target = limits.get('humidity_target')
                if h is not None:
                    if h < (h_target - 5):
                        GPIO.output(STEAM_PIN, GPIO.HIGH)
                        if cur_ts - last_alerts_time['hum'] > ALERT_RETRY_INTERVAL:
                            alerts_list.append(f"💧 Сухо: {h}%. Увлажнение ВКЛ 💨")
                            last_alerts_time['hum'] = cur_ts
                    elif h >= h_target:
                        GPIO.output(STEAM_PIN, GPIO.LOW)
                        last_alerts_time['hum'] = 0


                co2_max = limits.get('co2_max')
                if co2_max and c > co2_max and cur_ts - last_alerts_time['co2'] > ALERT_RETRY_INTERVAL:
                    alerts_list.append(f"🌬 Высокий CO2: {c} PPM")
                    last_alerts_time['co2'] = cur_ts
                
                if m is not None and m < 20 and cur_ts - last_alerts_time['soil'] > ALERT_RETRY_INTERVAL:
                    alerts_list.append(f"🪴 Сухая почва: {m}%")
                    last_alerts_time['soil'] = cur_ts

                if alerts_list:
                    msg = (f"🚨 <b>КОНТРОЛЬ: {new_mode_name}</b>\n"
                           f"──────────────────\n" + "\n".join(alerts_list) +
                           f"\n──────────────────\n⏰ {now.strftime('%H:%M:%S')}")
                    await bot.send_message(admin_id, msg, parse_mode="HTML")

            logging.info("Мониторинг климата выполнен.")
        except Exception as e:
            logging.error(f"Ошибка в фоновом процессе: {e}")
        
        await asyncio.sleep(300)

# Клавиатуры

def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Показатели датчиков"),
        KeyboardButton(text="⚙️ Комплектация"),
        KeyboardButton(text="🎮 Панель управления")
    )
    builder.row(
        KeyboardButton(text="📝 Заполнить анкету"),
        KeyboardButton(text="👨‍💻 Поддержка")
    )
    builder.row(KeyboardButton(text='📸 Сделать фото'))
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите нужный раздел...")

def devices_inline_kb():
    l_st = "🟢" if GPIO.input(LIGHT_PIN) else "🔴"
    s_st = "🟢" if GPIO.input(STEAM_PIN) else "🔴"
    p_st = "🟢" if GPIO.input(PELTIER_PIN) else "🔴"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"Свет {l_st}", callback_data="toggle_light"),
            InlineKeyboardButton(text=f"Пар {s_st}", callback_data="toggle_steam")
        ],
        [
            InlineKeyboardButton(text=f"Охлаждение (Пельтье+Вентиляторы) {p_st}", callback_data="toggle_cooling")
        ]
    ])

def link_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать администратору ✉️", url='https://t.me/vasechkaa_kr')]
    ])

# Обработчики команд и сообщений

@dp.message(Command('start'))
async def command_start(message: Message):
    welcome_text = (
        "<b>🌿 Добро пожаловать в SmartMushroom!</b>\n"
        "──────────────────────────\n"
        "Я твой персональный помощник по управлению умной теплицей. 👋🏻\n\n"
        "<b>Что я умею:</b>\n"
        "• Мониторинг данных с датчиков в реальном времени.\n"
        "• Предоставление полной информации о модулях теплицы.\n"
        "• Получение помощи через обратную связь с разработчиком.\n"
        "• Сбор обратной связи через анкеты.\n\n"
        "<i>Используй кнопки меню ниже, чтобы начать работу.</i>"
    )
    await message.answer(welcome_text, reply_markup=main_kb(), parse_mode="HTML")



@dp.message(F.text == '⚙️ Комплектация')
async def info_handler(message: Message):
    info_text = (
        "<b>🏗 ТЕХНИЧЕСКАЯ СПЕЦИФИКАЦИЯ</b>\n"
        "──────────────────────────\n"
        "🤖 <b>Контроллер:</b> <code>Raspberry Pi 3B</code>\n"
        "🔌 <b>Плата управления:</b> <code>Breadboard</code>\n\n"
        "<b>📡 Установленные датчики:</b>\n"
        "• <b>Климат:</b> DHT-22 (Температура и влажность)\n"
        "• <b>Климат почвы:</b> YL-018 (Влажность почвы)\n"
        "• <b>Газ:</b> MQ-135 (Уровень CO2)\n"
        "• <b>Свет:</b> KY-018 (Фоторезистор)\n\n"
        "<b>❄️ Охлаждение:</b> Элемент Пельтье (TEC-1) + активная вентиляция с помощью вентиляторов.\n"
        "<b>💧 Регулировка влажности:</b> Парогенератор\n"
        "──────────────────────────\n"
        "<i>💡 Совет: Не забывайте менять почву для грибов для ускорения роста!</i>"
    )
    await message.answer(info_text, parse_mode="HTML")



@dp.message(F.text == '🎮 Панель управления')
async def control_menu_handler(message: Message):
    l_state = "ВКЛЮЧЕН 🟢" if GPIO.input(LIGHT_PIN) else "ВЫКЛЮЧЕН 🔴"
    s_state = "ВКЛЮЧЕН 🟢" if GPIO.input(STEAM_PIN) else "ВЫКЛЮЧЕН 🔴"
    p_state = "ВЫКЛЮЧЕН 🔴" if not GPIO.input(PELTIER_PIN) else "ВКЛЮЧЕН 🟢"

    await message.answer(
        f"<b>🕹 Управление модулями теплицы</b>\n\n"
        f"Освещение: {l_state}\n"
        f"Увлажнение: {s_state}\n"
        f"Охлаждение: {p_state}",
        reply_markup=devices_inline_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("toggle_"))
async def process_toggle(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]

    if action == "light":
        GPIO.output(LIGHT_PIN, not GPIO.input(LIGHT_PIN))
    elif action == "steam":
        GPIO.output(STEAM_PIN, not GPIO.input(STEAM_PIN))
    elif action == "cooling":
        new_state = not GPIO.input(PELTIER_PIN)
        GPIO.output(PELTIER_PIN, new_state)
        GPIO.output(FAN_PIN, new_state)

    await callback.answer("Состояние изменено!")

    l_state = "ВКЛЮЧЕН 🟢" if GPIO.input(LIGHT_PIN) else "ВЫКЛЮЧЕН 🔴"
    s_state = "ВКЛЮЧЕН 🟢" if GPIO.input(STEAM_PIN) else "ВЫКЛЮЧЕН 🔴"
    p_state = "ВЫКЛЮЧЕН 🔴" if not GPIO.input(PELTIER_PIN) else "ВКЛЮЧЕН 🟢"

    await callback.message.edit_text(
        f"<b>🕹 Управление модулями теплицы</b>\n\n"
        f"Освещение: {l_state}\n"
        f"Увлажнение: {s_state}\n"
        f"Охлаждение: {p_state}",
        reply_markup=devices_inline_kb(),
        parse_mode="HTML"
    )



@dp.message(F.text == '📊 Показатели датчиков')
async def sensors_handler(message: Message):
    last_update = 0
    if os.path.exists(DATA_FILE):
        last_update = os.path.getmtime(DATA_FILE)
    current_time_sec = time.time()
    seconds_passed = current_time_sec - last_update
    if seconds_passed < SCREEN_UPDATE_COOLDOWN:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        remaining = int(SCREEN_UPDATE_COOLDOWN - seconds_passed)
        await message.answer(
            "<b>📊 ПОСЛЕДНИЕ ДАННЫЕ (ЭКРАН ОБНОВЛЯЕТСЯ...)</b>\n"
            f"<i>(Обновление будет доступно через {remaining} сек.)</i>\n"
            "──────────────────────────\n"
            f"🌡 <b>Температура:</b> <code>{data['температура']}°C</code>\n"
            f"💧 <b>Влажность воздуха:</b> <code>{data['влажность']}%</code>\n"
            f"🪴 <b>Влажность почвы:</b> <code>{data['влажность_почвы']}%</code>\n"
            f"🌬 <b>Уровень CO2:</b> <code>{data['co2']} PPM</code>\n"
            f"🌤️ <b>Свет:</b> <code>{data['освещенность']} Lm</code>\n"
            "──────────────────────────\n"
            f"⏰ <b>Время замера:</b> <code>{data['время']}</code>",
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer("⏳ <i>Считываю данные с датчиков...</i>", parse_mode="HTML")
    _, temperature, humidity, moisture_percent, ppm, lux, current_time = await update_sensors_logic()
    moisture_status = moisture_sensor.get_status_text(moisture_percent) if moisture_sensor else "Датчик почвы не подключен"
    
    percent_co2 = ((ppm - 400) / (1500 - 400)) * 100
    percent_co2 = max(0, min(100, percent_co2))

    if ppm < 800: status_co2 = "✅ Воздух отличный"
    elif ppm < 1200: status_co2 = "⚠️ Воздух несвежий, приоткройте окно"
    else: status_co2 = "🚨 СРОЧНО ПРОВЕТРИТЕ! Высокий уровень CO2"

    if lux < 50: lux_status = "🌑 Очень темно"
    elif lux < 450: lux_status = "💡 Обычный комнатный свет"
    else: lux_status = "☀️ Ярко"

    current_time_str = current_time.strftime("%H:%M:%S | %d.%m.%Y")

    report = (
        "<b>📊 ОТЧЕТ О СОСТОЯНИИ</b>\n"
        "──────────────────────────\n"
        f"<b>⏰ Время замера:</b> <code>{current_time_str}</code>\n\n"
        f"🌡 <b>Температура:</b> <code>{temperature if temperature is not None else '--'}°C</code>\n"
        f"💧 <b>Влажность воздуха:</b> <code>{humidity if humidity is not None else '--'}%</code>\n"
        f"🪴 <b>Влажность почвы:</b> <code>{moisture_percent}%</code>\n"
        f"Статус: {moisture_status}\n"
        "──────────────────────────\n"
        f"🌬 <b>Уровень CO2: </b>\n"
        f"Концентрация: <code>{ppm}</code> PPM \n"
        f"Загрязнение: <code>{percent_co2:.1f} %</code> от норма\n"
        f"Статус: {status_co2}\n"
        f"🌤️<b>Свет:</b> <code>{lux} Lm</code>\n"
        f"Статус: {lux_status}\n"
    )
    await status_msg.edit_text(report, parse_mode="HTML")


@dp.message(F.text == '📸 Сделать фото')
async def send_photo_handler(message: Message):
    wait_msg = await message.answer("📸 Пытаюсь сделать снимок...")

    photo_path = "test_shot.jpg"
    exit_code = os.system(f"fswebcam -d /dev/video0 -r 1280x720 --no-banner {photo_path}")
    if exit_code == 0:
        photo = types.FSInputFile(photo_path)
        await message.answer_photo(
            photo,
            caption=f"✅ Тестовый снимок\n⏰ Время: {datetime.datetime.now().strftime('%H:%M:%S')}"
        )
    else:
        await message.answer("❌ Ошибка камеры! Проверь, воткнута ли она в USB.")


# Анкета (FSM)
class Register(StatesGroup):
    name = State()
    model = State()
    mark = State()

@dp.message(F.text == '📝 Заполнить анкету')
async def register_start(message: Message, state: FSMContext):
    await state.set_state(Register.name)
    await message.answer("Шаг 1: Введите ваше <b>имя</b>:", parse_mode="HTML")

@dp.message(Register.name)
async def register_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Register.model)
    await message.answer("Шаг 2: Укажите <b>модель</b> теплицы:", parse_mode="HTML")

@dp.message(Register.model)
async def register_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await state.set_state(Register.mark)
    await message.answer("Шаг 3: Оцените удобство (1-10):", parse_mode="HTML")

@dp.message(Register.mark)
async def register_finish(message: Message, state: FSMContext):
    await state.update_data(mark=message.text)
    data = await state.get_data()
    await message.answer(f"✅ Спасибо, {data['name']}! Данные получены.", reply_markup=main_kb())
    await state.clear()

@dp.message(F.text == '👨‍💻 Поддержка')
async def admin_handler(message: Message):
    await message.answer("☎️Связь с разработчиком:", reply_markup=link_kb())

# Основная функция

async def main():
    asyncio.create_task(background_sensor_monitor())
    ip = get_ip_address()
    try:
        await bot.send_message(admin_id, f"🔌 <b>Питание подано!</b> SmartMushroom успешно запущен.\nIP: <code>{ip}</code>", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение о запуске: {e}")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        GPIO.cleanup()
