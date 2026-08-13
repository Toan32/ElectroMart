"""Create the ElectroMart database: collections, indexes and sample data.

Run it directly, no Django needed:

    python Database/seed_data.py            # wipe and reseed
    python Database/seed_data.py --keep     # keep existing documents

Connection settings come from the environment, falling back to a local server:
    MONGO_URI       default mongodb://localhost:27017/
    MONGO_DB_NAME   default electromart_db

Every category declares its own `spec_template`. That declaration is what the
storefront turns into a dynamic filter panel, so the shape of the data drives
the user interface rather than hard-coded code.
"""
import argparse
import os
import random
import unicodedata
from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient, TEXT

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('MONGO_DB_NAME', 'electromart_db')

CATEGORIES, BRANDS, PRODUCTS = 'categories', 'brands', 'products'
NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)

SYMBOLS = {'Ω': 'ohm', 'µ': 'u', 'μ': 'u', '%': 'pct', '°': 'deg'}


def slugify(text):
    """ASCII-only slug.

    Unicode letters such as the ohm sign are alphanumeric to Python, but
    Django's <slug> converter only accepts [-a-zA-Z0-9_], so they must be
    translated instead of kept.
    """
    for sym, word in SYMBOLS.items():
        text = text.replace(sym, ' %s ' % word)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    slug = ''.join(c if ('a' <= c <= 'z' or '0' <= c <= '9') else '-' for c in text.lower())
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-')


def field(key, label, dtype, unit='', values=None, filterable=True, order=0):
    return {'key': key, 'label': label, 'data_type': dtype, 'unit': unit,
            'allowed_values': values or [], 'is_filterable': filterable,
            'display_order': order}


