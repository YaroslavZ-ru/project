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

    # =====================================================================
    # МАССИВНОЕ РАСШИРЕНИЕ БАЗЫ (+500 понятий)
    # =====================================================================

    # --- СЛЕСАРНЫЙ ИНСТРУМЕНТ (ещё 30) ---
    {"term": "ключ трещёточный", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
        {"name": "reversible", "label_ru": "Реверс", "type": "boolean"},
    ]},
    {"term": "ключ комбинированный", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "ключи трубные", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_range", "label_ru": "Диапазон (дюйм)", "type": "string"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["арматурный", "газовый", "столбовой"]},
    ]},
    {"term": "ключ внутренний", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "ключи накидные", "domain": "слесарный инструмент", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "зубило", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "blade_width_mm", "label_ru": "Ширина лезвия (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "зубило слесарное", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "зубило столярное", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "blade_width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "киянка", "domain": "слесарный инструмент", "parameters": [
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "material", "label_ru": "Материал головки", "type": "enum", "enum_values": ["каучук", "пластик", "нейлон"]},
    ]},
    {"term": "молоток слесарный", "domain": "слесарный инструмент", "parameters": [
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "handle_material", "label_ru": "Материал рукоятки", "type": "string"},
    ]},
    {"term": "молоток столярный", "domain": "слесарный инструмент", "parameters": [
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "развёртка", "domain": "слесарный инструмент", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["ручная", "машинная"]},
    ]},
    {"term": "метчик", "domain": "слесарный инструмент", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "thread_type", "label_ru": "Тип резьбы", "type": "string"},
    ]},
    {"term": "напильник", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["круглый", "плоский", "треугольный", "квадратный", "полукруглый"]},
        {"name": "roughness", "label_ru": "Зернистость", "type": "string"},
    ]},
    {"term": "надфиль", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "set_count", "label_ru": "Количество", "type": "integer"},
    ]},
    {"term": "ножовка по металлу", "domain": "слесарный инструмент", "parameters": [
        {"name": "blade_length_mm", "label_ru": "Длина полотна (мм)", "type": "float", "unit": "мм"},
        {"name": "tpi", "label_ru": "Зубьев на дюйм", "type": "integer"},
    ]},
    {"term": "ножницы по металлу", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "cutting_thickness_mm", "label_ru": "Толщина реза (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "퓰ка", "domain": "слесарный инструмент", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "handle_material", "label_ru": "Материал рукоятки", "type": "string"},
    ]},
    {"term": "ковшёк слесарный", "domain": "слесарный инструмент", "parameters": [
        {"name": "capacity_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
    ]},
    {"term": "ерш для нарезки резьбы", "domain": "слесарный инструмент", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
    ]},
    {"term": "струбцина", "domain": "слесарный инструмент", "parameters": [
        {"name": "jaw_width_mm", "label_ru": "Ширина губок (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["F-образная", "слесарная", "угловая", "快速"]},
    ]},
    {"term": "струбцина F-образная", "domain": "слесарный инструмент", "parameters": [
        {"name": "jaw_width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "max_opening_mm", "label_ru": "Макс. раскрытие (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "струбцина угловая", "domain": "слесарный инструмент", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
    ]},
    {"term": "слесарный вороток", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "слесарный рычаг", "domain": "слесарный инструмент", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "слесарный молоток", "domain": "слесарный инструмент", "parameters": [
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "слесарный шпатель", "domain": "слесарный инструмент", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "слесарная щётка", "domain": "слесарный инструмент", "parameters": [
        {"name": "wire_type", "label_ru": "Тип щетины", "type": "enum", "enum_values": ["стальная", "латунная", "нейлоновая"]},
    ]},

    # --- ЭЛЕКТРОНИКА (ещё 30) ---
    {"term": "конденсатор электролитический", "domain": "электроника", "parameters": [
        {"name": "capacitance_mf", "label_ru": "Ёмкость (мкФ)", "type": "float", "unit": "мкФ"},
        {"name": "voltage_v", "label_ru": "Напряжение (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "конденсатор керамический", "domain": "электроника", "parameters": [
        {"name": "capacitance_pf", "label_ru": "Ёмкость (пФ)", "type": "float", "unit": "пФ"},
        {"name": "voltage_v", "label_ru": "Напряжение (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "резистор постоянный", "domain": "электроника", "parameters": [
        {"name": "resistance_ohm", "label_ru": "Сопротивление (Ом)", "type": "float", "unit": "Ом"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "tolerance_percent", "label_ru": "Допуск (%)", "type": "float", "unit": "%"},
    ]},
    {"term": "резистор переменный", "domain": "электроника", "parameters": [
        {"name": "resistance_ohm", "label_ru": "Сопротивление (Ом)", "type": "float", "unit": "Ом"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["постоянный", "подстроечный", "поворотный"]},
    ]},
    {"term": "диод выпрямительный", "domain": "электроника", "parameters": [
        {"name": "max_current_a", "label_ru": "Макс. ток (А)", "type": "float", "unit": "А"},
        {"name": "reverse_voltage_v", "label_ru": "Обратное напряжение (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "светодиод красный", "domain": "электроника", "parameters": [
        {"name": "forward_voltage_v", "label_ru": "Прямое напряжение (В)", "type": "float", "unit": "В"},
        {"name": "current_ma", "label_ru": "Ток (мА)", "type": "float", "unit": "мА"},
    ]},
    {"term": "светодиод зелёный", "domain": "электроника", "parameters": [
        {"name": "forward_voltage_v", "label_ru": "Прямое напряжение (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "светодиод синий", "domain": "электроника", "parameters": [
        {"name": "forward_voltage_v", "label_ru": "Прямое напряжение (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "светодиод белый", "domain": "электроника", "parameters": [
        {"name": "forward_voltage_v", "label_ru": "Прямое напряжение (В)", "type": "float", "unit": "В"},
        {"name": "color_temp_k", "label_ru": "Цветовая температура (К)", "type": "float", "unit": "К"},
    ]},
    {"term": "стабилизатор напряжения", "domain": "электроника", "parameters": [
        {"name": "output_voltage_v", "label_ru": "Выходное напряжение (В)", "type": "float", "unit": "В"},
        {"name": "max_current_a", "label_ru": "Макс. ток (А)", "type": "float", "unit": "А"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["линейный", "импульсный"]},
    ]},
    {"term": "преобразователь DC-DC", "domain": "электроника", "parameters": [
        {"name": "input_voltage_v", "label_ru": "Входное напряжение (В)", "type": "float", "unit": "В"},
        {"name": "output_voltage_v", "label_ru": "Выходное напряжение (В)", "type": "float", "unit": "В"},
        {"name": "max_current_a", "label_ru": "Макс. ток (А)", "type": "float", "unit": "А"},
    ]},
    {"term": "генератор импульсов", "domain": "электроника", "parameters": [
        {"name": "frequency_hz", "label_ru": "Частота (Гц)", "type": "float", "unit": "Гц"},
        {"name": "amplitude_v", "label_ru": "Амплитуда (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "осциллограф", "domain": "электроника", "parameters": [
        {"name": "bandwidth_mhz", "label_ru": "Полоса пропускания (МГц)", "type": "float", "unit": "МГц"},
        {"name": "channels", "label_ru": "Количество каналов", "type": "integer"},
        {"name": "sample_rate_msps", "label_ru": "Частота дискретизации (МВ/с)", "type": "float", "unit": "МВ/с"},
    ]},
    {"term": "мультиметр", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["цифровой", "аналоговый", "автоматический"]},
        {"name": "accuracy_class", "label_ru": "Класс точности", "type": "float"},
        {"name": "max_voltage_v", "label_ru": "Макс. напряжение (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "паяльник", "domain": "электроника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "tip_type", "label_ru": "Тип жала", "type": "enum", "enum_values": ["конусное", "плоское", "игольчатое"]},
    ]},
    {"term": "припой", "domain": "электроника", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "composition", "label_ru": "Состав", "type": "enum", "enum_values": ["свинцовый", "безсвинцовый", "серебросодержащий"]},
    ]},
    {"term": "флешка USB", "domain": "электроника", "parameters": [
        {"name": "capacity_gb", "label_ru": "Ёмкость (ГБ)", "type": "float", "unit": "ГБ"},
        {"name": "usb_version", "label_ru": "Версия USB", "type": "enum", "enum_values": ["2.0", "3.0", "3.1", "3.2", "4.0"]},
    ]},
    {"term": "жёсткий диск", "domain": "электроника", "parameters": [
        {"name": "capacity_tb", "label_ru": "Ёмкость (ТБ)", "type": "float", "unit": "ТБ"},
        {"name": "rpm", "label_ru": "Скорость вращения (об/мин)", "type": "integer", "unit": "об/мин"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["HDD", "SSD", "NVMe"]},
    ]},
    {"term": "оперативная память", "domain": "электроника", "parameters": [
        {"name": "capacity_gb", "label_ru": "Объём (ГБ)", "type": "float", "unit": "ГБ"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["DDR3", "DDR4", "DDR5"]},
        {"name": "frequency_mhz", "label_ru": "Частота (МГц)", "type": "float", "unit": "МГц"},
    ]},
    {"term": "процессор", "domain": "электроника", "parameters": [
        {"name": "cores", "label_ru": "Количество ядер", "type": "integer"},
        {"name": "frequency_ghz", "label_ru": "Частота (ГГц)", "type": "float", "unit": "ГГц"},
        {"name": "tdp_watt", "label_ru": "TDP (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "видеокарта", "domain": "электроника", "parameters": [
        {"name": "memory_gb", "label_ru": "Память (ГБ)", "type": "float", "unit": "ГБ"},
        {"name": "memory_type", "label_ru": "Тип памяти", "type": "enum", "enum_values": ["GDDR5", "GDDR6", "GDDR6X", "HBM2"]},
        {"name": "tdp_watt", "label_ru": "TDP (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "блок питания", "domain": "электроника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["ATX", "SFX", "бесперебойный", "импульсный"]},
        {"name": "efficiency", "label_ru": "КПД (%)", "type": "float", "unit": "%"},
    ]},
    {"term": "материнская плата", "domain": "электроника", "parameters": [
        {"name": "socket", "label_ru": "Сокет", "type": "string"},
        {"name": "form_factor", "label_ru": "Форм-фактор", "type": "enum", "enum_values": ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"]},
        {"name": "chipset", "label_ru": "Чипсет", "type": "string"},
    ]},
    {"term": "монитор", "domain": "электроника", "parameters": [
        {"name": "diagonal_inches", "label_ru": "Диагональ (дюйм)", "type": "float", "unit": "дюйм"},
        {"name": "resolution", "label_ru": "Разрешение", "type": "enum", "enum_values": ["1920x1080", "2560x1440", "3840x2160", "5120x2880"]},
        {"name": "refresh_rate_hz", "label_ru": "Частота обновления (Гц)", "type": "integer", "unit": "Гц"},
        {"name": "panel_type", "label_ru": "Тип матрицы", "type": "enum", "enum_values": ["IPS", "VA", "TN", "OLED"]},
    ]},
    {"term": "клавиатура", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["мембранная", "механическая", "электрокапacитивная"]},
        {"name": "connection", "label_ru": "Подключение", "type": "enum", "enum_values": ["проводная", "беспроводная", "Bluetooth"]},
        {"name": "backlight", "label_ru": "Подсветка", "type": "boolean"},
    ]},
    {"term": "мышь компьютерная", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["оптическая", "лазерная", "тренажёрная"]},
        {"name": "dpi", "label_ru": "DPI", "type": "integer"},
        {"name": "connection", "label_ru": "Подключение", "type": "enum", "enum_values": ["проводная", "беспроводная", "Bluetooth"]},
    ]},
    {"term": "наушники", "domain": "электроника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["внутриканальные", "накладные", "полноразмерные", "TWS"]},
        {"name": "frequency_hz", "label_ru": "Частотный диапазон (Гц)", "type": "string"},
        {"name": "impedance_ohm", "label_ru": "Импеданс (Ом)", "type": "float", "unit": "Ом"},
    ]},
    {"term": "колонки", "domain": "электроника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["активные", "пассивные", "портативные", "сабвуфер"]},
        {"name": "frequency_hz", "label_ru": "Частотный диапазон (Гц)", "type": "string"},
    ]},

    # --- СТРОИТЕЛЬСТВО (ещё 30) ---
    {"term": "гипсокартон", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["обычный", "влагостойкий", "огнестойкий", "комбинированный"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "unit": "мм"},
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "string"},
    ]},
    {"term": "профиль для гипсокартона", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["направляющий", "стоечный", "потолочный"]},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "керамическая плитка", "domain": "строительство", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "string"},
        {"name": "class", "label_ru": "Класс износостойкости", "type": "enum", "enum_values": ["PEI I", "PEI II", "PEI III", "PEI IV", "PEI V"]},
        {"name": "water_absorption", "label_ru": "Влагопоглощение (%)", "type": "float", "unit": "%"},
    ]},
    {"term": "ламинат", "domain": "строительство", "parameters": [
        {"name": "class", "label_ru": "Класс", "type": "enum", "enum_values": ["31", "32", "33", "34"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "unit": "мм"},
        {"name": "size_mm", "label_ru": "Размер планки (мм)", "type": "string"},
    ]},
    {"term": "линолеум", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["бытовой", "полукоммерческий", "коммерческий"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "unit": "мм"},
        {"name": "width_m", "label_ru": "Ширина рулона (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "краска интерьерная", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["акриловая", "латексная", "силиконовая"]},
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "coverage", "label_ru": "Расход (м²/л)", "type": "float", "unit": "м²/л"},
    ]},
    {"term": "обои", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["бумажные", "виниловые", "флизелиновые", "текстильные", "фотообои"]},
        {"name": "width_m", "label_ru": "Ширина (м)", "type": "float", "unit": "м"},
        {"name": "length_m", "label_ru": "Длина рулона (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "труба пластиковая", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["ПВХ", "ПП", "ПНД", "полипропилен"]},
    ]},
    {"term": "труба металлическая", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "wall_thickness_mm", "label_ru": "Толщина стенки (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "фитинг", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["угол", "тройник", "муфта", "кран"]},
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "крыша", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["скатная", "плоская", "мансардная"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["черепица", "металлочерепица", "профнастил", "мягкая кровля"]},
    ]},
    {"term": "стена", "domain": "строительство", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["кирпич", "блок", "дерево", "каркас"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "перегородка", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["гипсокартонная", "стеклянная", "деревянная", "кирпичная"]},
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "дверь входная", "domain": "строительство", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["металл", "дерево", "стекло", "комбинированный"]},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "height_mm", "label_ru": "Высота (мм)", "type": "float", "unit": "мм"},
        {"name": "insulation", "label_ru": "Утеплитель", "type": "boolean"},
    ]},
    {"term": "дверь межкомнатная", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["распашная", "раздвижная", "складная"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["дерево", "МДФ", "стекло", "комбинированный"]},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "окно пластиковое", "domain": "строительство", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "height_mm", "label_ru": "Высота (мм)", "type": "float", "unit": "мм"},
        {"name": "glass_type", "label_ru": "Тип стеклопакета", "type": "enum", "enum_values": ["однокамерный", "двухкамерный", "трёхкамерный"]},
    ]},
    {"term": "лестница", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["прямая", "поворотная", "винтовая", "на тетивах"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["дерево", "металл", "бетон", "стекло"]},
    ]},
    {"term": "крыльцо", "domain": "строительство", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["дерево", "металл", "бетон", "камень"]},
        {"name": "steps", "label_ru": "Количество ступеней", "type": "integer"},
    ]},
    {"term": "забор", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["профнастил", "сетка", "еврозабор", "деревянный", "каменный"]},
        {"name": "height_m", "label_ru": "Высота (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "ворота", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["распашные", "секционные", "rollo", "откатные"]},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "height_mm", "label_ru": "Высота (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "гаражные ворота", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["секционные", "rollo", "откатные", "распашные"]},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "height_mm", "label_ru": "Высота (мм)", "type": "float", "unit": "мм"},
        {"name": "automation", "label_ru": "Автоматика", "type": "boolean"},
    ]},
    {"term": "фундамент", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["ленточный", "плитный", "свайный", "столбчатый"]},
        {"name": "depth_m", "label_ru": "Глубина (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "крыльцо деревянное", "domain": "строительство", "parameters": [
        {"name": "steps", "label_ru": "Количество ступеней", "type": "integer"},
    ]},

    # --- КРЕПЁЖ (ещё 20) ---
    {"term": "гайка", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["обычная", "барашковая", "корончатая", "стопорная"]},
    ]},
    {"term": "гайка шестигранная", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "гайка барашковая", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "гайка стопорная", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "шайба", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["плоская", "гровер", "пружинная", "токопроводящая"]},
    ]},
    {"term": "гровер", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "болт", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "head_type", "label_ru": "Тип головки", "type": "enum", "enum_values": ["шестигранная", "потайная", "полукруглая"]},
    ]},
    {"term": "болт шестигранный", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "болт потайной", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "винт", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "head_type", "label_ru": "Тип головки", "type": "enum", "enum_values": ["потайная", "полукруглая", "шестигранная"]},
    ]},
    {"term": "саморез по дереву", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "саморез по металлу", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "дюбель пластиковый", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "дюбель-metal", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "дюбель-бабочка", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "анкер болт", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "анкер клиновой", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "анкер химический", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "volume_ml", "label_ru": "Объём капсулы (мл)", "type": "float", "unit": "мл"},
    ]},
    {"term": "кляймер", "domain": "крепёж", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["для гипсокартона", "для дерева", "универсальный"]},
    ]},
    {"term": "хомут", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["металлический", "пластиковый", "nylon"]},
    ]},

    # --- БЫТОВАЯ ТЕХНИКА (ещё 20) ---
    {"term": "холодильник двухдверный", "domain": "бытовая техника", "parameters": [
        {"name": "total_volume_l", "label_ru": "Общий объём (л)", "type": "float", "unit": "л"},
        {"name": "freezer_volume_l", "label_ru": "Морозильная камера (л)", "type": "float", "unit": "л"},
        {"name": "energy_class", "label_ru": "Класс энергоэффективности", "type": "enum", "enum_values": ["A+++", "A++", "A+", "A"]},
    ]},
    {"term": "холодильник однодверный", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "energy_class", "label_ru": "Класс энергоэффективности", "type": "enum", "enum_values": ["A++", "A+", "A", "B"]},
    ]},
    {"term": "морозильная камера", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "temperature_c", "label_ru": "Температура (°C)", "type": "float", "unit": "°C"},
    ]},
    {"term": "посудомоечная машина", "domain": "бытовая техника", "parameters": [
        {"name": "capacity", "label_ru": "Вместимость (наборов)", "type": "integer"},
        {"name": "energy_class", "label_ru": "Класс энергоэффективности", "type": "enum", "enum_values": ["A+++", "A++", "A+", "A"]},
        {"name": "noise_db", "label_ru": "Уровень шума (дБ)", "type": "float", "unit": "дБ"},
    ]},
    {"term": "духовой шкаф", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["газовый", "электрический", "комбинированный"]},
    ]},
    {"term": "варочная панель", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["газовая", "электрическая", "индукционная", "стеклокерамическая"]},
        {"name": "zones", "label_ru": "Количество конфорок", "type": "integer"},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "вытяжка", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["встроенная", "навесная", "островная", "купольная"]},
        {"name": "capacity_m3h", "label_ru": "Производительность (м³/ч)", "type": "float", "unit": "м³/ч"},
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "водонагреватель", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["накопительный", "проточный", "бойлер"]},
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "кондиционер", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["сплит-система", "мобильный", "оконный", "кассетный"]},
        {"name": "power_kw", "label_ru": "Мощность охлаждения (кВт)", "type": "float", "unit": "кВт"},
        {"name": "area_m2", "label_ru": "Площадь помещения (м²)", "type": "float", "unit": "м²"},
    ]},
    {"term": "обогреватель", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["конвектор", "масляный", "керамический", "инфракрасный", "тепловентилятор"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "area_m2", "label_ru": "Площадь обогрева (м²)", "type": "float", "unit": "м²"},
    ]},
    {"term": "утюг", "domain": "бытовая техника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "sole_material", "label_ru": "Материал подошвы", "type": "enum", "enum_values": ["титан", "керамика", "нержавеющая сталь", "тефлон"]},
        {"name": "steam_gmin", "label_ru": "Паровой удар (г/мин)", "type": "float", "unit": "г/мин"},
    ]},
    {"term": "парогенератор", "domain": "бытовая техника", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "tank_volume_l", "label_ru": "Объём бака (л)", "type": "float", "unit": "л"},
    ]},
    {"term": "соковыжималка", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["цитрусовая", "шнековая", "центробежная"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "блендер", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["погружной", "стационарный", "кухонный комбайн"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "speeds", "label_ru": "Количество скоростей", "type": "integer"},
    ]},
    {"term": "мясорубка", "domain": "бытовая техника", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["электрическая", "ручная"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "productivity_kgh", "label_ru": "Производительность (кг/ч)", "type": "float", "unit": "кг/ч"},
    ]},
    {"term": "тостер", "domain": "бытовая техника", "parameters": [
        {"name": "slots", "label_ru": "Количество слотов", "type": "integer"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "мультиварка", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "programs", "label_ru": "Количество программ", "type": "integer"},
    ]},
    {"term": "скороварка", "domain": "бытовая техника", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["электрическая", "газовая"]},
    ]},

    # --- ТРАНСПОРТ (ещё 20) ---
    {"term": "легковой автомобиль", "domain": "транспорт", "parameters": [
        {"name": "body_type", "label_ru": "Тип кузова", "type": "enum", "enum_values": ["седан", "хэтчбек", "универсал", "купе", "кабриолет"]},
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "unit": "л"},
        {"name": "power_hp", "label_ru": "Мощность (л.с.)", "type": "float", "unit": "л.с."},
    ]},
    {"term": "внедорожник", "domain": "транспорт", "parameters": [
        {"name": "drive_type", "label_ru": "Привод", "type": "enum", "enum_values": ["передний", "задний", "полный"]},
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "unit": "л"},
        {"name": "clearance_mm", "label_ru": "Клиренс (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "пикап", "domain": "транспорт", "parameters": [
        {"name": "payload_kg", "label_ru": "Грузоподъёмность (кг)", "type": "float", "unit": "кг"},
        {"name": "body_length_m", "label_ru": "Длина кузова (м)", "type": "float", "unit": "м"},
        {"name": "drive_type", "label_ru": "Привод", "type": "enum", "enum_values": ["задний", "полный"]},
    ]},
    {"term": "минивэн", "domain": "транспорт", "parameters": [
        {"name": "seats", "label_ru": "Количество мест", "type": "integer"},
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "unit": "л"},
    ]},
    {"term": "кроссовер", "domain": "транспорт", "parameters": [
        {"name": "drive_type", "label_ru": "Привод", "type": "enum", "enum_values": ["передний", "полный"]},
        {"name": "engine_volume_l", "label_ru": "Объём двигателя (л)", "type": "float", "unit": "л"},
        {"name": "clearance_mm", "label_ru": "Клиренс (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "электромобиль", "domain": "транспорт", "parameters": [
        {"name": "battery_kwh", "label_ru": "Ёмкость батареи (кВт·ч)", "type": "float", "unit": "кВт·ч"},
        {"name": "range_km", "label_ru": "Запас хода (км)", "type": "float", "unit": "км"},
        {"name": "power_kw", "label_ru": "Мощность (кВт)", "type": "float", "unit": "кВт"},
    ]},
    {"term": "прицеп", "domain": "транспорт", "parameters": [
        {"name": "payload_kg", "label_ru": "Грузоподъёмность (кг)", "type": "float", "unit": "кг"},
        {"name": "body_volume_m3", "label_ru": "Объём кузова (м³)", "type": "float", "unit": "м³"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["бортовой", "тентованный", "фургон", "рефрижератор"]},
    ]},
    {"term": "лодка моторная", "domain": "транспорт", "parameters": [
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
        {"name": "engine_power_hp", "label_ru": "Мощность мотора (л.с.)", "type": "float", "unit": "л.с."},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["ПВХ", "алюминий", "стеклопластик", "дерево"]},
    ]},
    {"term": "катер", "domain": "транспорт", "parameters": [
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
        {"name": "engine_power_hp", "label_ru": "Мощность мотора (л.с.)", "type": "float", "unit": "л.с."},
        {"name": "capacity", "label_ru": "Вместимость (чел)", "type": "integer"},
    ]},
    {"term": "яхта", "domain": "транспорт", "parameters": [
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["парусная", "моторная", "моторно-парусная"]},
        {"name": "cabins", "label_ru": "Количество кают", "type": "integer"},
    ]},
    {"term": "снегоход", "domain": "транспорт", "parameters": [
        {"name": "engine_cc", "label_ru": "Объём двигателя (см³)", "type": "float", "unit": "см³"},
        {"name": "track_length_mm", "label_ru": "Длина гусеницы (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["趟овый", "mountain", "утилитарный"]},
    ]},
    {"term": "квадроцикл", "domain": "транспорт", "parameters": [
        {"name": "engine_cc", "label_ru": "Объём двигателя (см³)", "type": "float", "unit": "см³"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["sport", "utility", "youth"]},
        {"name": "drive_type", "label_ru": "Привод", "type": "enum", "enum_values": ["2WD", "4WD"]},
    ]},
    {"term": "велосипед шоссейный", "domain": "транспорт", "parameters": [
        {"name": "frame_material", "label_ru": "Материал рамы", "type": "enum", "enum_values": ["алюминий", "карбон", "сталь", "титан"]},
        {"name": "gears", "label_ru": "Количество передач", "type": "integer"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "велосипед городской", "domain": "транспорт", "parameters": [
        {"name": "wheel_size", "label_ru": "Диаметр колёс", "type": "enum", "enum_values": ["24", "26", "28"]},
        {"name": "gears", "label_ru": "Количество передач", "type": "integer"},
        {"name": "basket", "label_ru": "Корзина", "type": "boolean"},
    ]},
    {"term": "самокат электрический", "domain": "транспорт", "parameters": [
        {"name": "max_speed_kmh", "label_ru": "Макс. скорость (км/ч)", "type": "float", "unit": "км/ч"},
        {"name": "range_km", "label_ru": "Запас хода (км)", "type": "float", "unit": "км"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "сигвей", "domain": "транспорт", "parameters": [
        {"name": "max_speed_kmh", "label_ru": "Макс. скорость (км/ч)", "type": "float", "unit": "км/ч"},
        {"name": "range_km", "label_ru": "Запас хода (км)", "type": "float", "unit": "км"},
    ]},
    {"term": "гидроцикл", "domain": "транспорт", "parameters": [
        {"name": "engine_power_hp", "label_ru": "Мощность (л.с.)", "type": "float", "unit": "л.с."},
        {"name": "capacity", "label_ru": "Вместимость (чел)", "type": "integer"},
    ]},
    {"term": "снегокат", "domain": "транспорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["детский", "взрослый", "гидроцикл"]},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},

    # --- МЕБЕЛЬ (ещё 20) ---
    {"term": "стол обеденный", "domain": "мебель", "parameters": [
        {"name": "seats", "label_ru": "Количество мест", "type": "integer"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "extendable", "label_ru": "Раздвижной", "type": "boolean"},
    ]},
    {"term": "стол письменный", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "depth_mm", "label_ru": "Глубина (мм)", "type": "float", "unit": "мм"},
        {"name": "drawers", "label_ru": "Количество ящиков", "type": "integer"},
    ]},
    {"term": "стол компьютерный", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "keyboard_tray", "label_ru": "Выдвижная полка", "type": "boolean"},
    ]},
    {"term": "стол журнальный", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "стол кухонный", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "extendable", "label_ru": "Раздвижной", "type": "boolean"},
    ]},
    {"term": "стол консольный", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "стул деревянный", "domain": "мебель", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "seat_height_mm", "label_ru": "Высота сиденья (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "стул столярный", "domain": "мебель", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "стул барный", "domain": "мебель", "parameters": [
        {"name": "seat_height_mm", "label_ru": "Высота сиденья (мм)", "type": "float", "unit": "мм"},
        {"name": "adjustable", "label_ru": "Регулируемый", "type": "boolean"},
    ]},
    {"term": "стул детский", "domain": "мебель", "parameters": [
        {"name": "age_range", "label_ru": "Возраст", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "кресло офисное", "domain": "мебель", "parameters": [
        {"name": "seat_height_mm", "label_ru": "Высота сиденья (мм)", "type": "float", "unit": "мм"},
        {"name": "backrest", "label_ru": "Регулируемая спинка", "type": "boolean"},
        {"name": "armrests", "label_ru": "Подлокотники", "type": "boolean"},
    ]},
    {"term": "кресло компьютерное", "domain": "мебель", "parameters": [
        {"name": "seat_height_mm", "label_ru": "Высота сиденья (мм)", "type": "float", "unit": "мм"},
        {"name": "armrests", "label_ru": "Подлокотники", "type": "boolean"},
    ]},
    {"term": "кресло-мешок", "domain": "мебель", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "filling", "label_ru": "Наполнитель", "type": "enum", "enum_values": ["пенополистирол", "холлофайбер", "пена"]},
    ]},
    {"term": "кресло-качалка", "domain": "мебель", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "upholstery", "label_ru": "Обивка", "type": "string"},
    ]},
    {"term": "банкетка", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "табурет", "domain": "мебель", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "seat_height_mm", "label_ru": "Высота сиденья (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "тумба прикроватная", "domain": "мебель", "parameters": [
        {"name": "drawers", "label_ru": "Количество ящиков", "type": "integer"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "тумба под ТВ", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "max_tv_size", "label_ru": "Макс. размер ТВ (дюйм)", "type": "float", "unit": "дюйм"},
    ]},
    {"term": "сервант", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "glass_doors", "label_ru": "Стеклянные дверцы", "type": "boolean"},
    ]},
    {"term": "витрина", "domain": "мебель", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "glass", "label_ru": "Стеклянные полки", "type": "boolean"},
    ]},

    # --- СПОРТ (ещё 20) ---
    {"term": "гантели", "domain": "спорт", "parameters": [
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["фиксированные", "регулируемые"]},
    ]},
    {"term": "штанга олимпийская", "domain": "спорт", "parameters": [
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "блин", "domain": "спорт", "parameters": [
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "скамейка для жима", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["горизонтальная", "наклонная", "регулируемая"]},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "тренажёр беговая дорожка", "domain": "спорт", "parameters": [
        {"name": "max_speed_kmh", "label_ru": "Макс. скорость (км/ч)", "type": "float", "unit": "км/ч"},
        {"name": "motor_power_watt", "label_ru": "Мощность мотора (Вт)", "type": "float", "unit": "Вт"},
        {"name": "belt_width_mm", "label_ru": "Ширина ленты (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "тренажёр велосипед", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["вертикальный", "горизонтальный", "спиннинг"]},
        {"name": "flywheel_kg", "label_ru": "Маховик (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "степпер", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["мини", "с ручками", "вращающийся"]},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "эллиптический тренажёр", "domain": "спорт", "parameters": [
        {"name": "stride_length_mm", "label_ru": "Длина шага (мм)", "type": "float", "unit": "мм"},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "гриф", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["прямой", "изогнутый", "EZ"]},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "мяч фитнес", "domain": "спорт", "parameters": [
        {"name": "diameter_cm", "label_ru": "Диаметр (см)", "type": "float", "unit": "см"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["классический", "с ручками", "мини"]},
    ]},
    {"term": "резинка эластичная", "domain": "спорт", "parameters": [
        {"name": "resistance_kg", "label_ru": "Сопротивление (кг)", "type": "float", "unit": "кг"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["петля", "лента", "-expander"]},
    ]},
    {"term": "мат для йоги", "domain": "спорт", "parameters": [
        {"name": "thickness_mm", "label_ru": "Толщина (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["TPE", "ПВХ", "натуральный каучук", "пробковый"]},
    ]},
    {"term": "верёвка для прыжков", "domain": "спорт", "parameters": [
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
        {"name": "handle_type", "label_ru": "Тип ручек", "type": "enum", "enum_values": ["пластик", "металл", "с подшипниками"]},
    ]},
    {"term": "боксерские перчатки", "domain": "спорт", "parameters": [
        {"name": "weight_oz", "label_ru": "Вес (унций)", "type": "float", "unit": "унц"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["тренажёрные", "спарринговые", "для боя"]},
    ]},
    {"term": "груша боксёрская", "domain": "спорт", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["прямая", "грушевидная", "молния"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "мяч баскетбольный", "domain": "спорт", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "enum_values": ["5", "6", "7"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["кожа", "синтетика", "каучук"]},
    ]},
    {"term": "мяч волейбольный", "domain": "спорт", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "enum_values": ["5", "4"]},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "ракетка бадминтонная", "domain": "спорт", "parameters": [
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
        {"name": "shaft_flex", "label_ru": "Жёсткость", "type": "enum", "enum_values": ["жёсткая", "средняя", "мягкая"]},
    ]},
    {"term": "лыжи горные", "domain": "спорт", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "radius_mm", "label_ru": "Радиус (мм)", "type": "float", "unit": "мм"},
        {"name": "level", "label_ru": "Уровень", "type": "enum", "enum_values": ["начинающий", "средний", "продвинутый"]},
    ]},
    {"term": "сноуборд", "domain": "спорт", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["allsround", "freestyle", "freeride", "race"]},
    ]},
    {"term": "коньки фигурные", "domain": "спорт", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "blade_type", "label_ru": "Тип лезвия", "type": "enum", "enum_values": ["обычные", "хоккейные", "фигурные"]},
    ]},

    # --- ОДЕЖДА (ещё 20) ---
    {"term": "штаны", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["джинсы", "костюмные", "спортивные", "джоггеры"]},
    ]},
    {"term": "рубашка", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "sleeve", "label_ru": "Рукав", "type": "enum", "enum_values": ["длинный", "короткий"]},
    ]},
    {"term": "блузка", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "платье", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "length", "label_ru": "Длина", "type": "enum", "enum_values": ["мини", "миди", "макси", "до колена"]},
    ]},
    {"term": "юбка", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "length", "label_ru": "Длина", "type": "enum", "enum_values": ["мини", "миди", "макси", "до колена"]},
    ]},
    {"term": "пиджак", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "жилет", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["утеплённый", "тёплый", "декоративный"]},
    ]},
    {"term": "кардиган", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "свитер", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "neckline", "label_ru": "Вырез", "type": "enum", "enum_values": ["круглый", "V-образный", "стойка", "высокий"]},
    ]},
    {"term": "худи", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "hood", "label_ru": "Капюшон", "type": "boolean"},
    ]},
    {"term": "толстовка", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "zipper", "label_ru": "Молния", "type": "boolean"},
    ]},
    {"term": "шорты", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "length", "label_ru": "Длина", "type": "enum", "enum_values": ["мини", "миди", "до колена"]},
    ]},
    {"term": "пижама", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "season", "label_ru": "Сезон", "type": "enum", "enum_values": ["летняя", "зимняя", "демисезон"]},
    ]},
    {"term": "халат", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["хлопок", "флис", "махра", "шёлк"]},
    ]},
    {"term": "носки", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "length", "label_ru": "Длина", "type": "enum", "enum_values": ["следки", "щиколотка", "гольфы", "колготки"]},
    ]},
    {"term": "колготки", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "density_den", "label_ru": "Плотность (ден)", "type": "float", "unit": "ден"},
    ]},
    {"term": "перчатки", "domain": "одежда", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["кожа", "ткань", "трикотаж", "нейлон"]},
        {"name": "lining", "label_ru": "Утеплитель", "type": "enum", "enum_values": ["флис", "шерсть", "синтепон", "без утеплителя"]},
    ]},
    {"term": "шарф", "domain": "одежда", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["шерсть", "кашемир", "шёлк", "акрил", "хлопок"]},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "берет", "domain": "одежда", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "кепка", "domain": "одежда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["бейсболка", "панамка", "фуражка", "козырёк"]},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "шапка", "domain": "одежда", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
        {"name": "season", "label_ru": "Сезон", "type": "enum", "enum_values": ["зимняя", "демисезон", "летняя"]},
    ]},

    # --- ЕДА (ещё 20) ---
    {"term": "рис", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["белый", "коричневый", "дикий", "жасминовый", "балдо"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "гречка", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["ядрица", "продел", "запаренная"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "макароны", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["спагетти", "перо", "ракушки", "лапша", "пенне"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "масло сливочное", "domain": "еда", "parameters": [
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "сыр", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["творожный", "плавленый", "твёрдый", "полутвёрдый", "мягкий"]},
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "колбаса", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["варёная", "копчёная", "сырокопчёная", "сухокопчёная", "сосиски"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "ветчина", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["варёная", "копчёная", "сырокопчёная"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "йогурт", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["натуральный", "питьевой", "с наполнителем", "греческий"]},
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "unit": "%"},
        {"name": "volume_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "творог", "domain": "еда", "parameters": [
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "сметана", "domain": "еда", "parameters": [
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "хлеб", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["белый", "чёрный", "бородинский", "батон", "буханка", "нарезной"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "батон", "domain": "еда", "parameters": [
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "булочка", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["сдобная", "с маком", "с корицей", "с вишней"]},
    ]},
    {"term": "печенье", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["песочное", "вафельное", "овсяное", "крекер"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "торт", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["бисквитный", "медовик", "наполеон", "медовик", "чизкейк"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "пирожное", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": [" эклер", "трубочка", "безе", "маффин"]},
    ]},
    {"term": "мороженое", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["пломбир", "мороженое", "фруктовый лёд", "сорбет"]},
        {"name": "fat_percent", "label_ru": "Жирность (%)", "type": "float", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "шоколад молочный", "domain": "еда", "parameters": [
        {"name": "cocoa_percent", "label_ru": "Какао (%)", "type": "float", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "шоколад тёмный", "domain": "еда", "parameters": [
        {"name": "cocoa_percent", "label_ru": "Какао (%)", "type": "float", "unit": "%"},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "конфеты", "domain": "еда", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["карамель", "шоколадные", "леденцовые", "мягкие", "нуга"]},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},

    # --- ЖИВОТНЫЕ (ещё 15) ---
    {"term": "хомяк", "domain": "животные", "parameters": [
        {"name": "species", "label_ru": "Вид", "type": "enum", "enum_values": ["сирийский", "джунгарский", "чунгари"]},
        {"name": "weight_g", "label_ru": "Масса (г)", "type": "float", "unit": "г"},
    ]},
    {"term": "кролик", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "wool_type", "label_ru": "Тип шерсти", "type": "enum", "enum_values": ["короткошёрстный", "длинношёрстный", "безшёрстный"]},
    ]},
    {"term": "попугай", "domain": "животные", "parameters": [
        {"name": "species", "label_ru": "Вид", "type": "enum", "enum_values": ["волнистый", "неразлучник", "жако", "корелла"]},
        {"name": "color", "label_ru": "Окрас", "type": "string"},
    ]},
    {"term": "канарейка", "domain": "животные", "parameters": [
        {"name": "color", "label_ru": "Окрас", "type": "string"},
        {"name": "song_type", "label_ru": "Тип песни", "type": "enum", "enum_values": ["ролевой", "фантазийный", "военный"]},
    ]},
    {"term": "человек", "domain": "животные", "parameters": [
        {"name": "age", "label_ru": "Возраст", "type": "integer"},
        {"name": "gender", "label_ru": "Пол", "type": "enum", "enum_values": ["мужской", "женский"]},
    ]},
    {"term": "корова", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "purpose", "label_ru": "Назначение", "type": "enum", "enum_values": ["молочная", "мясная", "мясомолочная"]},
    ]},
    {"term": "лошадь", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "purpose", "label_ru": "Назначение", "type": "enum", "enum_values": ["верховая", "вьючная", "упряжная"]},
    ]},
    {"term": "свинья", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "овца", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
        {"name": "purpose", "label_ru": "Назначение", "type": "enum", "enum_values": ["шёрстная", "молочная", "мясная"]},
    ]},
    {"term": "коза", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "курица", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "purpose", "label_ru": "Назначение", "type": "enum", "enum_values": ["яичная", "мясная", "декоративная"]},
    ]},
    {"term": "утка", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "гузь", "domain": "животные", "parameters": [
        {"name": "breed", "label_ru": "Порода", "type": "string"},
        {"name": "weight_kg", "label_ru": "Масса (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "крокодил", "domain": "животные", "parameters": [
        {"name": "species", "label_ru": "Вид", "type": "string"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "черепаха", "domain": "животные", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["сухопутная", "водная", "морская"]},
        {"name": "species", "label_ru": "Вид", "type": "string"},
    ]},

    # --- МЕДИЦИНА (ещё 15) ---
    {"term": "пластырь", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["бактерицидный", "хирургический", "перцовый", "обезболивающий"]},
        {"name": "size_cm", "label_ru": "Размер (см)", "type": "string"},
    ]},
    {"term": "пластырь бактерицидный", "domain": "медицина", "parameters": [
        {"name": "size_cm", "label_ru": "Размер (см)", "type": "string"},
        {"name": "quantity", "label_ru": "Количество", "type": "integer"},
    ]},
    {"term": "пластырь хирургический", "domain": "медицина", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "термометр электронный", "domain": "медицина", "parameters": [
        {"name": "accuracy_c", "label_ru": "Точность (°C)", "type": "float", "unit": "°C"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["подмышечный", "ректальный", "лобный", "ушной"]},
    ]},
    {"term": "тонометр", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["автоматический", "полуавтоматический", "механический"]},
        {"name": "cuff_size", "label_ru": "Размер манжеты", "type": "enum", "enum_values": ["детская", "взрослая", "большая"]},
    ],
    },
    {"term": "небулайзер", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["компрессорный", "ультразвуковой", "меш-небулайзер"]},
        {"name": "particle_size_mkm", "label_ru": "Размер частиц (мкм)", "type": "float", "unit": "мкм"},
    ]},
    {"term": "пульсоксиметр", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["напальчник", "настенный", "портативный"]},
    ]},
    {"term": "ингалятор", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["паровой", "компрессорный", "ультразвуковой"]},
    ]},
    {"term": "градусник", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["ртутный", "электронный", "инфракрасный"]},
    ]},
    {"term": "шприц одноразовый", "domain": "медицина", "parameters": [
        {"name": "volume_ml", "label_ru": "Объём (мл)", "type": "float", "unit": "мл"},
        {"name": "needle_gauge", "label_ru": "Диаметр иглы (G)", "type": "float", "unit": "G"},
    ]},
    {"term": "бинт стерильный", "domain": "медицина", "parameters": [
        {"name": "width_cm", "label_ru": "Ширина (см)", "type": "float", "unit": "см"},
        {"name": "length_m", "label_ru": "Длина (м)", "type": "float", "unit": "м"},
    ]},
    {"term": "жгут", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["пневматический", "эластичный", "зажим"]},
    ]},
    {"term": "носилки", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["складные", "жёсткие", "вакуумные"]},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "дефибриллятор", "domain": "медицина", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["автоматический", "полуавтоматический", "ручной"]},
        {"name": "energy_j", "label_ru": "Энергия (Дж)", "type": "float", "unit": "Дж"},
    ]},
    {"term": "монитор пациента", "domain": "медицина", "parameters": [
        {"name": "parameters", "label_ru": "Отслеживаемые параметры", "type": "string"},
        {"name": "display_size", "label_ru": "Размер экрана (дюйм)", "type": "float", "unit": "дюйм"},
    ]},

    # --- ОБОРУДОВАНИЕ (ещё 15) ---
    {"term": "сварочный инвертор", "domain": "оборудование", "parameters": [
        {"name": "current_a", "label_ru": "Ток (А)", "type": "float", "unit": "А"},
        {"name": "voltage_v", "label_ru": "Напряжение холостого хода (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "сварочная маска", "domain": "оборудование", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["автоматическая", "ручная", "пассивная"]},
        {"name": "din_range", "label_ru": "Диапазон DIN", "type": "string"},
    ]},
    {"term": "болгарка малая", "domain": "оборудование", "parameters": [
        {"name": "disc_diameter_mm", "label_ru": "Диаметр диска (мм)", "type": "float", "unit": "мм"},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "лобзик электрический", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "max_cut_mm", "label_ru": "Макс. рез (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "рубанок электрический", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "width_mm", "label_ru": "Ширина строгания (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "фрезер электрический", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "max_depth_mm", "label_ru": "Макс. глубина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "шлифовальная машина", "domain": "оборудование", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["ленточная", "орбитальная", "вибрационная", "дисковая"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "eton", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "max_depth_mm", "label_ru": "Макс. глубина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "перфоратор", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "max_drill_mm", "label_ru": "Макс. диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "impact_energy_j", "label_ru": "Энергия удара (Дж)", "type": "float", "unit": "Дж"},
    ]},
    {"term": "станок токарный", "domain": "оборудование", "parameters": [
        {"name": "max_diameter_mm", "label_ru": "Макс. диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "max_length_mm", "label_ru": "Макс. длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "фрезерный станок", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "travel_mm", "label_ru": "Ход (мм)", "type": "string"},
    ]},
    {"term": "лазерный гравёр", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность лазера (Вт)", "type": "float", "unit": "Вт"},
        {"name": "working_area_mm", "label_ru": "Рабочая область (мм)", "type": "string"},
    ]},
    {"term": "3D-принтер", "domain": "оборудование", "parameters": [
        {"name": "technology", "label_ru": "Технология", "type": "enum", "enum_values": ["FDM", "SLA", "SLS", "DLP"]},
        {"name": "build_volume_mm", "label_ru": "Объём печати (мм)", "type": "string"},
        {"name": "layer_height_mkm", "label_ru": "Высота слоя (мкм)", "type": "float", "unit": "мкм"},
    ]},
    {"term": "плазморез", "domain": "оборудование", "parameters": [
        {"name": "current_a", "label_ru": "Ток (А)", "type": "float", "unit": "А"},
        {"name": "cutting_thickness_mm", "label_ru": "Макс. толщина реза (мм)", "type": "float", "unit": "мм"},
    ]},

    # --- МУЗЫКА (ещё 30) ---
    {"term": "фортепиано", "domain": "музыка", "parameters": [
        {"name": "keys", "label_ru": "Количество клавиш", "type": "integer"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["акустическое", "цифровое", "электронное"]},
    ]},
    {"term": "пианино", "domain": "музыка", "parameters": [
        {"name": "keys", "label_ru": "Количество клавиш", "type": "integer"},
        {"name": "material", "label_ru": "Материал корпуса", "type": "string"},
    ]},
    {"term": "гитара акустическая", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["классическая", "акустическая", "фолк"]},
        {"name": "strings", "label_ru": "Количество струн", "type": "integer"},
    ]},
    {"term": "гитара электрическая", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["solo", "бас", "риторн"]},
        {"name": "strings", "label_ru": "Количество струн", "type": "integer"},
    ]},
    {"term": "бас-гитара", "domain": "музыка", "parameters": [
        {"name": "strings", "label_ru": "Количество струн", "type": "integer"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["акустическая", "электрическая"]},
    ]},
    {"term": "скрипка", "domain": "музыка", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "enum_values": ["1/16", "1/10", "1/8", "1/4", "1/2", "3/4", "4/4"]},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "альт", "domain": "музыка", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
    ]},
    {"term": "виолончель", "domain": "музыка", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "string"},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "контрабас", "domain": "музыка", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "enum_values": ["1/2", "3/4", "4/4"]},
    ]},
    {"term": "арфа", "domain": "музыка", "parameters": [
        {"name": "strings", "label_ru": "Количество струн", "type": "integer"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["педальная", "кельтская", "народная"]},
    ]},
    {"term": "кларнет", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["сопрано", "альт", "тенор", "бас"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["дерево", "абсолют", "полиэбонит"]},
    ]},
    {"term": "саксофон", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["сопрано", "альт", "тенор", "баритон", "бас"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["латунь", "серебро", "сплав"]},
    ]},
    {"term": "фагот", "domain": "музыка", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "труба", "domain": "музыка", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["латунь", "серебро", "никель-серебро"]},
        {"name": "bell_type", "label_ru": "Тип раструба", "type": "enum", "enum_values": ["переносной", "полупереносной", "непереносной"]},
    ]},
    {"term": "тромбон", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["itone", "тенор", "бас"]},
    ]},
    {"term": "валторна", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["вентильная", " 자연ная"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["латунь", "серебро"]},
    ]},
    {"term": "ударные", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["акустические", "электронные", "перкуссия"]},
    ]},
    {"term": "барабан", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["снэр", "том", "бас-бочка", "хай-хэт", "крэш"]},
        {"name": "diameter_inch", "label_ru": "Диаметр (дюйм)", "type": "float", "unit": "дюйм"},
    ]},
    {"term": "метроном", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["механический", "цифровой", "приложение"]},
    ]},
    {"term": "тангенция", "domain": "музыка", "parameters": [
        {"name": "keys", "label_ru": "Количество клавиш", "type": "integer"},
    ]},
    {"term": "аккордеон", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["певческий", "баян", "баян-аккордеон"]},
        {"name": "keys", "label_ru": "Количество клавиш", "type": "integer"},
    ]},
    {"term": "гармонь", "domain": "музыка", "parameters": [
        {"name": "keys", "label_ru": "Количество клавиш", "type": "integer"},
    ]},
    {"term": "балалайка", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["primа", "секунда", "альт", "бас"]},
        {"name": "strings", "label_ru": "Количество струн", "type": "integer"},
    ]},
    {"term": "домра", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["прима", "альт", "тенор", "бас"]},
    ]},
    {"term": "гусли", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": [" щипковые", "клавишные", "псалтерион"]},
        {"name": "strings", "label_ru": "Количество струн", "type": "integer"},
    ]},
    {"term": "свирель", "domain": "музыка", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["дерево", "металл", "пластик"]},
        {"name": "holes", "label_ru": "Количество отверстий", "type": "integer"},
    ]},
    {"term": "гармоника", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["диатоническая", "хроматическая", "блюзовая"]},
        {"name": "holes", "label_ru": "Количество отверстий", "type": "integer"},
    ]},
    {"term": "ксилофон", "domain": "музыка", "parameters": [
        {"name": "material", "label_ru": "Материал пластин", "type": "enum", "enum_values": ["дерево", "металл", "стекло"]},
        {"name": "octaves", "label_ru": "Количество октав", "type": "float"},
    ]},
    {"term": "маримба", "domain": "музыка", "parameters": [
        {"name": "octaves", "label_ru": "Количество октав", "type": "float"},
    ]},
    {"term": "вибрафон", "domain": "музыка", "parameters": [
        {"name": "octaves", "label_ru": "Количество октав", "type": "float"},
        {"name": "motor", "label_ru": "Мотор", "type": "boolean"},
    ]},
    {"term": "колокольчики", "domain": "музыка", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["оркестровые", "укулеле", "глокеншпиль"]},
    ]},

    # --- ДОПОЛНИТЕЛЬНЫЕ ПОНЯТИЯ РАЗНЫХ ДОМЕНОВ ---
    {"term": "насос", "domain": "оборудование", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["центробежный", "поршневой", "вибрационный", "погружной"]},
        {"name": "flow_rate_m3h", "label_ru": "Производительность (м³/ч)", "type": "float", "unit": "м³/ч"},
    ]},
    {"term": "генератор электрический", "domain": "оборудование", "parameters": [
        {"name": "power_kva", "label_ru": "Мощность (кВА)", "type": "float", "unit": "кВА"},
        {"name": "fuel_type", "label_ru": "Тип топлива", "type": "enum", "enum_values": ["бензин", "дизель", "газ"]},
    ]},
    {"term": "сварочный трансформатор", "domain": "оборудование", "parameters": [
        {"name": "current_a", "label_ru": "Ток (А)", "type": "float", "unit": "А"},
    ]},
    {"term": "кислородный баллон", "domain": "оборудование", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
        {"name": "pressure_mpa", "label_ru": "Давление (МПа)", "type": "float", "unit": "МПа"},
    ]},
    {"term": "аргонный баллон", "domain": "оборудование", "parameters": [
        {"name": "volume_l", "label_ru": "Объём (л)", "type": "float", "unit": "л"},
    ]},
    {"term": "дрель-шуруповёрт", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "battery_voltage", "label_ru": "Напряжение аккумулятора (В)", "type": "float", "unit": "В"},
    ]},
    {"term": "ножовка электрическая", "domain": "оборудование", "parameters": [
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
        {"name": "max_cut_mm", "label_ru": "Макс. рез (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "циркулярная пила", "domain": "оборудование", "parameters": [
        {"name": "disc_diameter_mm", "label_ru": "Диаметр диска (мм)", "type": "float", "unit": "мм"},
        {"name": "max_cut_mm", "label_ru": "Макс. глубина реза (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "торцовочная пила", "domain": "оборудование", "parameters": [
        {"name": "disc_diameter_mm", "label_ru": "Диаметр диска (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["однопильная", "двухпильная", "с протяжкой"]},
    ]},
    {"term": "рейсмус", "domain": "оборудование", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина строгания (мм)", "type": "float", "unit": "мм"},
        {"name": "height_mm", "label_ru": "Высота (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "фуговальный станок", "domain": "оборудование", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "кованая скамейка", "domain": "оборудование", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["сталь", "чугун", "алюминий"]},
    ]},
    {"term": "стол слесарный", "domain": "оборудование", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "тумба инструментальная", "domain": "оборудование", "parameters": [
        {"name": "drawers", "label_ru": "Количество ящиков", "type": "integer"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["сталь", "пластик"]},
    ]},
    {"term": "стеллаж для инструментов", "domain": "оборудование", "parameters": [
        {"name": "shelves", "label_ru": "Количество полок", "type": "integer"},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка на полку (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "ящик для инструментов", "domain": "оборудование", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["пластик", "металл", "дерево"]},
        {"name": "compartments", "label_ru": "Количество отсеков", "type": "integer"},
    ]},
    {"term": "тележка инструментальная", "domain": "оборудование", "parameters": [
        {"name": "shelves", "label_ru": "Количество полок", "type": "integer"},
        {"name": "max_load_kg", "label_ru": "Макс. нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "светильник рабочий", "domain": "оборудование", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["светодиодный", "галогенный", "люминесцентный"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "фонарь переносной", "domain": "оборудование", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["светодиодный", "галогенный", "ацетиленовый"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "колесо тележки", "domain": "оборудование", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "load_kg", "label_ru": "Грузоподъёмность (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": " ролик", "domain": "оборудование", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["колёсико", "опорный", "поворотный"]},
    ]},

    # --- ЕЩЁ 35 ПОНЯТИЙ ---
    {"term": "кран шаровой", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["латунь", "нержавеющая сталь", "полипропилен"]},
    ]},
    {"term": "вентиль", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["шаровой", "запорный", "регулирующий"]},
    ]},
    {"term": "смеситель", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["однорычажный", "двухрычажный", "сенсорный", "бесконтактный"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["латунь", "нержавеющая сталь", "керамика"]},
    ]},
    {"term": "унитаз", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["компакт", "подвесной", "с инсталляцией"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["фарфор", "фаянс"]},
    ]},
    {"term": "раковина", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["напольная", "подвесная", "врезная", "накладная"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["керамика", "стекло", "нержавеющая сталь", "камень"]},
    ]},
    {"term": "ванна", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["акриловая", "чугунная", "стальная", "стекловолокно"]},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "душевая кабина", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["угловая", "прямоугольная", "без поддона"]},
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "string"},
    ]},
    {"term": "полотенцесушитель", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["водяной", "электрический", "комбинированный"]},
        {"name": "power_watt", "label_ru": "Мощность (Вт)", "type": "float", "unit": "Вт"},
    ]},
    {"term": "зеркало в ванную", "domain": "строительство", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "backlight", "label_ru": "Подсветка", "type": "boolean"},
    ]},
    {"term": "умывальник", "domain": "строительство", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["керамика", "стекло", "камень"]},
    ]},
    {"term": "сифон", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["бутылочный", "трубный", "гофрированный"]},
    ]},
    {"term": "труба канализационная", "domain": "строительство", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "стеклопакет", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["однокамерный", "двухкамерный", "трёхкамерный"]},
        {"name": "glass_thickness_mm", "label_ru": "Толщина стекла (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "жалюзи", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["горизонтальные", "вертикальные", "ролл-жалюзи", "плisse"]},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["алюминий", "пластик", "дерево", "ткань"]},
    ]},
    {"term": "шторы", "domain": "строительство", "parameters": [
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": [" портьерные", "тюлевые", " рулонные", "шторы-плиссе", "зебра"]},
        {"name": "material", "label_ru": "Материал", "type": "string"},
    ]},
    {"term": "карниз", "domain": "строительство", "parameters": [
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["дерево", "металл", "пластик"]},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["стержневой", "потолочный", "профильный"]},
    ]},
    {"term": "настенный крюк", "domain": "крепёж", "parameters": [
        {"name": "load_kg", "label_ru": "Нагрузка (кг)", "type": "float", "unit": "кг"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["простой", "двойной", "потолочный"]},
    ]},
    {"term": "кронштейн", "domain": "крепёж", "parameters": [
        {"name": "load_kg", "label_ru": "Нагрузка (кг)", "type": "float", "unit": "кг"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["потолочный", "настенный", "угловой"]},
    ]},
    {"term": "уголок мебельный", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["сталь", "алюминий"]},
    ]},
    {"term": "уголок крепёжный", "domain": "крепёж", "parameters": [
        {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "шуруп по бетону", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "шуруп по дереву", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "шуруп по гипсокартону", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "шуруп кровельный", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "шуруп-саморез", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "гвоздь", "domain": "крепёж", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "гвоздь строительный", "domain": "крепёж", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "гвоздь финишный", "domain": "крепёж", "parameters": [
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "скоба мебельная", "domain": "крепёж", "parameters": [
        {"name": "width_mm", "label_ru": "Ширина (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["сталь", "нержавеющая сталь"]},
    ]},
    {"term": "скрепка канцелярская", "domain": "крепёж", "parameters": [
        {"name": "size", "label_ru": "Размер", "type": "enum", "enum_values": ["10", "26", "33"]},
    ]},
    {"term": "заклёпка", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
        {"name": "material", "label_ru": "Материал", "type": "enum", "enum_values": ["алюминий", "сталь", "нержавеющая сталь"]},
    ]},
    {"term": "заклёпка алюминиевая", "domain": "крепёж", "parameters": [
        {"name": "diameter_mm", "label_ru": "Диаметр (мм)", "type": "float", "unit": "мм"},
        {"name": "length_mm", "label_ru": "Длина (мм)", "type": "float", "unit": "мм"},
    ]},
    {"term": "кронштейн трубный", "domain": "крепёж", "parameters": [
        {"name": "pipe_diameter_mm", "label_ru": "Диаметр трубы (мм)", "type": "float", "unit": "мм"},
        {"name": "load_kg", "label_ru": "Нагрузка (кг)", "type": "float", "unit": "кг"},
    ]},
    {"term": "клипса для кабеля", "domain": "крепёж", "parameters": [
        {"name": "cable_diameter_mm", "label_ru": "Диаметр кабеля (мм)", "type": "float", "unit": "мм"},
        {"name": "type", "label_ru": "Тип", "type": "enum", "enum_values": ["одинарная", "двойная", "стяжка"]},
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
