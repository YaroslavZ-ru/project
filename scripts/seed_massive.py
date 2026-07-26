"""scripts/seed_massive.py -- масштабное наполнение БД (100+ понятий, 10+ доменов).

Вставляет напрямую в SQLite через KnowledgeBase.compute_concept_embedding.
Запуск: python -m scripts.seed_massive [--force]
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ДАННЫЕ: 120+ понятий по 10+ доменам
# ---------------------------------------------------------------------------

CONCEPTS = [
    # =====================================================================
    # СЛЕСАРНЫЙ ИНСТРУМЕНТ
    # =====================================================================
    {"term": "ключ гаечный", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер под ключ в миллиметрах", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал изготовления ключа"},
        {"name": "torque_nm", "label_ru": "Момент затяжки", "type": "float", "description": "Максимальный крутящий момент", "unit": "Н·м"},
    ]},
    {"term": "ключ разводной", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_range_mm", "label_ru": "Диапазон размеров", "type": "string", "description": "Минимальный и максимальный размер"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал изготовления"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Общая длина ключа", "unit": "мм"},
    ]},
    {"term": "ключ торцевой", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер головки", "unit": "мм"},
        {"name": "drive_type", "label_ru": "Тип привода", "type": "enum", "description": "Форма приводного квадрата", "enum_values": ["крест", "шестигранник", "звёздочка"]},
    ]},
    {"term": "ключ трещёточный", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер головки", "unit": "мм"},
        {"name": "ratchet_mechanism", "label_ru": "Тип трещётки", "type": "string", "description": "Количество зубьев механизма"},
        {"name": "reversible", "label_ru": "Реверсивный", "type": "boolean", "description": "Возможность работы в обратном направлении"},
    ]},
    {"term": "отвёртка", "domain": "слесарный инструмент", "parameters": [
        {"name": "tip_type", "label_ru": "Тип жала", "type": "enum", "description": "Форма рабочей части", "enum_values": ["крест", "плоская", "торкс", "шестигранник"]},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина лезвия", "unit": "мм"},
        {"name": "handle_material", "label_ru": "Материал рукоятки", "type": "string", "description": "Материал и тип рукоятки"},
    ]},
    {"term": "плоскогубцы", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Общая длина", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип плоскогубцев", "enum_values": ["обычные", "тонкогубцы", "бокорезы", "кусачки"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материалjaw"},
    ]},
    {"term": "молоток", "domain": "слесарный инструмент", "parameters": [
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Масса головки молотка", "unit": "кг"},
        {"name": "head_type", "label_ru": "Тип головки", "type": "enum", "description": "Материал и форма головки", "enum_values": ["стальная", "медная", "каучуковая", "пластиковая"]},
        {"name": "handle_material", "label_ru": "Материал рукоятки", "type": "string", "description": "Материал рукоятки"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Общая длина молотка", "unit": "мм"},
    ]},
    {"term": "ножовка", "domain": "слесарный инструмент", "parameters": [
        {"name": "blade_length_mm", "label_ru": "Длина полотна (мм)", "type": "float", "description": "Длина режущего полотна", "unit": "мм"},
        {"name": "teeth_per_inch", "label_ru": "Зубьев на дюйм", "type": "integer", "description": "Частота зубьев пилы"},
        {"name": "material", "label_ru": "Материал полотна", "type": "string", "description": "Материал режущей части"},
    ]},
    {"term": "разводной ключ", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_range_mm", "label_ru": "Диапазон размеров", "type": "string", "description": "Рабочий диапазон"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал изготовления"},
    ]},
    {"term": "кусачки", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Общая длина", "unit": "мм"},
        {"name": "cutting_diameter_mm", "label_ru": "Диаметр реза (мм)", "type": "float", "description": "Максимальный диаметр провода", "unit": "мм"},
    ]},
    {"term": "пассатижи", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Общая длина", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал jaw"},
    ]},

    # =====================================================================
    # ЭЛЕКТРОНИКА
    # =====================================================================
    {"term": "резистор", "domain": "электроника", "parameters": [
        {"name": "resistance_ohm", "label_ru": "Сопротивление (Ом)", "type": "float", "description": "Номинальное сопротивление", "unit": "Ом"},
        {"name": "tolerance_percent", "label_ru": "Допуск (%)", "type": "float", "description": "Допуск сопротивления", "unit": "%"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Рассеиваемая мощность", "unit": "Вт"},
        {"name": "package", "label_ru": "Корпус", "type": "enum", "description": "Тип корпуса", "enum_values": ["SMD", "проводной", "постоянный", "переменный"]},
    ]},
    {"term": "конденсатор", "domain": "электроника", "parameters": [
        {"name": "capacitance_farad", "label_ru": "Ёмкость (Ф)", "type": "float", "description": "Номинальная ёмкость", "unit": "Ф"},
        {"name": "voltage_rating", "label_ru": "Напряжение (В)", "type": "float", "description": "Максимальное рабочее напряжение", "unit": "В"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип диэлектрика", "enum_values": ["керамический", "электролитический", "плёночный", "танталовый"]},
        {"name": "package", "label_ru": "Корпус", "type": "string", "description": "Форм-фактор корпуса"},
    ]},
    {"term": "диод", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип диода", "enum_values": ["выпрямительный", "светоизлучающий", "стабилитрон", "шоттки"]},
        {"name": "forward_voltage", "label_ru": "Прямое напряжение (В)", "type": "float", "description": "Напряжение на выводах при прямом токе", "unit": "В"},
        {"name": "max_current", "label_ru": "Макс. ток (А)", "type": "float", "description": "Максимальный прямой ток", "unit": "А"},
        {"name": "color", "label_ru": "Цвет", "type": "enum", "description": "Цвет свечения (для LED)", "enum_values": ["красный", "зелёный", "синий", "белый", "жёлтый", "RGB"]},
    ]},
    {"term": "светодиод", "domain": "электроника", "parameters": [
        {"name": "color", "label_ru": "Цвет", "type": "enum", "description": "Цвет свечения", "enum_values": ["красный", "зелёный", "синий", "белый", "жёлтый", "RGB"]},
        {"name": "forward_voltage", "label_ru": "Прямое напряжение (В)", "type": "float", "description": "Напряжение на выводах", "unit": "В"},
        {"name": "luminosity_mcd", "label_ru": "Сила света (мкд)", "type": "float", "description": "Яркость свечения", "unit": "мкд"},
        {"name": "wavelength_nm", "label_ru": "Длина волны (нм)", "type": "float", "description": "Длина волны излучения", "unit": "нм"},
    ]},
    {"term": "транзистор", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип транзистора", "enum_values": ["NPN", "PNP", "MOSFET", "JFET"]},
        {"name": "max_voltage", "label_ru": "Макс. напряжение (В)", "type": "float", "description": "Коллектор-эмиттер", "unit": "В"},
        {"name": "max_current", "label_ru": "Макс. ток (А)", "type": "float", "description": "Максимальный коллекторный ток", "unit": "А"},
        {"name": "package", "label_ru": "Корпус", "type": "string", "description": "Тип корпуса"},
    ]},
    {"term": "автоматический выключатель", "domain": "электроника", "parameters": [
        {"name": "current_rating", "label_ru": "Номинальный ток (А)", "type": "float", "description": "Номинальный ток отключения", "unit": "А"},
        {"name": "poles", "label_ru": "Количество полюсов", "type": "integer", "description": "Число полюсов"},
        {"name": "trip_characteristic", "label_ru": "Характеристика отключения", "type": "enum", "description": "Кривая автоматического отключения", "enum_values": ["B", "C", "D", "K"]},
        {"name": "breaking_capacity_ka", "label_ru": "Предельная отключающая способность (кА)", "type": "float", "description": "Максимальный ток КЗ", "unit": "кА"},
    ]},
    {"term": "микроконтроллер", "domain": "электроника", "parameters": [
        {"name": "architecture", "label_ru": "Архитектура", "type": "enum", "description": "Процессорная архитектура", "enum_values": ["ARM Cortex-M", "AVR", "RISC-V", "ESP32"]},
        {"name": "flash_kb", "label_ru": "Flash (КБ)", "type": "float", "description": "Объём.flash-памяти", "unit": "КБ"},
        {"name": "ram_kb", "label_ru": "RAM (КБ)", "type": "float", "description": "Объём оперативной памяти", "unit": "КБ"},
        {"name": "clock_mhz", "label_ru": "Частота (МГц)", "type": "float", "description": "Тактовая частота процессора", "unit": "МГц"},
        {"name": "gpio_count", "label_ru": "Количество GPIO", "type": "integer", "description": "Число программируемых выводов"},
    ]},
    {"term": "розетка", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип розетки", "enum_values": ["европейская", "американская", "универсальная", "с заземлением"]},
        {"name": "current_rating", "label_ru": "Номинальный ток (А)", "type": "float", "description": "Максимальный ток", "unit": "А"},
        {"name": "voltage_rating", "label_ru": "Напряжение (В)", "type": "float", "description": "Номинальное напряжение", "unit": "В"},
        {"name": "mounting", "label_ru": "Монтаж", "type": "enum", "description": "Способ установки", "enum_values": ["скрытый", "открытый", "накладной"]},
    ]},
    {"term": "лампочка", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип лампы", "enum_values": ["накаливания", "галогенная", "светодиодная", "люминесцентная"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Потребляемая мощность", "unit": "Вт"},
        {"name": "lumen", "label_ru": "Световой поток (лм)", "type": "float", "description": "Яркость свечения", "unit": "лм"},
        {"name": "color_temp_k", "label_ru": "Цветовая температура (К)", "type": "float", "description": "Тон свечения", "unit": "К"},
        {"name": "socket_type", "label_ru": "Цоколь", "type": "string", "description": "Тип цоколя"},
    ]},

    # =====================================================================
    # МУЗЫКА
    # =====================================================================
    {"term": "гитара", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип гитары", "enum_values": ["акустическая", "электрогитара", "классическая", "бас-гитара"]},
        {"name": "strings_count", "label_ru": "Количество струн", "type": "integer", "description": "Число струн"},
        {"name": "body_material", "label_ru": "Материал корпуса", "type": "string", "description": "Основной материал корпуса"},
        {"name": "scale_length_mm", "label_ru": "Длина мензуры (мм)", "type": "float", "description": "Рабочая длина струны", "unit": "мм"},
        {"name": "neck_material", "label_ru": "Материал грифа", "type": "string", "description": "Материал и профиль грифа"},
    ]},
    {"term": "пианино", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип пианино", "enum_values": ["вертикальное", "концертное", "цифровое"]},
        {"name": "keys_count", "label_ru": "Количество клавиш", "type": "integer", "description": "Число клавиш"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина инструмента", "unit": "мм"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес инструмента", "unit": "кг"},
        {"name": "finish", "label_ru": "Отделка", "type": "string", "description": "Тип отделки корпуса"},
    ]},
    {"term": "скрипка", "domain": "музыка", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "description": "Размер скрипки", "enum_values": ["4/4", "3/4", "1/2", "1/4"]},
        {"name": "body_material", "label_ru": "Материал корпуса", "type": "string", "description": "Породы дерева"},
        {"name": "strings_count", "label_ru": "Количество струн", "type": "integer", "description": "Число струн (обычно 4)"},
    ]},
    {"term": "ударные", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип ударной установки", "enum_values": ["акустическая", "электронная", "джембэ", "тарелки"]},
        {"name": "pieces_count", "label_ru": "Количество элементов", "type": "integer", "description": "Число барабанов и тарелок"},
        {"name": "material", "label_ru": "Материал корпуса", "type": "string", "description": "Материал корпусов барабанов"},
    ]},
    {"term": "метроном", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип метронома", "enum_values": ["механический", "цифровой", "маятниковый"]},
        {"name": "tempo_range", "label_ru": "Диапазон темпа (уд/мин)", "type": "string", "description": "Диапазон BPM"},
    ]},
    {"term": "нота", "domain": "музыка", "parameters": [
        {"name": "pitch", "label_ru": "Высота звука", "type": "string", "description": "Название ноты"},
        {"name": "duration", "label_ru": "Длительность", "type": "enum", "description": "Размер ноты", "enum_values": ["целая", "половинная", "четвертная", "восьмая", "шестнадцатая"]},
        {"name": "octave", "label_ru": "Октава", "type": "integer", "description": "Номер октавы"},
    ]},
    {"term": "аккорд", "domain": "музыка", "parameters": [
        {"name": "chord_type", "label_ru": "Тип аккорда", "type": "enum", "description": "Вид аккорда", "enum_values": ["мажорный", "минорный", "септаккорд", "диминишутое"]},
        {"name": "root_note", "label_ru": "Основной тон", "type": "string", "description": "Основная нота аккорда"},
    ]},
    {"term": "саксофон", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Разновидность саксофона", "enum_values": ["сопрано", "альт", "тенор", "баритон"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал корпуса"},
        {"name": "keys_material", "label_ru": "Материал клавиш", "type": "string", "description": "Материал механизма"},
    ]},

    # =====================================================================
    # КРЕПЁЖ
    # =====================================================================
    {"term": "болт", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Диаметр резьбы", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина болта", "unit": "мм"},
        {"name": "thread_type", "label_ru": "Тип резьбы", "type": "string", "description": "Метричная, дюймовая"},
        {"name": "strength_class", "label_ru": "Класс прочности", "type": "string", "description": "Класс прочности (8.8, 10.9, 12.9)"},
        {"name": "head_type", "label_ru": "Тип головки", "type": "enum", "description": "Форма головки", "enum_values": ["шестигранник", "круглая", "потай", "полукруглая"]},
    ]},
    {"term": "гайка", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер под ключ", "unit": "мм"},
        {"name": "thread_type", "label_ru": "Тип резьбы", "type": "string", "description": "Метрическая или дюймовая"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид гайки", "enum_values": ["обычная", "барашковая", "корончатая", "стопорная"]},
    ]},
    {"term": "саморез", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Диаметр и длина", "unit": "мм"},
        {"name": "head_type", "label_ru": "Тип головки", "type": "enum", "description": "Форма шляпки", "enum_values": ["потай", "полукруглая", "шестигранник"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал самореза"},
    ]},
    {"term": "шуруп", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Диаметр и длина", "unit": "мм"},
        {"name": "tip_type", "label_ru": "Тип наконечника", "type": "enum", "description": "Форма наконечника", "enum_values": ["острый", "сверло", "конусный"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал шурупа"},
    ]},
    {"term": "дюбель", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Диаметр и глубина", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид дюбеля", "enum_values": ["пластиковый", "металлический", "химический", "распорный"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал корпуса"},
    ]},
    {"term": "анкер", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Диаметр и длина", "unit": "мм"},
        {"name": "load_capacity_kg", "label_ru": "Нагрузка (кг)", "type": "float", "description": "Максимальная нагрузка на отрыв", "unit": "кг"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип анкера", "enum_values": ["клинковый", "химический", "забивной", "рамный"]},
    ]},
    {"term": "стяжка", "domain": "крепёж", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина стяжки", "unit": "мм"},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "description": "Ширина ленты", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал (нейлон, металл)"},
    ]},
    {"term": "хомут", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр трубы", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип хомута", "enum_values": ["пластиковый", "металлический", " быстросъемный"]},
    ]},

    # =====================================================================
    # СТРОИТЕЛЬСТВО
    # =====================================================================
    {"term": "кирпич", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид кирпича", "enum_values": ["красный", "силикатный", "керамический", "огнеупорный"]},
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "string", "description": "Габариты (длина x ширина x высота)"},
        {"name": "strength_mpa", "label_ru": "Прочность (МПа)", "type": "float", "description": "Предел прочности на сжатие", "unit": "МПа"},
        {"name": "density_kg_m3", "label_ru": "Плотность (кг/м³)", "type": "float", "description": "Объёмная плотность", "unit": "кг/м³"},
        {"name": "thermal_conductivity", "label_ru": "Теплопроводность (Вт/м·К)", "type": "float", "description": "Коэффициент теплопроводности", "unit": "Вт/м·К"},
    ]},
    {"term": "бетон", "domain": "строительство", "parameters": [
        {"name": "grade", "label_ru": "Марка", "type": "string", "description": "Класс прочности (B10, B15, B25)"},
        {"name": "slump_cm", "label_ru": "Осадка конуса (см)", "type": "float", "description": "Подвижность смеси", "unit": "см"},
        {"name": "density_kg_m3", "label_ru": "Плотность (кг/м³)", "type": "float", "description": "Объёмная плотность", "unit": "кг/м³"},
        {"name": "strength_mpa", "label_ru": "Прочность (МПа)", "type": "float", "description": "Предел прочности на сжатие", "unit": "МПа"},
    ]},
    {"term": "арматура", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр стержня", "unit": "мм"},
        {"name": "grade", "label_ru": "Марка стали", "type": "string", "description": "Класс арматурной стали (A400, A500)"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина стержня", "unit": "м"},
    ]},
    {"term": "утеплитель", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид утеплителя", "enum_values": ["минеральная вата", "пенопласт", "экструдированный пенополистирол", "пеноизол"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "description": "Толщина плиты", "unit": "мм"},
        {"name": "thermal_conductivity", "label_ru": "Теплопроводность (Вт/м·К)", "type": "float", "description": "Коэффициент теплопроводности", "unit": "Вт/м·К"},
        {"name": "density_kg_m3", "label_ru": "Плотность (кг/м³)", "type": "float", "description": "Плотность материала", "unit": "кг/м³"},
    ]},
    {"term": "гипсокартон", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид ГКЛ", "enum_values": ["обычный", "влагостойкий", "огнеупорный", "влагоогнеупорный"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "description": "Толщина листа", "unit": "мм"},
        {"name": "dimensions_mm", "label_ru": "Габариты (мм)", "type": "string", "description": "Длина x Ширина"},
    ]},
    {"term": "плитка", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид плитки", "enum_values": ["керамическая", "керамогранит", "мозаика", "стеклянная"]},
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "string", "description": "Длина x Ширина"},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "description": "Толщина плитки", "unit": "мм"},
        {"name": "class", "label_ru": "Класс", "type": "enum", "description": "Класс износостойкости", "enum_values": ["PEI I", "PEI II", "PEI III", "PEI IV", "PEI V"]},
    ]},
    {"term": "труба", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Наружный диаметр", "unit": "мм"},
        {"name": "thickness_mm", "label_ru": "Толщина стенки (мм)", "type": "float", "description": "Толщина стенки", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал трубы"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина трубы", "unit": "м"},
    ]},

    # =====================================================================
    # БЫТОВАЯ ТЕХНИКА
    # =====================================================================
    {"term": "холодильник", "domain": "бытовая техника", "parameters": [
        {"name": "total_volume_l", "label_ru": "Общий объём (л)", "type": "float", "description": "Суммарный объём камер", "unit": "л"},
        {"name": "freezer_volume_l", "label_ru": "Объём морозильника (л)", "type": "float", "description": "Объём морозильной камеры", "unit": "л"},
        {"name": "energy_class", "label_ru": "Класс энергоэффективности", "type": "enum", "description": "Класс по энергопотреблению", "enum_values": ["A+++", "A++", "A+", "A", "B"]},
        {"name": "dimensions_mm", "label_ru": "Габариты (мм)", "type": "string", "description": "Высота x Ширина x Глубина"},
        {"name": "noise_level_db", "label_ru": "Уровень шума (дБ)", "type": "float", "description": "Уровень шума при работе", "unit": "дБ"},
    ]},
    {"term": "стиральная машина", "domain": "бытовая техника", "parameters": [
        {"name": "load_capacity_kg", "label_ru": "Загрузка (кг)", "type": "float", "description": "Максимальная загрузка белья", "unit": "кг"},
        {"name": "spin_speed_rpm", "label_ru": "Скорость отжима (об/мин)", "type": "integer", "description": "Максимальные обороты отжима"},
        {"name": "energy_class", "label_ru": "Класс энергоэффективности", "type": "enum", "description": "Класс по энергопотреблению", "enum_values": ["A+++", "A++", "A+", "A"]},
        {"name": "noise_level_db", "label_ru": "Уровень шума стирки (дБ)", "type": "float", "description": "Уровень шума при стирке", "unit": "дБ"},
        {"name": "dimensions_mm", "label_ru": "Габариты (мм)", "type": "string", "description": "Высота x Ширина x Глубина"},
    ]},
    {"term": "пылесос", "domain": "бытовая техника", "parameters": [
        {"name": "suction_power_airw", "label_ru": "Мощность всасывания (Вт)", "type": "float", "description": "Реальная мощность всасывания", "unit": "Вт"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Потребляемая мощность", "unit": "Вт"},
        {"name": "dust_container_l", "label_ru": "Объём пылесборника (л)", "type": "float", "description": "Ёмкость контейнера для пыли", "unit": "л"},
        {"name": "noise_level_db", "label_ru": "Уровень шума (дБ)", "type": "float", "description": "Уровень шума при работе", "unit": "дБ"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип пылесоса", "enum_values": ["вертикальный", "робот", "классический", "аквафильтр"]},
    ]},
    {"term": "кофемашина", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип кофемашины", "enum_values": ["капсульная", "капельная", "эспрессо", "автоматическая"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Потребляемая мощность", "unit": "Вт"},
        {"name": "pressure_bar", "label_ru": "Давление (бар)", "type": "float", "description": "Давление помпы", "unit": "бар"},
        {"name": "water_tank_ml", "label_ru": "Объём резервуара (мл)", "type": "float", "description": "Ёмкость бака для воды", "unit": "мл"},
        {"name": "grinder", "label_ru": "Встроенная кофемолка", "type": "boolean", "description": "Наличие встроенной кофемолки"},
    ]},
    {"term": "микроволновка", "domain": "бытовая техника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Мощность СВЧ-излучения", "unit": "Вт"},
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Объём камеры", "unit": "л"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип управления", "enum_values": ["механическое", "электронное", "сенсорное"]},
    ]},
    {"term": "чайник", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Объём чайника", "unit": "л"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Мощность нагрева", "unit": "Вт"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал корпуса"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип чайника", "enum_values": ["электрический", "обычный", "с термоподставкой"]},
    ]},

    # =====================================================================
    # ТРАНСПОРТ
    # =====================================================================
    {"term": "автомобиль", "domain": "транспорт", "parameters": [
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "description": "Рабочий объём двигателя", "unit": "л"},
        {"name": "power_hp", "label_ru": "Мощность (л.с.)", "type": "float", "description": "Мощность двигателя", "unit": "л.с."},
        {"name": "fuel_type", "label_ru": "Тип топлива", "type": "enum", "description": "Вид топлива", "enum_values": ["бензин", "дизель", "электро", "гибрид"]},
        {"name": "dimensions_mm", "label_ru": "Габариты (мм)", "type": "string", "description": "Длина x Ширина x Высота"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Снаряжённая масса", "unit": "кг"},
    ]},
    {"term": "велосипед", "domain": "транспорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип велосипеда", "enum_values": ["горный", "шоссейный", "городской", "BMX", "электро"]},
        {"name": "wheel_size", "label_ru": "Размер колёс", "type": "string", "description": "Диаметр колёс (дюймы)"},
        {"name": "gears_count", "label_ru": "Количество передач", "type": "integer", "description": "Число скоростей"},
        {"name": "frame_size", "label_ru": "Размер рамы", "type": "string", "description": "Размер рамы (дюймы или см)"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес велосипеда", "unit": "кг"},
    ]},
    {"term": "мопед", "domain": "транспорт", "parameters": [
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "description": "Рабочий объём", "unit": "л"},
        {"name": "power_hp", "label_ru": "Мощность (л.с.)", "type": "float", "description": "Мощность двигателя", "unit": "л.с."},
        {"name": "max_speed_kmh", "label_ru": "Макс. скорость (км/ч)", "type": "float", "description": "Максимальная скорость", "unit": "км/ч"},
    ]},
    {"term": "скутер", "domain": "транспорт", "parameters": [
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "description": "Рабочий объём", "unit": "л"},
        {"name": "wheel_size", "label_ru": "Размер колёс", "type": "string", "description": "Диаметр колёс"},
        {"name": "fuel_type", "label_ru": "Тип топлива", "type": "enum", "description": "Вид топлива", "enum_values": ["бензин", "электро"]},
    ]},

    # =====================================================================
    # МЕБЕЛЬ
    # =====================================================================
    {"term": "стол", "domain": "мебель", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Назначение стола", "enum_values": ["обеденный", "письменный", "журнальный", "компьютерный", "кухонный", "консольный", "трансформер"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "description": "Основной материал изготовления", "enum_values": ["дерево", "металл", "пластик", "стекло", "камень", "композит"]},
        {"name": "wood_type", "label_ru": "Порода дерева", "type": "enum", "description": "Порода древесины для деревянных столов", "enum_values": ["сосна", "ель", "дуб", "бук", "ясень", "орех", "вишня", "клен", "тик"]},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "description": "Ширина столешницы", "unit": "мм"},
        {"name": "depth_mm", "label_ru": "Глубина (мм)", "type": "float", "description": "Глубина столешницы", "unit": "мм"},
        {"name": "height_mm", "label_ru": "Высота (мм)", "type": "float", "description": "Высота стола от пола до столешницы", "unit": "мм"},
        {"name": "shape", "label_ru": "Форма столешницы", "type": "enum", "description": "Геометрическая форма столешницы", "enum_values": ["прямоугольная", "квадратная", "круглая", "овальная", "угловая", "трапециевидная"]},
        {"name": "coating", "label_ru": "Покрытие", "type": "enum", "description": "Тип защитно-декоративного покрытия", "enum_values": ["лак", "масло", "воск", "полиуретан", "шлифовка", "без покрытия"]},
        {"name": "load_capacity_kg", "label_ru": "Нагрузка (кг)", "type": "float", "description": "Максимальная допустимая нагрузка на столешницу", "unit": "кг"},
        {"name": "wood_grade", "label_ru": "Класс древесины", "type": "enum", "description": "Сортность древесины", "enum_values": ["A", "B", "C", "Extra", "Prime"]},
        {"name": "moisture_resistance", "label_ru": "Влагостойкость", "type": "enum", "description": "Устойчивость к воздействию влаги", "enum_values": ["низкая", "средняя", "высокая", "водостойкая"]},
        {"name": "foldable", "label_ru": "Складной", "type": "boolean", "description": "Возможность складывания стола"},
        {"name": "extendable", "label_ru": "Раздвижной", "type": "boolean", "description": "Возможность увеличения размера столешницы"},
    ]},
    {"term": "стул", "domain": "мебель", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип стула", "enum_values": ["столярный", "офисный", "кресло", "барный", "складной", "детский", "вантуз"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "description": "Основной материал", "enum_values": ["дерево", "металл", "пластик", "стеклопластик"]},
        {"name": "seat_height_mm", "label_ru": "Высота сиденья (мм)", "type": "float", "description": "Высота от пола до сиденья", "unit": "мм"},
        {"name": "seat_width_mm", "label_ru": "Ширина сиденья (мм)", "type": "float", "description": "Ширина посадочного места", "unit": "мм"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес стула", "unit": "кг"},
        {"name": "load_capacity_kg", "label_ru": "Нагрузка (кг)", "type": "float", "description": "Максимальная допустимая нагрузка", "unit": "кг"},
        {"name": "backrest", "label_ru": "Спинка", "type": "boolean", "description": "Наличие спинки"},
        {"name": "armrests", "label_ru": "Подлокотники", "type": "boolean", "description": "Наличие подлокотников"},
    ]},
    {"term": "шкаф", "domain": "мебель", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип шкафа", "enum_values": ["встроенный", "отдельностоящий", "шкаф-купе", "стеллаж"]},
        {"name": "dimensions_mm", "label_ru": "Габариты (мм)", "type": "string", "description": "Высота x Ширина x Глубина"},
        {"name": "doors_count", "label_ru": "Количество дверей", "type": "integer", "description": "Число дверец"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал корпуса"},
    ]},
    {"term": "кровать", "domain": "мебель", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер спального места (см)"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип кровати", "enum_values": ["односпальная", "двухспальная", "двухъярусная", "выдвижная"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал каркаса"},
        {"name": "has_mechanism", "label_ru": "Подъёмный механизм", "type": "boolean", "description": "Наличие подъёмного механизма"},
    ]},
    {"term": "диван", "domain": "мебель", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип дивана", "enum_values": ["прямой", "угловой", "модульный", "выкатной"]},
        {"name": "sleep_mechanism", "label_ru": "Механизм трансформации", "type": "enum", "description": "Тип раскладывания", "enum_values": ["еврокнижка", "пантограф", "дельфин", "аккордеон"]},
        {"name": "seat_depth_mm", "label_ru": "Глубина сиденья (мм)", "type": "float", "description": "Глубина посадочного места", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Обивочный материал"},
    ]},
    {"term": "комод", "domain": "мебель", "parameters": [
        {"name": "drawers_count", "label_ru": "Количество ящиков", "type": "integer", "description": "Число выдвижных ящиков"},
        {"name": "dimensions_mm", "label_ru": "Габариты (мм)", "type": "string", "description": "Высота x Ширина x Глубина"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал корпуса"},
    ]},

    # =====================================================================
    # СПОРТ
    # =====================================================================
    {"term": "мяч", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид спорта", "enum_values": ["футбольный", "баскетбольный", "волейбольный", "теннисный", "гольф"]},
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр мяча", "unit": "мм"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес мяча", "unit": "кг"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал покрытия"},
    ]},
    {"term": "ракетка", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид спорта", "enum_values": ["теннисная", "настольный теннис", "бадминтон", "сквош"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Вес ракетки", "unit": "г"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина ракетки", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал рамы"},
    ]},
    {"term": "лыжи", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип лыж", "enum_values": ["беговые", "горные", "сноуборд"]},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина лыжи", "unit": "мм"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес пары лыж", "unit": "кг"},
        {"name": "radius_mm", "label_ru": "Радиус (мм)", "type": "float", "description": "Радиус бокового выреза", "unit": "мм"},
    ]},
    {"term": "велосипед спортивный", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип велосипеда", "enum_values": ["шоссейный", "горный", "triathlon", "BMX"]},
        {"name": "frame_material", "label_ru": "Материал рамы", "type": "string", "description": "Карбон, алюминий, сталь"},
        {"name": "gears_count", "label_ru": "Количество передач", "type": "integer", "description": "Число скоростей"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес велосипеда", "unit": "кг"},
    ]},
    {"term": "шлем", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Назначение шлема", "enum_values": ["велосипедный", "лыжный", "мотоциклетный", "скальный"]},
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Обхват головы (см)"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал оболочки"},
        {"name": "ventilation", "label_ru": "Вентиляция", "type": "boolean", "description": "Наличие вентиляционных отверстий"},
    ]},

    # =====================================================================
    # ОДЕЖДА
    # =====================================================================
    {"term": "куртка", "domain": "одежда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип куртки", "enum_values": ["зимняя", "демисезонная", "ветровка", "кожаная", "джинсовая"]},
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер (S, M, L, XL)"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Основной материал"},
        {"name": "filling", "label_ru": "Утеплитель", "type": "string", "description": "Тип утеплителя"},
    ]},
    {"term": "джинсы", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер (RUS/EU)"},
        {"name": "fit", "label_ru": "Крой", "type": "enum", "description": "Тип кроя", "enum_values": ["skinny", "slim", "regular", "relaxed", "bootcut"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Состав ткани"},
        {"name": "color", "label_ru": "Цвет", "type": "string", "description": "Цвет джинсов"},
    ]},
    {"term": "футболка", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер (S, M, L, XL)"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Состав ткани"},
        {"name": "color", "label_ru": "Цвет", "type": "string", "description": "Цвет футболки"},
        {"name": "sleeve_type", "label_ru": "Тип рукава", "type": "enum", "description": "Длина рукава", "enum_values": ["короткий", "длинный", "без рукавов"]},
    ]},
    {"term": "обувь", "domain": "одежда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип обуви", "enum_values": ["кроссовки", "ботинки", "туфли", "сандалии", "сапоги"]},
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер (EU/US)"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал верха"},
        {"name": "sole_material", "label_ru": "Материал подошвы", "type": "string", "description": "Материал подошвы"},
    ]},

    # =====================================================================
    # ЕДА И НАПИТКИ
    # =====================================================================
    {"term": "кофе", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид кофе", "enum_values": ["арабика", "робуста", "смесь", "молотый", "в зёрнах"]},
        {"name": "roast", "label_ru": "Обжарка", "type": "enum", "description": "Степень обжарки", "enum_values": ["светлая", "средняя", "тёмная"]},
        {"name": "origin", "label_ru": "Страна происхождения", "type": "string", "description": "Страна выращивания"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Масса упаковки", "unit": "г"},
    ]},
    {"term": "чай", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид чая", "enum_values": ["чёрный", "зелёный", "белый", "oolong", "травяной"]},
        {"name": "form", "label_ru": "Форма", "type": "enum", "description": "Форма выпуска", "enum_values": ["рассыпной", "в пакетиках", "брикетный"]},
        {"name": "origin", "label_ru": "Страна происхождения", "type": "string", "description": "Страна производства"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Масса упаковки", "unit": "г"},
    ]},
    {"term": "шоколад", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид шоколада", "enum_values": ["тёмный", "молочный", "белый"]},
        {"name": "cocoa_percent", "label_ru": "Процент какао", "type": "float", "description": "Содержание какао-массы", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Масса плитки", "unit": "г"},
        {"name": "filling", "label_ru": "Начинка", "type": "string", "description": "Тип начинки"},
    ]},
    {"term": "молоко", "domain": "еда", "parameters": [
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "description": "Процент жирности", "unit": "%"},
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Объём упаковки", "unit": "л"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид молока", "enum_values": ["пастеризованное", "ультрапастеризованное", "сгущённое"]},
    ]},
    {"term": "хлеб", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид хлеба", "enum_values": ["белый", "чёрный", "цельнозерновой", "батон", "буханка"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Масса буханки", "unit": "г"},
        {"name": "ingredients", "label_ru": "Состав", "type": "string", "description": "Основные ингредиенты"},
    ]},

    # =====================================================================
    # ЖИВОТНЫЕ
    # =====================================================================
    {"term": "собака", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string", "description": "Порода собаки"},
        {"name": "size", "label_ru": "Размер", "type": "enum", "description": "Размерная категория", "enum_values": ["маленькая", "средняя", "большая"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес собаки", "unit": "кг"},
        {"name": "life_expectancy_years", "label_ru": "Продолжительность жизни (лет)", "type": "integer", "description": "Средняя продолжительность жизни"},
    ]},
    {"term": "кошка", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string", "description": "Порода кошки"},
        {"name": "color", "label_ru": "Окрас", "type": "string", "description": "Окрас шерсти"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес кошки", "unit": "кг"},
        {"name": "life_expectancy_years", "label_ru": "Продолжительность жизни (лет)", "type": "integer", "description": "Средняя продолжительность жизни"},
    ]},
    {"term": "рыба", "domain": "животные", "parameters": [
        {"name": "species", "label_ru": "Вид", "type": "string", "description": "Вид рыбы"},
        {"name": "habitat", "label_ru": "Среда обитания", "type": "enum", "description": "Тип воды", "enum_values": ["пресная", "морская", "аквариумная"]},
        {"name": "length_cm", "label_ru": "Длина (см)", "type": "float", "description": "Длина тела", "unit": "см"},
    ]},
    {"term": "птица", "domain": "животные", "parameters": [
        {"name": "species", "label_ru": "Вид", "type": "string", "description": "Вид птицы"},
        {"name": "wingspan_cm", "label_ru": "Размах крыльев (см)", "type": "float", "description": "Размах крыльев", "unit": "см"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес птицы", "unit": "кг"},
    ]},

    # =====================================================================
    # МЕДИЦИНА
    # =====================================================================
    {"term": "термометр", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид термометра", "enum_values": ["электронный", "ртутный", "инфракрасный", "пластиковый"]},
        {"name": "measurement_range", "label_ru": "Диапазон измерения", "type": "string", "description": "Градусы Цельсия"},
        {"name": "accuracy", "label_ru": "Точность", "type": "float", "description": "Погрешность измерения", "unit": "°C"},
    ]},
    {"term": "бинт", "domain": "медицина", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "description": "Ширина бинта", "unit": "мм"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина бинта", "unit": "м"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал (хлопок, эластичный)"},
    ]},
    {"term": "шприц", "domain": "медицина", "parameters": [
        {"name": "volume_ml", "label_ru": "Объём (мл)", "type": "float", "description": "Объём шприца", "unit": "мл"},
        {"name": "needle_gauge", "label_ru": "Диаметр иглы", "type": "string", "description": "Калибр иглы (G)"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип шприца", "enum_values": ["одноразовый", "инсулиновый", "перфузорный"]},
    ]},
    {"term": "пластырь", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид пластыря", "enum_values": ["бактерицидный", "специальный", "широкий", "хирургический"]},
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "string", "description": "Длина x Ширина"},
        {"name": "quantity", "label_ru": "Количество", "type": "integer", "description": "Число штук в упаковке"},
    ]},

    # =====================================================================
    # ОБОРУДОВАНИЕ
    # =====================================================================
    {"term": "сверло", "domain": "оборудование", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр сверла", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал (HSS, победит, алмаз)"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Рабочая длина", "unit": "мм"},
        {"name": "shank_type", "label_ru": "Тип хвостовика", "type": "enum", "description": "Тип крепления", "enum_values": ["цилиндрический", "SDS-plus", "SDS-max", "шестигранник"]},
    ]},
    {"term": "перфоратор", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Потребляемая мощность", "unit": "Вт"},
        {"name": "max_drill_mm", "label_ru": "Макс. диаметр сверления (мм)", "type": "float", "description": "Максимальный диаметр в бетоне", "unit": "мм"},
        {"name": "impact_energy_j", "label_ru": "Энергия удара (Дж)", "type": "float", "description": "Энергия ударного механизма", "unit": "Дж"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес перфоратора", "unit": "кг"},
    ]},
    {"term": "болгарка", "domain": "оборудование", "parameters": [
        {"name": "disc_diameter_mm", "label_ru": "Диаметр диска (мм)", "type": "float", "description": "Максимальный диаметр отрезного диска", "unit": "мм"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Потребляемая мощность", "unit": "Вт"},
        {"name": "speed_rpm", "label_ru": "Скорость (об/мин)", "type": "integer", "description": "Число оборотов"},
    ]},
    {"term": "лазерный уровень", "domain": "оборудование", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип уровня", "enum_values": ["точечный", "линейный", "ротационный", "комбинированный"]},
        {"name": "accuracy_mm", "label_ru": "Точность (мм)", "type": "float", "description": "Погрешность на 10м", "unit": "мм"},
        {"name": "range_m", "label_ru": "Дальность (м)", "type": "float", "description": "Радиус действия", "unit": "м"},
    ]},
    {"term": "генератор", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Номинальная мощность", "unit": "Вт"},
        {"name": "fuel_type", "label_ru": "Тип топлива", "type": "enum", "description": "Вид топлива", "enum_values": ["бензин", "дизель", "газ"]},
        {"name": "voltage", "label_ru": "Напряжение (В)", "type": "float", "description": "Выходное напряжение", "unit": "В"},
        {"name": "noise_level_db", "label_ru": "Уровень шума (дБ)", "type": "float", "description": "Уровень шума", "unit": "дБ"},
    ]},

    # =====================================================================
    # НОВЫЕ ПОНЯТИЯ (добавлены для расширения базы)
    # =====================================================================

    # --- МЕБЕЛЬ ---
    {"term": "стул офисный", "domain": "мебель", "parameters": [
        {"name": "seat_height_mm", "label_ru": "Высота сиденья (мм)", "type": "float", "description": "Регулируемая высота", "unit": "мм"},
        {"name": "load_capacity_kg", "label_ru": "Нагрузка (кг)", "type": "float", "description": "Максимальная нагрузка", "unit": "кг"},
        {"name": "backrest", "label_ru": "Спинка", "type": "boolean", "description": "Наличие регулируемой спинки"},
        {"name": "armrests", "label_ru": "Подлокотники", "type": "boolean", "description": "Наличие подлокотников"},
    ]},
    {"term": "кровать", "domain": "мебель", "parameters": [
        {"name": "size", "label_ru": "Размер спального места", "type": "enum", "description": "Стандартный размер", "enum_values": ["90x200", "120x200", "140x200", "160x200", "180x200"]},
        {"name": "material", "label_ru": "Материал каркаса", "type": "string", "description": "Материал каркаса"},
        {"name": "storage", "label_ru": "Ящик для белья", "type": "boolean", "description": "Наличие выдвижного ящика"},
    ]},
    {"term": "диван", "domain": "мебель", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип дивана", "enum_values": ["прямой", "угловой", "выкатной", "раскладной"]},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Общая длина", "unit": "мм"},
        {"name": "upholstery", "label_ru": "Обивка", "type": "string", "description": "Материал обивки"},
    ]},

    # --- СТРОИТЕЛЬСТВО ---
    {"term": "кирпич", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид кирпича", "enum_values": ["силикатный", "керамический", "гиперпрессованный"]},
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "string", "description": "Длина x Ширина x Высота"},
        {"name": "strength_mpa", "label_ru": "Прочность (МПа)", "type": "float", "description": "Марка прочности", "unit": "МПа"},
    ]},
    {"term": "бетон", "domain": "строительство", "parameters": [
        {"name": "grade", "label_ru": "Марка", "type": "enum", "description": "Класс прочности", "enum_values": ["М100", "М150", "М200", "М250", "М300", "М350", "М400"]},
        {"name": "slump_cm", "label_ru": "Подвижность (см)", "type": "float", "description": "Осадка конуса", "unit": "см"},
    ]},

    # --- ЭЛЕКТРОНИКА ---
    {"term": "аккумулятор", "domain": "электроника", "parameters": [
        {"name": "capacity_mah", "label_ru": "Ёмкость (мАч)", "type": "float", "description": "Ёмкость аккумулятора", "unit": "мАч"},
        {"name": "voltage", "label_ru": "Напряжение (В)", "type": "float", "description": "Номинальное напряжение", "unit": "В"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип элементов", "enum_values": ["Li-Ion", "Li-Po", "NiMH", "NiCd"]},
    ]},
    {"term": "микроконтроллер", "domain": "электроника", "parameters": [
        {"name": "architecture", "label_ru": "Архитектура", "type": "enum", "description": "Архитектура ядра", "enum_values": ["ARM", "AVR", "RISC-V", "ESP32"]},
        {"name": "flash_kb", "label_ru": "Flash (КБ)", "type": "float", "description": "Объём флеш-памяти", "unit": "КБ"},
        {"name": "clock_mhz", "label_ru": "Частота (МГц)", "type": "float", "description": "Тактовая частота", "unit": "МГц"},
    ]},

    # --- ТРАНСПОРТ ---
    {"term": "велосипед", "domain": "транспорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип велосипеда", "enum_values": ["горный", "шоссейный", "городской", "BMX", "электро"]},
        {"name": "wheel_size", "label_ru": "Диаметр колёс", "type": "enum", "description": "Размер колёс", "enum_values": ["20", "24", "26", "27.5", "29"]},
        {"name": "gears", "label_ru": "Количество передач", "type": "integer", "description": "Число скоростей"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес велосипеда", "unit": "кг"},
    ]},
    {"term": "автомобиль", "domain": "транспорт", "parameters": [
        {"name": "body_type", "label_ru": "Тип кузова", "type": "enum", "description": "Форма кузова", "enum_values": ["седан", "хэтчбек", "универсал", "кроссовер", "минивэн"]},
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "description": "Рабочий объём", "unit": "л"},
        {"name": "power_hp", "label_ru": "Мощность (л.с.)", "type": "float", "description": "Мощность двигателя", "unit": "л.с."},
    ]},

    # --- СПОРТ ---
    {"term": "беговые кроссовки", "domain": "спорт", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "EU размер"},
        {"name": "drop_mm", "label_ru": "Дроп (мм)", "type": "float", "description": "Перепад высоты", "unit": "мм"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Вес пары", "unit": "г"},
    ]},
    {"term": "штанга", "domain": "спорт", "parameters": [
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина штанги", "unit": "м"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Масса штанги", "unit": "кг"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип штанги", "enum_values": ["олимпийская", "классическая", "-trap-bar"]},
    ]},

    # --- ОДЕЖДА ---
    {"term": "зимняя куртка", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер одежды"},
        {"name": "fill_type", "label_ru": "Утеплитель", "type": "enum", "description": "Тип утеплителя", "enum_values": ["пух", "синтепон", "мембрана", "淑羊毛"]},
        {"name": "waterproof", "label_ru": "Водонепроницаемость", "type": "boolean", "description": "Наличие мембраны"},
    ]},

    # --- ЕДА ---
    {"term": "кофе", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид кофе", "enum_values": ["арабика", "робуста", "смесь"]},
        {"name": "roast", "label_ru": "Обжарка", "type": "enum", "description": "Степень обжарки", "enum_values": ["светлая", "средняя", "тёмная"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Масса упаковки", "unit": "г"},
    ]},
    {"term": "шоколад", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид шоколада", "enum_values": ["тёмный", "молочный", "белый"]},
        {"name": "cocoa_percent", "label_ru": "Какао (%)", "type": "float", "description": "Содержание какао-бобов", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Масса плитки", "unit": "г"},
    ]},

    # --- ЖИВОТНЫЕ ---
    {"term": "лабрадор", "domain": "животные", "parameters": [
        {"name": "color", "label_ru": "Окрас", "type": "enum", "description": "Цвет шерсти", "enum_values": ["чёрный", "жёлтый", "шоколадный"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Взрослая масса", "unit": "кг"},
        {"name": "lifespan_years", "label_ru": "Продолжительность жизни (лет)", "type": "float", "description": "Средняя продолжительность", "unit": "лет"},
    ]},
    {"term": "метис", "domain": "животные", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "description": "Группа размера", "enum_values": ["малый", "средний", "крупный"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Примерная масса", "unit": "кг"},
    ]},

    # --- МЕДИЦИНА ---
    {"term": "термометр", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид термометра", "enum_values": ["ртутный", "электронный", "инфракрасный"]},
        {"name": "range_c", "label_ru": "Диапазон (°C)", "type": "string", "description": "Измеряемый диапазон"},
        {"name": "accuracy_c", "label_ru": "Точность (°C)", "type": "float", "description": "Погрешность измерения", "unit": "°C"},
    ]},

    # --- БЫТОВАЯ ТЕХНИКА ---
    {"term": "холодильник", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Общий объём", "unit": "л"},
        {"name": "energy_class", "label_ru": "Класс энергоэффективности", "type": "enum", "description": "Класс A-G", "enum_values": ["A+++", "A++", "A+", "A", "B"]},
        {"name": "noise_db", "label_ru": "Уровень шума (дБ)", "type": "float", "description": "Уровень шума", "unit": "дБ"},
    ]},
    {"term": "стиральная машина", "domain": "бытовая техника", "parameters": [
        {"name": "load_kg", "label_ru": "Загрузка (кг)", "type": "float", "description": "Максимальная загрузка", "unit": "кг"},
        {"name": "spin_rpm", "label_ru": "Отжим (об/мин)", "type": "integer", "description": "Максимальные обороты"},
        {"name": "energy_class", "label_ru": "Класс энергоэффективности", "type": "enum", "description": "Класс A-G", "enum_values": ["A+++", "A++", "A+", "A", "B"]},
    ]},

    # =====================================================================
    # ДОПОЛНИТЕЛЬНЫЕ ПОНЯТИЯ (расширение базы)
    # =====================================================================

    # --- СЛЕСАРНЫЙ ИНСТРУМЕНТ (дополнительно) ---
    {"term": "гаечный ключ", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер под гайку", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал изготовления"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип ключа", "enum_values": ["рожковый", "накидной", "комбинированный", "торцевой"]},
    ]},
    {"term": "рожковый ключ", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер рожков", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал"},
    ]},
    {"term": "накидной ключ", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер", "unit": "мм"},
        {"name": "ratchet", "label_ru": "Трещётка", "type": "boolean", "description": "Наличие трещётки"},
    ]},
    {"term": "торцевой ключ", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "description": "Размер головки", "unit": "мм"},
        {"name": "drive_type", "label_ru": "Тип привода", "type": "enum", "description": "Привод", "enum_values": ["1/4", "3/8", "1/2", "3/4", "1"]},
    ]},
    {"term": "набор ключей", "domain": "слесарный инструмент", "parameters": [
        {"name": "count", "label_ru": "Количество", "type": "integer", "description": "Число ключей в наборе"},
        {"name": "size_range", "label_ru": "Диапазон размеров", "type": "string", "description": "Мин-макс размер"},
    ]},
    {"term": "шарнирно-губцевый инструмент", "domain": "слесарный инструмент", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид инструмента", "enum_values": ["кусачки", "пассатижи", "бокорезы", "тонкогубцы"]},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Общая длина", "unit": "мм"},
    ]},
    {"term": "кусачки электрика", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина", "unit": "мм"},
        {"name": "cutting_diameter", "label_ru": "Диаметр реза (мм)", "type": "float", "description": "Максимальный диаметр провода", "unit": "мм"},
    ]},

    # --- ЭЛЕКТРОНИКА (дополнительно) ---
    {"term": "транзистор", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип транзистора", "enum_values": ["NPN", "PNP", "MOSFET", "JFET"]},
        {"name": "voltage_v", "label_ru": "Напряжение (В)", "type": "float", "description": "Максимальное напряжение", "unit": "В"},
        {"name": "current_a", "label_ru": "Ток (А)", "type": "float", "description": "Максимальный ток", "unit": "А"},
    ]},
    {"term": "микросхема", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип микросхемы", "enum_values": ["микроконтроллер", "операционный усилитель", "стабилизатор", "логическая"]},
        {"name": "package", "label_ru": "Корпус", "type": "string", "description": "Тип корпуса"},
    ]},
    {"term": "датчик", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип датчика", "enum_values": ["температуры", "давления", "влажности", "света", "движения"]},
        {"name": "voltage", "label_ru": "Напряжение (В)", "type": "float", "description": "Рабочее напряжение", "unit": "В"},
        {"name": "interface", "label_ru": "Интерфейс", "type": "enum", "description": "Тип выхода", "enum_values": ["аналоговый", "цифровой", "I2C", "SPI", "UART"]},
    ]},
    {"term": "реле", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип реле", "enum_values": ["электромеханическое", "твердотельное", "импульсное"]},
        {"name": "voltage_v", "label_ru": "Напряжение катушки (В)", "type": "float", "description": "Напряжение управления", "unit": "В"},
        {"name": "current_a", "label_ru": "Ток коммутации (А)", "type": "float", "description": "Максимальный коммутируемый ток", "unit": "А"},
    ]},
    {"term": "кабель", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип кабеля", "enum_values": ["силовой", "сигнальный", "сетевой", "коаксиальный", "оптоволоконный"]},
        {"name": "cross_section", "label_ru": "Сечение (мм²)", "type": "float", "description": "Сечение жилы", "unit": "мм²"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина кабеля", "unit": "м"},
    ]},

    # --- СТРОИТЕЛЬСТВО (дополнительно) ---
    {"term": "бетонная смесь", "domain": "строительство", "parameters": [
        {"name": "grade", "label_ru": "Марка", "type": "enum", "description": "Класс прочности", "enum_values": ["М100", "М150", "М200", "М250", "М300", "М350", "М400"]},
        {"name": "slump_cm", "label_ru": "Подвижность (см)", "type": "float", "description": "Осадка конуса", "unit": "см"},
    ]},
    {"term": "арматура", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр стержня", "unit": "мм"},
        {"name": "steel_grade", "label_ru": "Марка стали", "type": "enum", "description": "Класс стали", "enum_values": ["А400", "А500", "А600", "В500"]},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина стержня", "unit": "м"},
    ]},
    {"term": "утеплитель", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид утеплителя", "enum_values": ["минвата", "пенопласт", "пенополистирол", "эковата", "пенополиуретан"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "description": "Толщина плиты", "unit": "мм"},
        {"name": "thermal_conductivity", "label_ru": "Теплопроводность (Вт/м·К)", "type": "float", "description": "Коэффициент теплопроводности", "unit": "Вт/м·К"},
    ]},
    {"term": "краска", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид краски", "enum_values": ["акриловая", "силиконовая", "масляная", "водоэмульсионная", "alkидная"]},
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Объём банки", "unit": "л"},
        {"name": "coverage", "label_ru": "Расход (м²/л)", "type": "float", "description": "Расход на слой", "unit": "м²/л"},
    ]},

    # --- КРЕПЁЖ (дополнительно) ---
    {"term": "дюбель", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр дюбеля", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип дюбеля", "enum_values": ["пластиковый", "металлический", "химический", "frames"]},
    ]},
    {"term": "саморез", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр резьбы", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина самореза", "unit": "мм"},
        {"name": "head_type", "label_ru": "Тип головки", "type": "enum", "description": "Форма головки", "enum_values": ["потайная", "полукруглая", "шестигранная"]},
    ]},
    {"term": "анкер", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "description": "Диаметр анкера", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "description": "Длина", "unit": "мм"},
        {"name": "load_kg", "label_ru": "Нагрузка (кг)", "type": "float", "description": "Максимальная нагрузка на отрыв", "unit": "кг"},
    ]},

    # --- БЫТОВАЯ ТЕХНИКА (дополнительно) ---
    {"term": "пылесос", "domain": "бытовая техника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Потребляемая мощность", "unit": "Вт"},
        {"name": "suction_pa", "label_ru": "Всасывание (Па)", "type": "float", "description": "Разрежение", "unit": "Па"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип пылесоса", "enum_values": ["вертикальный", "робот", "классический", "аккумуляторный"]},
    ]},
    {"term": "кофемашина", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип кофемашины", "enum_values": ["капсульная", "капельная", "эспрессо", "капучино"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Мощность", "unit": "Вт"},
        {"name": "water_tank_l", "label_ru": "Бак (л)", "type": "float", "description": "Объём бака для воды", "unit": "л"},
    ]},
    {"term": "микроволновая печь", "domain": "бытовая техника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Мощность", "unit": "Вт"},
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Объём камеры", "unit": "л"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип", "enum_values": ["только подогрев", "с грилем", "с конвекцией"]},
    ]},
    {"term": "чайник электрический", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Объём", "unit": "л"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Мощность", "unit": "Вт"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "description": "Материал корпуса", "enum_values": ["нержавеющая сталь", "пластик", "стекло", "керамика"]},
    ]},

    # --- ТРАНСПОРТ (дополнительно) ---
    {"term": "мотоцикл", "domain": "транспорт", "parameters": [
        {"name": "engine_cc", "label_ru": "Объём двигателя (см³)", "type": "float", "description": "Рабочий объём", "unit": "см³"},
        {"name": "power_hp", "label_ru": "Мощность (л.с.)", "type": "float", "description": "Мощность", "unit": "л.с."},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип мотоцикла", "enum_values": ["sport", "touring", "chopper", "enduro", "scooter"]},
    ]},
    {"term": "скутер", "domain": "транспорт", "parameters": [
        {"name": "engine_cc", "label_ru": "Объём двигателя (см³)", "type": "float", "description": "Объём", "unit": "см³"},
        {"name": "max_speed_kmh", "label_ru": "Макс. скорость (км/ч)", "type": "float", "description": "Максимальная скорость", "unit": "км/ч"},
    ]},
    {"term": "автобус", "domain": "транспорт", "parameters": [
        {"name": "capacity", "label_ru": "Вместимость (чел)", "type": "integer", "description": "Количество пассажиров"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина автобуса", "unit": "м"},
        {"name": "fuel_type", "label_ru": "Тип топлива", "type": "enum", "description": "Вид топлива", "enum_values": ["дизель", "электро", "газ", "гибрид"]},
    ]},
    {"term": "грузовик", "domain": "транспорт", "parameters": [
        {"name": "payload_kg", "label_ru": "Грузоподъёмность (кг)", "type": "float", "description": "Максимальная нагрузка", "unit": "кг"},
        {"name": "volume_m3", "label_ru": "Объём кузова (м³)", "type": "float", "description": "Объём кузова", "unit": "м³"},
        {"name": "fuel_type", "label_ru": "Тип топлива", "type": "enum", "description": "Вид топлива", "enum_values": ["дизель", "электро", "газ"]},
    ]},

    # --- МЕБЕЛЬ (дополнительно) ---
    {"term": "комод", "domain": "мебель", "parameters": [
        {"name": "drawers", "label_ru": "Количество ящиков", "type": "integer", "description": "Число ящиков"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал"},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "description": "Ширина", "unit": "мм"},
    ]},
    {"term": "стеллаж", "domain": "мебель", "parameters": [
        {"name": "shelves", "label_ru": "Количество полок", "type": "integer", "description": "Число полок"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал"},
        {"name": "max_load_kg", "label_ru": "Нагрузка на полку (кг)", "type": "float", "description": "Максимальная нагрузка", "unit": "кг"},
    ]},
    {"term": "кресло", "domain": "мебель", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип кресла", "enum_values": ["офисное", "компьютерное", "кресло-мешок", "кресло-качалка"]},
        {"name": "upholstery", "label_ru": "Обивка", "type": "string", "description": "Материал обивки"},
        {"name": "armrests", "label_ru": "Подлокотники", "type": "boolean", "description": "Наличие подлокотников"},
    ]},

    # --- СПОРТ (дополнительно) ---
    {"term": "мяч футбольный", "domain": "спорт", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "description": "Размер мяча", "enum_values": ["3", "4", "5"]},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал покрытия"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Вес мяча", "unit": "г"},
    ]},
    {"term": "ракетка теннисная", "domain": "спорт", "parameters": [
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Вес ракетки", "unit": "г"},
        {"name": "head_size_cm2", "label_ru": "Площадь головки (см²)", "type": "float", "description": "Размер головки", "unit": "см²"},
        {"name": "string_pattern", "label_ru": "Плотность нитей", "type": "string", "description": "Схема переплетения"},
    ]},
    {"term": "велосипед горный", "domain": "спорт", "parameters": [
        {"name": "wheel_size", "label_ru": "Диаметр колёс", "type": "enum", "description": "Размер колёс", "enum_values": ["26", "27.5", "29"]},
        {"name": "gears", "label_ru": "Количество передач", "type": "integer", "description": "Число скоростей"},
        {"name": "frame_material", "label_ru": "Материал рамы", "type": "enum", "description": "Материал", "enum_values": ["алюминий", "карбон", "сталь", "титан"]},
        {"name": "suspension", "label_ru": "Подвеска", "type": "enum", "description": "Тип подвески", "enum_values": ["hardtail", "full-suspension", "rigid"]},
    ]},

    # --- ОДЕЖДА (дополнительно) ---
    {"term": "джинсы", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал"},
        {"name": "fit", "label_ru": "Крой", "type": "enum", "description": "Тип кроя", "enum_values": ["skinny", "slim", "regular", "relaxed", "bootcut"]},
    ]},
    {"term": "футболка", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал"},
        {"name": "sleeve", "label_ru": "Рукав", "type": "enum", "description": "Длина рукава", "enum_values": ["короткий", "длинный", "без рукавов"]},
    ]},
    {"term": "куртка демисезонная", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string", "description": "Размер"},
        {"name": "material", "label_ru": "Материал", "type": "string", "description": "Материал"},
        {"name": "waterproof", "label_ru": "Водонепроницаемость", "type": "boolean", "description": "Наличие мембраны"},
    ]},

    # --- ЕДА (дополнительно) ---
    {"term": "чай", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид чая", "enum_values": ["чёрный", "зелёный", "белый", "oolong", "травяной"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "description": "Масса упаковки", "unit": "г"},
        {"name": "origin", "label_ru": "Происхождение", "type": "string", "description": "Страна производства"},
    ]},
    {"term": "сахар", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Вид сахара", "enum_values": ["песок", "рафинад", "коричневый", "пудра"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Масса упаковки", "unit": "кг"},
    ]},
    {"term": "молоко", "domain": "еда", "parameters": [
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "description": "Процент жирности", "unit": "%"},
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "description": "Объём упаковки", "unit": "л"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип молока", "enum_values": ["пастеризованное", "ультрапастеризованное", "свежее"]},
    ]},

    # --- ЖИВОТНЫЕ (дополнительно) ---
    {"term": "собака", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string", "description": "Порода"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес", "unit": "кг"},
        {"name": "size", "label_ru": "Размер", "type": "enum", "description": "Группа размера", "enum_values": ["малый", "средний", "крупный", "гигантский"]},
    ]},
    {"term": "кошка", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string", "description": "Порода"},
        {"name": "color", "label_ru": "Окрас", "type": "string", "description": "Окрас шерсти"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "description": "Вес", "unit": "кг"},
    ]},
    {"term": "рыба аквариумная", "domain": "животные", "parameters": [
        {"name": "species", "label_ru": "Вид", "type": "string", "description": "Вид рыбы"},
        {"name": "size_cm", "label_ru": "Размер (см)", "type": "float", "description": "Длина тела", "unit": "см"},
        {"name": "temperature_c", "label_ru": "Температура (°C)", "type": "string", "description": "Диапазон температуры"},
    ]},

    # --- МЕДИЦИНА (дополнительно) ---
    {"term": "шприц", "domain": "медицина", "parameters": [
        {"name": "volume_ml", "label_ru": "Объём (мл)", "type": "float", "description": "Объём шприца", "unit": "мл"},
        {"name": "needle_gauge", "label_ru": "Диаметр иглы (G)", "type": "float", "description": "Калибр иглы", "unit": "G"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип шприца", "enum_values": ["одноразовый", "многоразовый", "инсулиновый"]},
    ]},
    {"term": "бинт", "domain": "медицина", "parameters": [
        {"name": "width_cm", "label_ru": "Ширина (см)", "type": "float", "description": "Ширина бинта", "unit": "см"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "description": "Длина бинта", "unit": "м"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип бинта", "enum_values": ["стерильный", "нестерильный", "эластичный", " самоклеющийся"]},
    ]},

    # --- ОБОРУДОВАНИЕ (дополнительно) ---
    {"term": "сварочный аппарат", "domain": "оборудование", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип сварки", "enum_values": ["MIG", "TIG", "MMA", "plasma"]},
        {"name": "current_a", "label_ru": "Ток (А)", "type": "float", "description": "Максимальный ток", "unit": "А"},
        {"name": "voltage_v", "label_ru": "Напряжение (В)", "type": "float", "description": "Рабочее напряжение", "unit": "В"},
    ]},
    {"term": "компрессор", "domain": "оборудование", "parameters": [
        {"name": "pressure_bar", "label_ru": "Давление (бар)", "type": "float", "description": "Максимальное давление", "unit": "бар"},
        {"name": "volume_l", "label_ru": "Объём ресивера (л)", "type": "float", "description": "Объём бака", "unit": "л"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Мощность мотора", "unit": "Вт"},
    ]},
    {"term": "дрель", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "description": "Мощность", "unit": "Вт"},
        {"name": "max_drill_mm", "label_ru": "Макс. диаметр (мм)", "type": "float", "description": "Максимальный диаметр сверления", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "description": "Тип дрели", "enum_values": ["ударная", "безударная", "аккумуляторная"]},
    ]},
]


def seed_massive(db_path: str, force: bool = False) -> int:
    """Вставить понятия напрямую в SQLite.

    Returns:
        Количество вставленных понятий.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    if not force:
        row = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()
        if row[0] > 0:
            logger.info("База содержит %d понятий. Используйте --force.", row[0])
            conn.close()
            return 0

    if force:
        conn.execute("DELETE FROM relations")
        conn.execute("DELETE FROM parameters")
        conn.execute("DELETE FROM concepts")
        conn.commit()
        logger.info("Таблицы очищены.")

    # Подключаем компоненты для вычисления эмбеддингов
    from src.config import Config
    from src.embeddings import FastTextWrapper
    from src.knowledge_base import KnowledgeBase
    from src.lemmatizer import Lemmatizer
    from src.synonyms import SynonymDict

    project_root = Path(db_path).parent.parent
    cfg = Config.from_json("configs/config.json", project_root=project_root)
    Lemmatizer(cache_size=cfg.cache_lemma_size)
    synonym_dict = SynonymDict(json_path=cfg.synonyms_path)
    fallback_path = Path(cfg.fallback_embeddings_path) if cfg.fallback_embeddings_path else None
    embedding_model = FastTextWrapper(
        model_path=cfg.fasttext_model_path,
        fallback_path=fallback_path,
        cache_size=cfg.word_vector_cache_size,
    )
    kb = KnowledgeBase(config=cfg, embedding_model=embedding_model, synonym_dict=synonym_dict)

    inserted = 0
    try:
        for i, concept in enumerate(CONCEPTS):
            term = concept["term"]
            domain = concept["domain"]
            params = concept.get("parameters", [])

            # Вычислить эмбеддинг
            try:
                emb = kb.compute_concept_embedding(term)
                blob = emb.astype("<f4").tobytes()
            except Exception as exc:
                logger.warning("Ошибка эмбеддинга для %r: %s", term, exc)
                blob = None

            concept_id = f"concept_{i+1:04d}"

            # Вставить понятие
            conn.execute(
                "INSERT OR IGNORE INTO concepts (id, term, domain, embedding) VALUES (?, ?, ?, ?)",
                (concept_id, term, domain, blob),
            )

            # Вставить параметры
            for p in params:
                enum_val = json.dumps(p["enum_values"], ensure_ascii=False) if p.get("enum_values") else None
                conn.execute(
                    "INSERT INTO parameters (concept_id, name, label_ru, type, description, unit, enum_values, confidence) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 1.0)",
                    (
                        concept_id,
                        p["name"],
                        p["label_ru"],
                        p.get("type", "string"),
                        p.get("description", ""),
                        p.get("unit"),
                        enum_val,
                    ),
                )

            inserted += 1
            if (i + 1) % 20 == 0:
                conn.commit()
                logger.info("Обработано %d/%d понятий", i + 1, len(CONCEPTS))

        conn.commit()
        logger.info("Вставлено %d понятий", inserted)
    finally:
        kb.close()
        conn.close()

    return inserted


if __name__ == "__main__":
    _root = Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Масштабное наполнение БД")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--config", default="configs/config.json")
    args = parser.parse_args()

    from src.config import Config
    cfg = Config.from_json(args.config, project_root=_root)
    n = seed_massive(str(cfg.db_path), force=args.force)
    print(f"Готово. Вставлено: {n} понятий")