# --------------------------------------------------------------- categories
CATEGORY_DATA = [
    {
        'name': 'Microcontrollers & Kits',
        'icon': '\U0001f9e0',
        'spec_template': [
            field('core', 'Core', 'select', '',
                  ['ARM Cortex-M0', 'ARM Cortex-M3', 'ARM Cortex-M4',
                   'AVR 8-bit', 'Xtensa LX6', 'Xtensa LX7', 'RISC-V'], order=1),
            field('clock_speed_mhz', 'Clock speed', 'number', 'MHz', order=2),
            field('flash_kb', 'Flash memory', 'number', 'KB', order=3),
            field('ram_kb', 'RAM', 'number', 'KB', order=4),
            field('gpio_count', 'GPIO pins', 'number', 'pins', order=5),
            field('wifi', 'Wi-Fi', 'boolean', '', order=6),
            field('bluetooth', 'Bluetooth', 'boolean', '', order=7),
            field('operating_voltage_v', 'Operating voltage', 'number', 'V', order=8),
        ],
        'products': [
            ('ESP32-WROOM-32 DevKit V1', 'ESP32-DEVKITC-32E', 'Espressif', 165000, 320,
             {'core': 'Xtensa LX6', 'clock_speed_mhz': 240, 'flash_kb': 4096, 'ram_kb': 520,
              'gpio_count': 34, 'wifi': True, 'bluetooth': True, 'operating_voltage_v': 3.3}),
            ('ESP32-S3 DevKitC-1 N16R8', 'ESP32-S3-DEVKITC-1', 'Espressif', 295000, 140,
             {'core': 'Xtensa LX7', 'clock_speed_mhz': 240, 'flash_kb': 16384, 'ram_kb': 512,
              'gpio_count': 45, 'wifi': True, 'bluetooth': True, 'operating_voltage_v': 3.3}),
            ('ESP8266 NodeMCU Lua V3', 'NODEMCU-V3', 'Espressif', 89000, 410,
             {'core': 'Xtensa LX6', 'clock_speed_mhz': 80, 'flash_kb': 4096, 'ram_kb': 80,
              'gpio_count': 17, 'wifi': True, 'bluetooth': False, 'operating_voltage_v': 3.3}),
            ('ESP32-C3 SuperMini Board', 'ESP32-C3-MINI', 'Espressif', 78000, 260,
             {'core': 'RISC-V', 'clock_speed_mhz': 160, 'flash_kb': 4096, 'ram_kb': 400,
              'gpio_count': 13, 'wifi': True, 'bluetooth': True, 'operating_voltage_v': 3.3}),
            ('Arduino Uno R3 (original)', 'A000066', 'Arduino', 585000, 60,
             {'core': 'AVR 8-bit', 'clock_speed_mhz': 16, 'flash_kb': 32, 'ram_kb': 2,
              'gpio_count': 20, 'wifi': False, 'bluetooth': False, 'operating_voltage_v': 5.0}),
            ('Arduino Uno R3 (compatible, CH340)', 'UNO-R3-CH340', 'OEM', 125000, 520,
             {'core': 'AVR 8-bit', 'clock_speed_mhz': 16, 'flash_kb': 32, 'ram_kb': 2,
              'gpio_count': 20, 'wifi': False, 'bluetooth': False, 'operating_voltage_v': 5.0}),
            ('Arduino Nano V3 CH340', 'NANO-V3-CH340', 'OEM', 72000, 640,
             {'core': 'AVR 8-bit', 'clock_speed_mhz': 16, 'flash_kb': 32, 'ram_kb': 2,
              'gpio_count': 22, 'wifi': False, 'bluetooth': False, 'operating_voltage_v': 5.0}),
            ('Arduino Mega 2560 R3', 'MEGA2560-R3', 'OEM', 235000, 180,
             {'core': 'AVR 8-bit', 'clock_speed_mhz': 16, 'flash_kb': 256, 'ram_kb': 8,
              'gpio_count': 54, 'wifi': False, 'bluetooth': False, 'operating_voltage_v': 5.0}),
            ('STM32F103C8T6 Blue Pill', 'STM32F103C8T6', 'STMicroelectronics', 68000, 380,
             {'core': 'ARM Cortex-M3', 'clock_speed_mhz': 72, 'flash_kb': 64, 'ram_kb': 20,
              'gpio_count': 37, 'wifi': False, 'bluetooth': False, 'operating_voltage_v': 3.3}),
            ('STM32F411CEU6 Black Pill', 'STM32F411CEU6', 'STMicroelectronics', 148000, 150,
             {'core': 'ARM Cortex-M4', 'clock_speed_mhz': 100, 'flash_kb': 512, 'ram_kb': 128,
              'gpio_count': 32, 'wifi': False, 'bluetooth': False, 'operating_voltage_v': 3.3}),
            ('Raspberry Pi Pico', 'RP2-PICO', 'Raspberry Pi', 115000, 240,
             {'core': 'ARM Cortex-M0', 'clock_speed_mhz': 133, 'flash_kb': 2048, 'ram_kb': 264,
              'gpio_count': 26, 'wifi': False, 'bluetooth': False, 'operating_voltage_v': 3.3}),
            ('Raspberry Pi Pico W', 'RP2-PICO-W', 'Raspberry Pi', 168000, 190,
             {'core': 'ARM Cortex-M0', 'clock_speed_mhz': 133, 'flash_kb': 2048, 'ram_kb': 264,
              'gpio_count': 26, 'wifi': True, 'bluetooth': True, 'operating_voltage_v': 3.3}),
        ],
    },
    {
        'name': 'Sensors',
        'icon': '\U0001f4e1',
        'spec_template': [
            field('sensor_type', 'Sensor type', 'select', '',
                  ['Temperature & Humidity', 'Distance', 'Motion', 'Light',
                   'Gas', 'Accelerometer & Gyroscope', 'Pressure', 'Current'], order=1),
            field('interface', 'Interface', 'select', '',
                  ['I2C', 'SPI', 'UART', 'Analog', 'Digital', '1-Wire'], order=2),
            field('supply_voltage_v', 'Supply voltage', 'number', 'V', order=3),
            field('operating_temp_min_c', 'Min operating temperature', 'number', 'C', order=4),
            field('digital_output', 'Digital output', 'boolean', '', order=5),
        ],
        'products': [
            ('DHT22 / AM2302 Temperature & Humidity Sensor', 'DHT22', 'Aosong', 68000, 420,
             {'sensor_type': 'Temperature & Humidity', 'interface': '1-Wire', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': -40, 'digital_output': True}),
            ('DHT11 Temperature & Humidity Sensor', 'DHT11', 'Aosong', 22000, 780,
             {'sensor_type': 'Temperature & Humidity', 'interface': '1-Wire', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': 0, 'digital_output': True}),
            ('DS18B20 Waterproof Temperature Probe', 'DS18B20-WP', 'Maxim', 35000, 560,
             {'sensor_type': 'Temperature & Humidity', 'interface': '1-Wire', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': -55, 'digital_output': True}),
            ('BMP280 Barometric Pressure Sensor', 'BMP280', 'Bosch', 42000, 340,
             {'sensor_type': 'Pressure', 'interface': 'I2C', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': -40, 'digital_output': True}),
            ('BME280 Environmental Sensor', 'BME280', 'Bosch', 96000, 210,
             {'sensor_type': 'Pressure', 'interface': 'I2C', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': -40, 'digital_output': True}),
            ('HC-SR04 Ultrasonic Distance Sensor', 'HC-SR04', 'OEM', 25000, 900,
             {'sensor_type': 'Distance', 'interface': 'Digital', 'supply_voltage_v': 5.0,
              'operating_temp_min_c': -15, 'digital_output': True}),
            ('VL53L0X Laser Distance Sensor', 'VL53L0X', 'STMicroelectronics', 118000, 130,
             {'sensor_type': 'Distance', 'interface': 'I2C', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': -20, 'digital_output': True}),
            ('HC-SR501 PIR Motion Sensor', 'HC-SR501', 'OEM', 28000, 640,
             {'sensor_type': 'Motion', 'interface': 'Digital', 'supply_voltage_v': 5.0,
              'operating_temp_min_c': -15, 'digital_output': True}),
            ('BH1750 Digital Light Sensor', 'BH1750FVI', 'ROHM', 38000, 290,
             {'sensor_type': 'Light', 'interface': 'I2C', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': -40, 'digital_output': True}),
            ('LDR 5mm Photoresistor Module', 'LDR-5528', 'OEM', 9000, 1200,
             {'sensor_type': 'Light', 'interface': 'Analog', 'supply_voltage_v': 5.0,
              'operating_temp_min_c': -30, 'digital_output': False}),
            ('MQ-2 Smoke & Flammable Gas Sensor', 'MQ-2', 'Hanwei', 34000, 380,
             {'sensor_type': 'Gas', 'interface': 'Analog', 'supply_voltage_v': 5.0,
              'operating_temp_min_c': -20, 'digital_output': True}),
            ('MQ-135 Air Quality Sensor', 'MQ-135', 'Hanwei', 45000, 220,
             {'sensor_type': 'Gas', 'interface': 'Analog', 'supply_voltage_v': 5.0,
              'operating_temp_min_c': -20, 'digital_output': True}),
            ('MPU-6050 Accelerometer & Gyroscope', 'MPU-6050', 'InvenSense', 48000, 470,
             {'sensor_type': 'Accelerometer & Gyroscope', 'interface': 'I2C', 'supply_voltage_v': 3.3,
              'operating_temp_min_c': -40, 'digital_output': True}),
            ('ACS712 30A Current Sensor', 'ACS712-30A', 'Allegro', 52000, 260,
             {'sensor_type': 'Current', 'interface': 'Analog', 'supply_voltage_v': 5.0,
              'operating_temp_min_c': -40, 'digital_output': False}),
        ],
    },
    {
        'name': 'Resistors',
        'icon': '\U0001f39a',
        'spec_template': [
            field('resistance_ohm', 'Resistance', 'number', 'ohm', order=1),
            field('tolerance_percent', 'Tolerance', 'select', '%', ['1', '5'], order=2),
            field('power_rating_w', 'Power rating', 'select', 'W',
                  ['0.125', '0.25', '0.5', '1', '2', '5'], order=3),
            field('package', 'Package', 'select', '',
                  ['Through-hole', 'SMD 0805', 'SMD 1206'], order=4),
            field('material', 'Material', 'select', '',
                  ['Carbon film', 'Metal film', 'Wirewound'], order=5),
        ],
        'products': [
            ('220 ohm 1/4W 5% Resistor (100 pcs)', 'R-220R-025W', 'Royal Ohm', 15000, 1500,
             {'resistance_ohm': 220, 'tolerance_percent': '5', 'power_rating_w': '0.25',
              'package': 'Through-hole', 'material': 'Carbon film'}),
            ('330 ohm 1/4W 5% Resistor (100 pcs)', 'R-330R-025W', 'Royal Ohm', 15000, 1350,
             {'resistance_ohm': 330, 'tolerance_percent': '5', 'power_rating_w': '0.25',
              'package': 'Through-hole', 'material': 'Carbon film'}),
            ('1k ohm 1/4W 1% Resistor (100 pcs)', 'R-1K-025W-1P', 'Royal Ohm', 22000, 1800,
             {'resistance_ohm': 1000, 'tolerance_percent': '1', 'power_rating_w': '0.25',
              'package': 'Through-hole', 'material': 'Metal film'}),
            ('4.7k ohm 1/4W 5% Resistor (100 pcs)', 'R-4K7-025W', 'Royal Ohm', 15000, 1100,
             {'resistance_ohm': 4700, 'tolerance_percent': '5', 'power_rating_w': '0.25',
              'package': 'Through-hole', 'material': 'Carbon film'}),
            ('10k ohm 1/4W 1% Resistor (100 pcs)', 'R-10K-025W-1P', 'Royal Ohm', 22000, 2100,
             {'resistance_ohm': 10000, 'tolerance_percent': '1', 'power_rating_w': '0.25',
              'package': 'Through-hole', 'material': 'Metal film'}),
            ('100k ohm 1/4W 5% Resistor (100 pcs)', 'R-100K-025W', 'Royal Ohm', 15000, 950,
             {'resistance_ohm': 100000, 'tolerance_percent': '5', 'power_rating_w': '0.25',
              'package': 'Through-hole', 'material': 'Carbon film'}),
            ('1M ohm 1/4W 5% Resistor (100 pcs)', 'R-1M-025W', 'Royal Ohm', 15000, 600,
             {'resistance_ohm': 1000000, 'tolerance_percent': '5', 'power_rating_w': '0.25',
              'package': 'Through-hole', 'material': 'Carbon film'}),
            ('SMD 0805 10k ohm 1% Resistor (100 pcs)', 'R-SMD0805-10K', 'Yageo', 18000, 880,
             {'resistance_ohm': 10000, 'tolerance_percent': '1', 'power_rating_w': '0.125',
              'package': 'SMD 0805', 'material': 'Metal film'}),
            ('SMD 1206 1k ohm 1% Resistor (100 pcs)', 'R-SMD1206-1K', 'Yageo', 20000, 720,
             {'resistance_ohm': 1000, 'tolerance_percent': '1', 'power_rating_w': '0.25',
              'package': 'SMD 1206', 'material': 'Metal film'}),
            ('10 ohm 5W Ceramic Power Resistor', 'R-10R-5W', 'OEM', 4500, 460,
             {'resistance_ohm': 10, 'tolerance_percent': '5', 'power_rating_w': '5',
              'package': 'Through-hole', 'material': 'Wirewound'}),
            ('100 ohm 2W Power Resistor', 'R-100R-2W', 'OEM', 2500, 540,
             {'resistance_ohm': 100, 'tolerance_percent': '5', 'power_rating_w': '2',
              'package': 'Through-hole', 'material': 'Metal film'}),
            ('47 ohm 1W Resistor (50 pcs)', 'R-47R-1W', 'Royal Ohm', 19000, 380,
             {'resistance_ohm': 47, 'tolerance_percent': '5', 'power_rating_w': '1',
              'package': 'Through-hole', 'material': 'Metal film'}),
        ],
    },
    {
        'name': 'Capacitors',
        'icon': '⚡',
        'spec_template': [
            field('capacitance_uf', 'Capacitance', 'number', 'uF', order=1),
            field('voltage_rating_v', 'Voltage rating', 'number', 'V', order=2),
            field('dielectric', 'Dielectric', 'select', '',
                  ['Electrolytic', 'Ceramic', 'Tantalum', 'Film'], order=3),
            field('package', 'Package', 'select', '',
                  ['Through-hole', 'SMD 0805', 'SMD 1206'], order=4),
            field('low_esr', 'Low ESR', 'boolean', '', order=5),
        ],
        'products': [
            ('1000uF 25V Electrolytic Capacitor', 'C-1000UF-25V', 'Rubycon', 3500, 620,
             {'capacitance_uf': 1000, 'voltage_rating_v': 25, 'dielectric': 'Electrolytic',
              'package': 'Through-hole', 'low_esr': True}),
            ('470uF 16V Electrolytic Capacitor', 'C-470UF-16V', 'Rubycon', 2200, 840,
             {'capacitance_uf': 470, 'voltage_rating_v': 16, 'dielectric': 'Electrolytic',
              'package': 'Through-hole', 'low_esr': True}),
            ('220uF 25V Electrolytic Capacitor', 'C-220UF-25V', 'Samwha', 1800, 900,
             {'capacitance_uf': 220, 'voltage_rating_v': 25, 'dielectric': 'Electrolytic',
              'package': 'Through-hole', 'low_esr': False}),
            ('100uF 50V Electrolytic Capacitor', 'C-100UF-50V', 'Samwha', 1500, 760,
             {'capacitance_uf': 100, 'voltage_rating_v': 50, 'dielectric': 'Electrolytic',
              'package': 'Through-hole', 'low_esr': False}),
            ('10uF 63V Electrolytic Capacitor', 'C-10UF-63V', 'Samwha', 900, 1050,
             {'capacitance_uf': 10, 'voltage_rating_v': 63, 'dielectric': 'Electrolytic',
              'package': 'Through-hole', 'low_esr': False}),
            ('0.1uF (104) 50V Ceramic Capacitor (100 pcs)', 'C-104-50V', 'Murata', 12000, 1600,
             {'capacitance_uf': 0.1, 'voltage_rating_v': 50, 'dielectric': 'Ceramic',
              'package': 'Through-hole', 'low_esr': True}),
            ('22pF 50V Ceramic Capacitor (100 pcs)', 'C-22PF-50V', 'Murata', 10000, 980,
             {'capacitance_uf': 0.000022, 'voltage_rating_v': 50, 'dielectric': 'Ceramic',
              'package': 'Through-hole', 'low_esr': True}),
            ('SMD 0805 1uF 25V Capacitor (100 pcs)', 'C-SMD0805-1UF', 'Samsung', 16000, 540,
             {'capacitance_uf': 1, 'voltage_rating_v': 25, 'dielectric': 'Ceramic',
              'package': 'SMD 0805', 'low_esr': True}),
            ('SMD 1206 10uF 16V Capacitor (50 pcs)', 'C-SMD1206-10UF', 'Samsung', 24000, 410,
             {'capacitance_uf': 10, 'voltage_rating_v': 16, 'dielectric': 'Ceramic',
              'package': 'SMD 1206', 'low_esr': True}),
            ('10uF 16V Tantalum Capacitor', 'C-TANT-10UF-16V', 'KEMET', 5500, 320,
             {'capacitance_uf': 10, 'voltage_rating_v': 16, 'dielectric': 'Tantalum',
              'package': 'SMD 1206', 'low_esr': True}),
            ('0.22uF 400V Film Capacitor', 'C-FILM-224-400V', 'WIMA', 8500, 240,
             {'capacitance_uf': 0.22, 'voltage_rating_v': 400, 'dielectric': 'Film',
              'package': 'Through-hole', 'low_esr': False}),
        ],
    },
    {
        'name': 'Power & Regulators',
        'icon': '\U0001f50b',
        'spec_template': [
            field('output_voltage_v', 'Output voltage', 'number', 'V', order=1),
            field('output_current_a', 'Max output current', 'number', 'A', order=2),
            field('input_voltage_max_v', 'Max input voltage', 'number', 'V', order=3),
            field('module_type', 'Module type', 'select', '',
                  ['Linear LDO', 'Buck (step-down)', 'Boost (step-up)',
                   'Buck-Boost', 'AC Adapter'], order=4),
            field('adjustable', 'Adjustable output', 'boolean', '', order=5),
        ],
        'products': [
            ('LM7805 5V Regulator TO-220 (10 pcs)', 'LM7805-TO220', 'STMicroelectronics', 28000, 680,
             {'output_voltage_v': 5.0, 'output_current_a': 1.0, 'input_voltage_max_v': 35,
              'module_type': 'Linear LDO', 'adjustable': False}),
            ('LM7812 12V Regulator TO-220 (10 pcs)', 'LM7812-TO220', 'STMicroelectronics', 28000, 420,
             {'output_voltage_v': 12.0, 'output_current_a': 1.0, 'input_voltage_max_v': 35,
              'module_type': 'Linear LDO', 'adjustable': False}),
            ('AMS1117-3.3V SMD Regulator (20 pcs)', 'AMS1117-3.3', 'AMS', 18000, 920,
             {'output_voltage_v': 3.3, 'output_current_a': 1.0, 'input_voltage_max_v': 15,
              'module_type': 'Linear LDO', 'adjustable': False}),
            ('LM2596 Adjustable Buck Converter', 'LM2596-ADJ', 'Texas Instruments', 32000, 740,
             {'output_voltage_v': 12.0, 'output_current_a': 3.0, 'input_voltage_max_v': 40,
              'module_type': 'Buck (step-down)', 'adjustable': True}),
            ('MP1584EN Mini Buck Converter', 'MP1584EN', 'MPS', 24000, 560,
             {'output_voltage_v': 5.0, 'output_current_a': 3.0, 'input_voltage_max_v': 28,
              'module_type': 'Buck (step-down)', 'adjustable': True}),
            ('XL4015 5A Buck Converter with Display', 'XL4015-5A', 'XLSEMI', 68000, 230,
             {'output_voltage_v': 12.0, 'output_current_a': 5.0, 'input_voltage_max_v': 38,
              'module_type': 'Buck (step-down)', 'adjustable': True}),
            ('XL6009 4A Boost Converter', 'XL6009', 'XLSEMI', 35000, 380,
             {'output_voltage_v': 24.0, 'output_current_a': 4.0, 'input_voltage_max_v': 32,
              'module_type': 'Boost (step-up)', 'adjustable': True}),
            ('MT3608 2A Boost Converter', 'MT3608', 'Aerosemi', 18000, 640,
             {'output_voltage_v': 12.0, 'output_current_a': 2.0, 'input_voltage_max_v': 24,
              'module_type': 'Boost (step-up)', 'adjustable': True}),
            ('5V 2A AC Adapter, 5.5mm jack', 'ADP-5V2A', 'OEM', 65000, 310,
             {'output_voltage_v': 5.0, 'output_current_a': 2.0, 'input_voltage_max_v': 240,
              'module_type': 'AC Adapter', 'adjustable': False}),
            ('12V 5A AC Adapter, 5.5mm jack', 'ADP-12V5A', 'OEM', 145000, 160,
             {'output_voltage_v': 12.0, 'output_current_a': 5.0, 'input_voltage_max_v': 240,
              'module_type': 'AC Adapter', 'adjustable': False}),
            ('TP4056 Type-C Lithium Charger Module', 'TP4056-TYPEC', 'NanJing', 12000, 1150,
             {'output_voltage_v': 4.2, 'output_current_a': 1.0, 'input_voltage_max_v': 8,
              'module_type': 'Buck-Boost', 'adjustable': False}),
        ],
    },
]

DESC = ('{name} is stocked by ElectroMart from authorised distributors and checked '
        'before shipping. Suitable for study projects, prototypes and production use. '
        'In stock at our warehouse, with a 7-day return window for manufacturing defects.')


def ensure_indexes(db):
    """Create every index described in the Design Document."""
    db[CATEGORIES].create_index([('slug', ASCENDING)], unique=True)
    db[CATEGORIES].create_index([('parent_id', ASCENDING)])
    db[CATEGORIES].create_index([('ancestors', ASCENDING)])

    db[BRANDS].create_index([('slug', ASCENDING)], unique=True)

    p = db[PRODUCTS]
    p.create_index([('slug', ASCENDING)], unique=True)
    p.create_index([('part_number', ASCENDING)], unique=True)
    # Main index for the category listing page
    p.create_index([('category_id', ASCENDING), ('is_hidden', ASCENDING),
                    ('min_price', ASCENDING)], name='cat_hidden_price')
    # Full-text search
    p.create_index([('name', TEXT), ('part_number', TEXT),
                    ('description', TEXT), ('tags', TEXT)],
                   name='product_text', default_language='none')
    # Wildcard index for the dynamic specification filter: each category uses a
    # different set of keys, so they cannot be listed in advance.
    p.create_index([('specifications.$**', ASCENDING)], name='spec_wildcard')
    p.create_index([('brand_id', ASCENDING)])
    p.create_index([('is_featured', ASCENDING), ('sold_count', DESCENDING)])
    p.create_index([('variants.sku', ASCENDING)])


def seed(keep=False):
    rnd = random.Random(2026)
    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[DB_NAME]

    if not keep:
        for c in (CATEGORIES, BRANDS, PRODUCTS):
            db[c].delete_many({})
        print('Cleared existing documents.')

    ensure_indexes(db)
    print('Indexes ready.')

    names = sorted({p[2] for c in CATEGORY_DATA for p in c['products']})
    brand_ids = {n: db[BRANDS].insert_one(
        {'name': n, 'slug': slugify(n), 'country': '', 'logo': ''}).inserted_id
        for n in names}
    print('Inserted %d brands.' % len(brand_ids))

    total = 0
    for order, cat in enumerate(CATEGORY_DATA, 1):
        cat_id = db[CATEGORIES].insert_one({
            'name': cat['name'],
            'slug': slugify(cat['name']),
            'parent_id': None,
            'ancestors': [],
            'level': 0,
            'icon': cat['icon'],
            'description': '',
            'display_order': order,
            'is_hidden': False,
            'spec_template': cat['spec_template'],
        }).inserted_id

        docs = []
        for i, (name, part, brand, price, stock, specs) in enumerate(cat['products']):
            # A higher list price so the storefront can show a discount badge
            has_sale = i % 3 != 2
            list_price = int(price * rnd.choice([1.15, 1.2, 1.25, 1.3])) if has_sale else price
            list_price = int(round(list_price / 1000.0) * 1000)

            variant = {
                'sku': part + '-01',
                'option_name': 'Standard',
                'retail_price': price,
                'list_price': list_price,
                'price_tiers': [
                    {'min_qty': 1, 'price': price},
                    {'min_qty': 10, 'price': int(price * 0.92 // 1000 * 1000)},
                    {'min_qty': 50, 'price': int(price * 0.85 // 1000 * 1000)},
                ],
                'stock_qty': stock,
                'reorder_level': 30,
                'warehouse_location': 'A%d-%02d' % (order, i + 1),
            }
            rating_count = rnd.randint(0, 180)
            docs.append({
                'name': name,
                'part_number': part,
                'slug': slugify(name + '-' + part),
                'category_id': cat_id,
                'brand_id': brand_ids[brand],
                'description': DESC.format(name=name),
                'specifications': specs,
                'variants': [variant],
                'min_price': price,
                'list_price': list_price,
                'total_stock': stock,
                'images': [],
                'datasheet_url': '',
                'tags': [part.lower(), slugify(brand), slugify(cat['name'])],
                'avg_rating': round(rnd.uniform(3.8, 5.0), 1) if rating_count else 0.0,
                'rating_count': rating_count,
                'sold_count': rnd.randint(20, 900),
                'is_featured': i < 3,
                'is_hidden': False,
                'created_at': NOW - timedelta(days=rnd.randint(0, 120)),
            })
        db[PRODUCTS].insert_many(docs)
        total += len(docs)
        print('  %-26s %2d products' % (cat['name'], len(docs)))

    print('Done: %d categories, %d brands, %d products in "%s".'
          % (len(CATEGORY_DATA), len(brand_ids), total, DB_NAME))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Seed the ElectroMart MongoDB database')
    ap.add_argument('--keep', action='store_true', help='keep existing documents')
    seed(**vars(ap.parse_args()))
