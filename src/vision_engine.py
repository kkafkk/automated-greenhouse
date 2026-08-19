import cv2  # Библиотека OpenCV для работы с изображениями
import numpy as np  # Библиотека для работы с массивами и математическими операциями
import os  # Библиотека для работы с операционной системой

def analyze_growth(mode):
    """
    Анализ роста растений и грибов на фотографии.
    Возвращает процент покрытия белыми пикселями (плодовые тела грибов или растения).
    """
    # Путь для сохранения фотографии с камеры
    photo_path = "live_mushrooms.jpg"
    # Съемка фотографии с веб-камеры
    exit_code = os.system(f"fswebcam -d /dev/video0 -r 640x480 --no-banner {photo_path}")

    # Проверка успешности съемки
    if exit_code != 0:
        return None

    # Загрузка изображения
    img = cv2.imread(photo_path)
    # Преобразование изображения в цветовую модель HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Определение диапазона цветов для выделения объектов
    if "Шампиньоны" in mode:
        # Диапазон для шампиньонов (белые плодовые тела)
        lower = np.array([0, 0, 160])
        upper = np.array([180, 40, 255])
    else:
        # Диапазон для других растений и грибов (зеленые части)
        lower = np.array([35, 40, 40])
        upper = np.array([85, 255, 255])

    # Создание маски по заданному диапазону цветов
    mask = cv2.inRange(hsv, lower, upper)
    # Подсчет количества белых пикселей на маске
    white_pixels = cv2.countNonZero(mask)
    # Общее количество пикселей на изображении
    total_pixels = mask.shape[0] * mask.shape[1]

    # Возврат процента покрытия белыми пикселями
    return round((white_pixels / total_pixels) * 100, 2)