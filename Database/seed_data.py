"""Create the ElectroMart database: collections, indexes and sample data.

Run through Django (recommended) or directly:

    python manage.py seed_data
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
from django.contrib.auth.hashers import PBKDF2PasswordHasher

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('MONGO_DB_NAME', 'electromart_db')

CATEGORIES, BRANDS, PRODUCTS = 'categories', 'brands', 'products'
USERS = 'users'
WHOLESALE_PROFILES = 'wholesale_profiles'
STOCK_MOVEMENTS = 'stock_movements'
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
        'icon': '🔧',
        'spec_template': [
            field(
                'mcu',
                'Microcontroller',
                'select',
                '',
                [
                    'ESP32',
                    'ESP8266',
                    'ATmega328P',
                    'ATmega2560',
                    'RP2040',
                    'STM32F103',
                ],
                order=1,
            ),
            field(
                'logic_voltage',
                'Logic Voltage',
                'select',
                'V',
                ['3.3', '5'],
                order=2,
            ),
            field(
                'flash_memory',
                'Flash Memory',
                'select',
                '',
                ['32KB', '64KB', '256KB', '512KB', '2MB', '4MB', '16MB'],
                order=3,
            ),
            field(
                'connectivity',
                'Connectivity',
                'select',
                '',
                ['USB', 'WiFi', 'WiFi + Bluetooth', 'USB + WiFi'],
                order=4,
            ),
            field(
                'board_type',
                'Board Type',
                'select',
                '',
                ['Development Board', 'Microcontroller Board', 'Starter Kit'],
                order=5,
            ),
        ],
        'products': [
            (
                'ESP32 DevKit V1 WiFi Bluetooth Development Board',
                'ESP32-DEVKIT-V1',
                'Espressif',
                145000,
                180,
                {
                    'mcu': 'ESP32',
                    'logic_voltage': '3.3',
                    'flash_memory': '4MB',
                    'connectivity': 'WiFi + Bluetooth',
                    'board_type': 'Development Board',
                },
            ),
            (
                'ESP32-S3 DevKitC-1 Development Board',
                'ESP32-S3-DEVKITC1',
                'Espressif',
                235000,
                120,
                {
                    'mcu': 'ESP32',
                    'logic_voltage': '3.3',
                    'flash_memory': '16MB',
                    'connectivity': 'WiFi + Bluetooth',
                    'board_type': 'Development Board',
                },
            ),
            (
                'NodeMCU ESP8266 CP2102 Development Board',
                'NODEMCU-ESP8266',
                'NodeMCU',
                95000,
                220,
                {
                    'mcu': 'ESP8266',
                    'logic_voltage': '3.3',
                    'flash_memory': '4MB',
                    'connectivity': 'USB + WiFi',
                    'board_type': 'Development Board',
                },
            ),
            (
                'Arduino Uno R3 Compatible Development Board',
                'ARDUINO-UNO-R3',
                'Arduino',
                185000,
                160,
                {
                    'mcu': 'ATmega328P',
                    'logic_voltage': '5',
                    'flash_memory': '32KB',
                    'connectivity': 'USB',
                    'board_type': 'Microcontroller Board',
                },
            ),
            (
                'Arduino Nano V3 ATmega328P',
                'ARDUINO-NANO-V3',
                'Arduino',
                125000,
                190,
                {
                    'mcu': 'ATmega328P',
                    'logic_voltage': '5',
                    'flash_memory': '32KB',
                    'connectivity': 'USB',
                    'board_type': 'Microcontroller Board',
                },
            ),
            (
                'Arduino Mega 2560 R3 Development Board',
                'ARDUINO-MEGA2560',
                'Arduino',
                295000,
                90,
                {
                    'mcu': 'ATmega2560',
                    'logic_voltage': '5',
                    'flash_memory': '256KB',
                    'connectivity': 'USB',
                    'board_type': 'Microcontroller Board',
                },
            ),
            (
                'Raspberry Pi Pico RP2040',
                'RPI-PICO-RP2040',
                'Raspberry Pi',
                135000,
                140,
                {
                    'mcu': 'RP2040',
                    'logic_voltage': '3.3',
                    'flash_memory': '2MB',
                    'connectivity': 'USB',
                    'board_type': 'Development Board',
                },
            ),
            (
                'Raspberry Pi Pico W RP2040 WiFi',
                'RPI-PICO-W',
                'Raspberry Pi',
                185000,
                130,
                {
                    'mcu': 'RP2040',
                    'logic_voltage': '3.3',
                    'flash_memory': '2MB',
                    'connectivity': 'USB + WiFi',
                    'board_type': 'Development Board',
                },
            ),
            (
                'STM32 Blue Pill STM32F103C8T6',
                'STM32F103-BLUEPILL',
                'STMicroelectronics',
                89000,
                200,
                {
                    'mcu': 'STM32F103',
                    'logic_voltage': '3.3',
                    'flash_memory': '64KB',
                    'connectivity': 'USB',
                    'board_type': 'Development Board',
                },
            ),
            (
                'Arduino Uno Starter Kit Basic',
                'ARDUINO-UNO-KIT',
                'Arduino',
                465000,
                75,
                {
                    'mcu': 'ATmega328P',
                    'logic_voltage': '5',
                    'flash_memory': '32KB',
                    'connectivity': 'USB',
                    'board_type': 'Starter Kit',
                },
            ),
        ],
    },

    {
        'name': 'Sensors',
        'icon': '🌡️',
        'spec_template': [
            field(
                'sensor_type',
                'Sensor Type',
                'select',
                '',
                [
                    'Temperature & Humidity',
                    'Temperature',
                    'Distance',
                    'Light',
                    'Motion',
                    'Gas',
                    'Pressure',
                    'Soil Moisture',
                ],
                order=1,
            ),
            field(
                'operating_voltage',
                'Operating Voltage',
                'select',
                'V',
                ['3.3', '5', '3.3-5'],
                order=2,
            ),
            field(
                'interface',
                'Interface',
                'select',
                '',
                ['Digital', 'Analog', 'I2C', 'OneWire', 'Trigger/Echo'],
                order=3,
            ),
            field(
                'module_type',
                'Module Type',
                'select',
                '',
                ['Sensor', 'Sensor Module'],
                order=4,
            ),
        ],
        'products': [
            (
                'DHT11 Temperature and Humidity Sensor Module',
                'DHT11-MODULE',
                'Aosong',
                35000,
                350,
                {
                    'sensor_type': 'Temperature & Humidity',
                    'operating_voltage': '3.3-5',
                    'interface': 'Digital',
                    'module_type': 'Sensor Module',
                },
            ),
            (
                'DHT22 AM2302 Temperature and Humidity Sensor',
                'DHT22-AM2302',
                'Aosong',
                89000,
                260,
                {
                    'sensor_type': 'Temperature & Humidity',
                    'operating_voltage': '3.3-5',
                    'interface': 'Digital',
                    'module_type': 'Sensor',
                },
            ),
            (
                'DS18B20 Waterproof Temperature Sensor',
                'DS18B20-WATERPROOF',
                'Maxim',
                69000,
                280,
                {
                    'sensor_type': 'Temperature',
                    'operating_voltage': '3.3-5',
                    'interface': 'OneWire',
                    'module_type': 'Sensor',
                },
            ),
            (
                'HC-SR04 Ultrasonic Distance Sensor',
                'HC-SR04',
                'ElecFreaks',
                39000,
                420,
                {
                    'sensor_type': 'Distance',
                    'operating_voltage': '5',
                    'interface': 'Trigger/Echo',
                    'module_type': 'Sensor Module',
                },
            ),
            (
                'BH1750 Digital Light Sensor Module',
                'BH1750-GY30',
                'ROHM',
                49000,
                210,
                {
                    'sensor_type': 'Light',
                    'operating_voltage': '3.3-5',
                    'interface': 'I2C',
                    'module_type': 'Sensor Module',
                },
            ),
            (
                'PIR HC-SR501 Motion Sensor Module',
                'HC-SR501',
                'Generic',
                45000,
                300,
                {
                    'sensor_type': 'Motion',
                    'operating_voltage': '5',
                    'interface': 'Digital',
                    'module_type': 'Sensor Module',
                },
            ),
            (
                'MQ-2 Smoke and Gas Sensor Module',
                'MQ2-MODULE',
                'Hanwei',
                55000,
                190,
                {
                    'sensor_type': 'Gas',
                    'operating_voltage': '5',
                    'interface': 'Analog',
                    'module_type': 'Sensor Module',
                },
            ),
            (
                'BMP280 Pressure Temperature Sensor Module',
                'BMP280-MODULE',
                'Bosch',
                72000,
                170,
                {
                    'sensor_type': 'Pressure',
                    'operating_voltage': '3.3',
                    'interface': 'I2C',
                    'module_type': 'Sensor Module',
                },
            ),
            (
                'Capacitive Soil Moisture Sensor V1.2',
                'SOIL-CAP-V12',
                'Generic',
                65000,
                230,
                {
                    'sensor_type': 'Soil Moisture',
                    'operating_voltage': '3.3-5',
                    'interface': 'Analog',
                    'module_type': 'Sensor Module',
                },
            ),
            (
                'LM35 Precision Temperature Sensor',
                'LM35DZ',
                'Texas Instruments',
                42000,
                250,
                {
                    'sensor_type': 'Temperature',
                    'operating_voltage': '5',
                    'interface': 'Analog',
                    'module_type': 'Sensor',
                },
            ),
        ],
    },

    {
        'name': 'Resistors',
        'icon': '〰️',
        'spec_template': [
            field(
                'resistance',
                'Resistance',
                'select',
                'Ω',
                [
                    '100',
                    '220',
                    '330',
                    '470',
                    '1000',
                    '2200',
                    '4700',
                    '10000',
                    '47000',
                    '100000',
                ],
                order=1,
            ),
            field(
                'power',
                'Power Rating',
                'select',
                'W',
                ['0.25', '0.5', '1'],
                order=2,
            ),
            field(
                'tolerance',
                'Tolerance',
                'select',
                '%',
                ['1', '5'],
                order=3,
            ),
            field(
                'resistor_type',
                'Resistor Type',
                'select',
                '',
                ['Carbon Film', 'Metal Film'],
                order=4,
            ),
        ],
        'products': [
            (
                '100 Ohm 1/4W Metal Film Resistor 1% Pack 100',
                'RES-100R-025W',
                'Yageo',
                28000,
                500,
                {
                    'resistance': '100',
                    'power': '0.25',
                    'tolerance': '1',
                    'resistor_type': 'Metal Film',
                },
            ),
            (
                '220 Ohm 1/4W Carbon Film Resistor 5% Pack 100',
                'RES-220R-025W',
                'UniOhm',
                22000,
                650,
                {
                    'resistance': '220',
                    'power': '0.25',
                    'tolerance': '5',
                    'resistor_type': 'Carbon Film',
                },
            ),
            (
                '330 Ohm 1/4W Metal Film Resistor 1% Pack 100',
                'RES-330R-025W',
                'Yageo',
                28000,
                580,
                {
                    'resistance': '330',
                    'power': '0.25',
                    'tolerance': '1',
                    'resistor_type': 'Metal Film',
                },
            ),
            (
                '470 Ohm 1/2W Carbon Film Resistor 5% Pack 100',
                'RES-470R-05W',
                'UniOhm',
                32000,
                430,
                {
                    'resistance': '470',
                    'power': '0.5',
                    'tolerance': '5',
                    'resistor_type': 'Carbon Film',
                },
            ),
            (
                '1K Ohm 1/4W Metal Film Resistor 1% Pack 100',
                'RES-1K-025W',
                'Yageo',
                29000,
                700,
                {
                    'resistance': '1000',
                    'power': '0.25',
                    'tolerance': '1',
                    'resistor_type': 'Metal Film',
                },
            ),
            (
                '2.2K Ohm 1/4W Metal Film Resistor 1% Pack 100',
                'RES-2K2-025W',
                'Yageo',
                29000,
                460,
                {
                    'resistance': '2200',
                    'power': '0.25',
                    'tolerance': '1',
                    'resistor_type': 'Metal Film',
                },
            ),
            (
                '4.7K Ohm 1/4W Carbon Film Resistor 5% Pack 100',
                'RES-4K7-025W',
                'UniOhm',
                23000,
                490,
                {
                    'resistance': '4700',
                    'power': '0.25',
                    'tolerance': '5',
                    'resistor_type': 'Carbon Film',
                },
            ),
            (
                '10K Ohm 1/4W Metal Film Resistor 1% Pack 100',
                'RES-10K-025W',
                'Yageo',
                29000,
                800,
                {
                    'resistance': '10000',
                    'power': '0.25',
                    'tolerance': '1',
                    'resistor_type': 'Metal Film',
                },
            ),
            (
                '47K Ohm 1/2W Carbon Film Resistor 5% Pack 100',
                'RES-47K-05W',
                'UniOhm',
                33000,
                370,
                {
                    'resistance': '47000',
                    'power': '0.5',
                    'tolerance': '5',
                    'resistor_type': 'Carbon Film',
                },
            ),
            (
                '100K Ohm 1W Metal Film Resistor 1% Pack 50',
                'RES-100K-1W',
                'Vishay',
                45000,
                310,
                {
                    'resistance': '100000',
                    'power': '1',
                    'tolerance': '1',
                    'resistor_type': 'Metal Film',
                },
            ),
        ],
    },

    {
        'name': 'Capacitors',
        'icon': '🔋',
        'spec_template': [
            field(
                'capacitance',
                'Capacitance',
                'select',
                '',
                [
                    '100nF',
                    '1uF',
                    '10uF',
                    '22uF',
                    '47uF',
                    '100uF',
                    '220uF',
                    '470uF',
                    '1000uF',
                    '2200uF',
                ],
                order=1,
            ),
            field(
                'voltage_rating',
                'Voltage Rating',
                'select',
                'V',
                ['16', '25', '35', '50'],
                order=2,
            ),
            field(
                'capacitor_type',
                'Capacitor Type',
                'select',
                '',
                ['Ceramic', 'Electrolytic'],
                order=3,
            ),
            field(
                'mounting',
                'Mounting',
                'select',
                '',
                ['Through Hole'],
                order=4,
            ),
        ],
        'products': [
            (
                '100nF 50V Ceramic Capacitor Pack 50',
                'CAP-100NF-50V',
                'Murata',
                35000,
                420,
                {
                    'capacitance': '100nF',
                    'voltage_rating': '50',
                    'capacitor_type': 'Ceramic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '1uF 50V Electrolytic Capacitor Pack 20',
                'CAP-1UF-50V',
                'Nichicon',
                32000,
                360,
                {
                    'capacitance': '1uF',
                    'voltage_rating': '50',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '10uF 25V Electrolytic Capacitor Pack 20',
                'CAP-10UF-25V',
                'Nichicon',
                34000,
                390,
                {
                    'capacitance': '10uF',
                    'voltage_rating': '25',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '22uF 25V Electrolytic Capacitor Pack 20',
                'CAP-22UF-25V',
                'Panasonic',
                36000,
                340,
                {
                    'capacitance': '22uF',
                    'voltage_rating': '25',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '47uF 25V Electrolytic Capacitor Pack 20',
                'CAP-47UF-25V',
                'Panasonic',
                38000,
                320,
                {
                    'capacitance': '47uF',
                    'voltage_rating': '25',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '100uF 25V Electrolytic Capacitor Pack 20',
                'CAP-100UF-25V',
                'Nichicon',
                42000,
                300,
                {
                    'capacitance': '100uF',
                    'voltage_rating': '25',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '220uF 25V Electrolytic Capacitor Pack 10',
                'CAP-220UF-25V',
                'Rubycon',
                39000,
                280,
                {
                    'capacitance': '220uF',
                    'voltage_rating': '25',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '470uF 25V Electrolytic Capacitor Pack 10',
                'CAP-470UF-25V',
                'Rubycon',
                49000,
                240,
                {
                    'capacitance': '470uF',
                    'voltage_rating': '25',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '1000uF 35V Electrolytic Capacitor Pack 5',
                'CAP-1000UF-35V',
                'Panasonic',
                55000,
                200,
                {
                    'capacitance': '1000uF',
                    'voltage_rating': '35',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
            (
                '2200uF 35V Electrolytic Capacitor Pack 5',
                'CAP-2200UF-35V',
                'Nichicon',
                75000,
                170,
                {
                    'capacitance': '2200uF',
                    'voltage_rating': '35',
                    'capacitor_type': 'Electrolytic',
                    'mounting': 'Through Hole',
                },
            ),
        ],
    },

    {
        'name': 'Power & Regulators',
        'icon': '⚡',
        'spec_template': [
            field(
                'regulator_type',
                'Type',
                'select',
                '',
                [
                    'Linear Regulator',
                    'Buck Converter',
                    'Boost Converter',
                    'Buck-Boost Converter',
                    'Power Module',
                ],
                order=1,
            ),
            field(
                'input_voltage',
                'Input Voltage',
                'select',
                '',
                ['5-12V', '7-35V', '4.5-40V', '2-24V', '3-35V'],
                order=2,
            ),
            field(
                'output_voltage',
                'Output Voltage',
                'select',
                '',
                ['3.3V', '5V', '9V', '12V', 'Adjustable'],
                order=3,
            ),
            field(
                'max_current',
                'Maximum Current',
                'select',
                'A',
                ['1', '1.5', '2', '3', '5'],
                order=4,
            ),
            field(
                'package',
                'Package',
                'select',
                '',
                ['TO-220', 'Module'],
                order=5,
            ),
        ],
        'products': [
            (
                'LM7805 5V Linear Voltage Regulator TO-220',
                'LM7805',
                'STMicroelectronics',
                18000,
                600,
                {
                    'regulator_type': 'Linear Regulator',
                    'input_voltage': '7-35V',
                    'output_voltage': '5V',
                    'max_current': '1',
                    'package': 'TO-220',
                },
            ),
            (
                'LM7809 9V Linear Voltage Regulator TO-220',
                'LM7809',
                'STMicroelectronics',
                19000,
                420,
                {
                    'regulator_type': 'Linear Regulator',
                    'input_voltage': '7-35V',
                    'output_voltage': '9V',
                    'max_current': '1',
                    'package': 'TO-220',
                },
            ),
            (
                'LM7812 12V Linear Voltage Regulator TO-220',
                'LM7812',
                'STMicroelectronics',
                19000,
                450,
                {
                    'regulator_type': 'Linear Regulator',
                    'input_voltage': '7-35V',
                    'output_voltage': '12V',
                    'max_current': '1',
                    'package': 'TO-220',
                },
            ),
            (
                'AMS1117 3.3V Voltage Regulator Module',
                'AMS1117-33-MOD',
                'Advanced Monolithic Systems',
                25000,
                380,
                {
                    'regulator_type': 'Linear Regulator',
                    'input_voltage': '5-12V',
                    'output_voltage': '3.3V',
                    'max_current': '1',
                    'package': 'Module',
                },
            ),
            (
                'LM2596 Adjustable Buck Converter Module',
                'LM2596-BUCK',
                'Texas Instruments',
                45000,
                330,
                {
                    'regulator_type': 'Buck Converter',
                    'input_voltage': '4.5-40V',
                    'output_voltage': 'Adjustable',
                    'max_current': '3',
                    'package': 'Module',
                },
            ),
            (
                'XL4015 5A Adjustable Buck Converter Module',
                'XL4015-BUCK',
                'XLSEMI',
                75000,
                240,
                {
                    'regulator_type': 'Buck Converter',
                    'input_voltage': '4.5-40V',
                    'output_voltage': 'Adjustable',
                    'max_current': '5',
                    'package': 'Module',
                },
            ),
            (
                'MT3608 Adjustable Boost Converter Module',
                'MT3608-BOOST',
                'Aerosemi',
                32000,
                410,
                {
                    'regulator_type': 'Boost Converter',
                    'input_voltage': '2-24V',
                    'output_voltage': 'Adjustable',
                    'max_current': '2',
                    'package': 'Module',
                },
            ),
            (
                'XL6009 Adjustable Boost Converter Module',
                'XL6009-BOOST',
                'XLSEMI',
                55000,
                270,
                {
                    'regulator_type': 'Boost Converter',
                    'input_voltage': '3-35V',
                    'output_voltage': 'Adjustable',
                    'max_current': '3',
                    'package': 'Module',
                },
            ),
            (
                'DC-DC Buck Boost Converter Adjustable Module',
                'LTC3780-BUCKBOOST',
                'Analog Devices',
                185000,
                110,
                {
                    'regulator_type': 'Buck-Boost Converter',
                    'input_voltage': '5-12V',
                    'output_voltage': 'Adjustable',
                    'max_current': '5',
                    'package': 'Module',
                },
            ),
            (
                'MB102 Breadboard Power Supply Module 3.3V 5V',
                'MB102-POWER',
                'YwRobot',
                35000,
                360,
                {
                    'regulator_type': 'Power Module',
                    'input_voltage': '5-12V',
                    'output_voltage': '5V',
                    'max_current': '1',
                    'package': 'Module',
                },
            ),
        ],
    },
]

DESC = ('{name} is authentic, imported directly from authorized distributors. '
        'Includes full original box, full manufacturer warranty, and ElectroMart\'s premium support. '
        'In stock at our main warehouse, ready for same-day delivery with a 7-day return policy.')

# --------------------------------------------------------------- datasheets

DATASHEET_URLS = {
    'ESP32-DEVKIT-V1':
        'https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf',

    'ESP32-S3-DEVKITC1':
        'https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf',

    'NODEMCU-ESP8266':
        'https://www.espressif.com/sites/default/files/documentation/0a-esp8266ex_datasheet_en.pdf',

    'ARDUINO-UNO-R3':
        'https://www.microchip.com/en-us/product/ATmega328P',

    'ARDUINO-MEGA2560':
        'https://www.microchip.com/en-us/product/ATmega2560',

    'RPI-PICO-RP2040':
        'https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf',

    'STM32F103-BLUEPILL':
        'https://www.st.com/resource/en/datasheet/stm32f103c8.pdf',

    'BMP280-MODULE':
        'https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf',

    'LM35DZ':
        'https://www.ti.com/lit/ds/symlink/lm35.pdf',

    'LM7805':
        'https://www.st.com/resource/en/datasheet/l78.pdf',

    'LM2596-BUCK':
        'https://www.ti.com/lit/ds/symlink/lm2596.pdf',
}

# --------------------------------------------------------------- demo accounts

DEMO_PASSWORD = 'Demo@123'

ACCOUNT_DATA = [
    {
        'full_name': 'ElectroMart Admin',
        'email': 'admin@electromart.com',
        'role': 'admin',
    },

    # 7 retail customers
    {
        'full_name': 'Nguyen Van An',
        'email': 'retail1@electromart.com',
        'role': 'retail',
    },
    {
        'full_name': 'Tran Minh Bao',
        'email': 'retail2@electromart.com',
        'role': 'retail',
    },
    {
        'full_name': 'Le Hoang Gia',
        'email': 'retail3@electromart.com',
        'role': 'retail',
    },
    {
        'full_name': 'Pham Quoc Huy',
        'email': 'retail4@electromart.com',
        'role': 'retail',
    },
    {
        'full_name': 'Vo Thanh Nam',
        'email': 'retail5@electromart.com',
        'role': 'retail',
    },
    {
        'full_name': 'Bui Minh Khang',
        'email': 'retail6@electromart.com',
        'role': 'retail',
    },
    {
        'full_name': 'Do Gia Linh',
        'email': 'retail7@electromart.com',
        'role': 'retail',
    },

    # 3 approved wholesale customers
    {
        'full_name': 'Nguyen Duc Long',
        'email': 'wholesale1@electromart.com',
        'role': 'wholesale',
        'wholesale': {
            'company_name': 'Long Electronics Co., Ltd',
            'tax_code': '0312345001',
            'company_address': 'Ho Chi Minh City',
            'contact_person': 'Nguyen Duc Long',
            'approval_status': 'approved',
        },
    },
    {
        'full_name': 'Tran Quoc Viet',
        'email': 'wholesale2@electromart.com',
        'role': 'wholesale',
        'wholesale': {
            'company_name': 'Viet Automation Co., Ltd',
            'tax_code': '0312345002',
            'company_address': 'Binh Duong',
            'contact_person': 'Tran Quoc Viet',
            'approval_status': 'approved',
        },
    },
    {
        'full_name': 'Le Minh Phat',
        'email': 'wholesale3@electromart.com',
        'role': 'wholesale',
        'wholesale': {
            'company_name': 'Phat Embedded Solutions',
            'tax_code': '0312345003',
            'company_address': 'Dong Nai',
            'contact_person': 'Le Minh Phat',
            'approval_status': 'approved',
        },
    },

    # Pending B2B application: role remains retail until an admin approves it.
    {
        'full_name': 'Pham Tuan Kiet',
        'email': 'wholesale.pending@electromart.com',
        'role': 'retail',
        'wholesale': {
            'company_name': 'Kiet IoT Technology',
            'tax_code': '0312345004',
            'company_address': 'Ho Chi Minh City',
            'contact_person': 'Pham Tuan Kiet',
            'approval_status': 'pending',
        },
    },
]


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


import zlib

def generate_product_svg(name, part, cat_name):
    # Deterministic colors based on part number
    h = zlib.adler32(part.encode('utf-8'))
    hue1 = h % 360
    hue2 = (hue1 + 40) % 360
    
    color1 = f"hsl({hue1}, 70%, 45%)"
    color2 = f"hsl({hue2}, 80%, 35%)"
    
    if cat_name == 'Microcontrollers & Kits':
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100%" height="100%">
  <defs>
    <linearGradient id="g_{part}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f2027" />
      <stop offset="100%" stop-color="#203a43" />
    </linearGradient>
    <pattern id="pcb_grid" width="10" height="10" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.8" fill="#4a5568" opacity="0.3" />
    </pattern>
  </defs>
  <rect width="200" height="200" rx="12" fill="url(#g_{part})" />
  <rect width="200" height="200" fill="url(#pcb_grid)" />
  <!-- Circuit board tracks -->
  <path d="M 25 35 L 75 35 L 90 50 L 90 90" fill="none" stroke="#00b4d8" stroke-width="1.5" opacity="0.6" stroke-linecap="round" />
  <path d="M 175 165 L 125 165 L 110 150 L 110 110" fill="none" stroke="#00b4d8" stroke-width="1.5" opacity="0.6" stroke-linecap="round" />
  <path d="M 30 170 L 60 140 L 60 110" fill="none" stroke="#ecc94b" stroke-width="1.2" opacity="0.5" stroke-linecap="round" />
  <path d="M 170 30 L 140 60 L 140 90" fill="none" stroke="#ecc94b" stroke-width="1.2" opacity="0.5" stroke-linecap="round" />
  <!-- Board Outline -->
  <rect x="40" y="40" width="120" height="120" rx="6" fill="#1b2e3c" stroke="#2b6cb0" stroke-width="2.5" />
  <!-- CPU Chip -->
  <rect x="75" y="75" width="50" height="50" rx="4" fill="#111" stroke="#4a5568" stroke-width="1.5" />
  <rect x="83" y="83" width="34" height="34" rx="2" fill="#2d3748" />
  <!-- CPU Pins -->
  <rect x="78" y="70" width="4" height="5" fill="#e2e8f0" /><rect x="88" y="70" width="4" height="5" fill="#e2e8f0" /><rect x="98" y="70" width="4" height="5" fill="#e2e8f0" /><rect x="108" y="70" width="4" height="5" fill="#e2e8f0" /><rect x="118" y="70" width="4" height="5" fill="#e2e8f0" />
  <rect x="78" y="125" width="4" height="5" fill="#e2e8f0" /><rect x="88" y="125" width="4" height="5" fill="#e2e8f0" /><rect x="98" y="125" width="4" height="5" fill="#e2e8f0" /><rect x="108" y="125" width="4" height="5" fill="#e2e8f0" /><rect x="118" y="125" width="4" height="5" fill="#e2e8f0" />
  <rect x="70" y="78" width="5" height="4" fill="#e2e8f0" /><rect x="70" y="88" width="5" height="4" fill="#e2e8f0" /><rect x="70" y="98" width="5" height="4" fill="#e2e8f0" /><rect x="70" y="108" width="5" height="4" fill="#e2e8f0" /><rect x="70" y="118" width="5" height="4" fill="#e2e8f0" />
  <rect x="125" y="78" width="5" height="4" fill="#e2e8f0" /><rect x="125" y="88" width="5" height="4" fill="#e2e8f0" /><rect x="125" y="98" width="5" height="4" fill="#e2e8f0" /><rect x="125" y="108" width="5" height="4" fill="#e2e8f0" /><rect x="125" y="118" width="5" height="4" fill="#e2e8f0" />
  <!-- USB Type-C Port -->
  <rect x="85" y="32" width="30" height="12" rx="2" fill="#718096" stroke="#4a5568" stroke-width="1" />
  <rect x="90" y="30" width="20" height="3" fill="#cbd5e0" />
  <!-- Header pins -->
  <rect x="46" y="48" width="6" height="104" rx="1" fill="#2d3748" />
  <path d="M 49 52 L 49 148" stroke="#ecc94b" stroke-dasharray="1,5" stroke-width="3" stroke-linecap="round" />
  <rect x="148" y="48" width="6" height="104" rx="1" fill="#2d3748" />
  <path d="M 151 52 L 151 148" stroke="#ecc94b" stroke-dasharray="1,5" stroke-width="3" stroke-linecap="round" />
  <!-- Capacitor -->
  <circle cx="130" cy="58" r="7" fill="#e53e3e" />
  <circle cx="130" cy="58" r="5" fill="#c53030" />
  <rect x="128" y="53" width="4" height="10" fill="#fff" opacity="0.3" />
  <!-- Crystal oscillator -->
  <rect x="62" y="60" width="16" height="8" rx="3" fill="#a0aec0" stroke="#718096" stroke-width="1" />
  <!-- Text branding -->
  <text x="100" y="145" fill="#ffffff" font-family="sans-serif" font-size="8" font-weight="bold" text-anchor="middle">{part}</text>
  <text x="100" y="154" fill="#a0aec0" font-family="sans-serif" font-size="6.5" text-anchor="middle">{name[:22]}</text>
</svg>"""
    elif cat_name == 'Sensors':
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100%" height="100%">
  <defs>
    <linearGradient id="g_{part}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#141e30" />
      <stop offset="100%" stop-color="#243b55" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="12" fill="url(#g_{part})" />
  <!-- Gold circuit paths -->
  <path d="M 30 30 L 70 70 L 70 130 L 30 170" fill="none" stroke="#d69e2e" stroke-width="1.5" opacity="0.3" />
  <path d="M 170 30 L 130 70 L 130 130 L 170 170" fill="none" stroke="#d69e2e" stroke-width="1.5" opacity="0.3" />
  <!-- Sensor Board -->
  <rect x="45" y="40" width="110" height="120" rx="8" fill="#2d3748" stroke="#4a5568" stroke-width="2" />
  <!-- Metallic Sensor Chamber -->
  <circle cx="100" cy="90" r="38" fill="#1a202c" stroke="#718096" stroke-width="3" />
  <!-- Inner sensor grill -->
  <circle cx="100" cy="90" r="28" fill="none" stroke="#ecc94b" stroke-width="1.5" stroke-dasharray="4,3" />
  <circle cx="100" cy="90" r="18" fill="none" stroke="#a0aec0" stroke-width="1" stroke-dasharray="2,2" />
  <circle cx="100" cy="90" r="8" fill="#e53e3e" opacity="0.8" />
  <!-- Detection waves -->
  <path d="M 85 45 A 25 25 0 0 1 115 45" fill="none" stroke="#48bb78" stroke-width="2" opacity="0.8" stroke-linecap="round" />
  <path d="M 75 35 A 40 40 0 0 1 125 35" fill="none" stroke="#48bb78" stroke-width="1.5" opacity="0.5" stroke-linecap="round" />
  <!-- Interface Pins -->
  <rect x="75" y="158" width="6" height="14" rx="1" fill="#ecc94b" />
  <rect x="91" y="158" width="6" height="14" rx="1" fill="#ecc94b" />
  <rect x="107" y="158" width="6" height="14" rx="1" fill="#ecc94b" />
  <rect x="123" y="158" width="6" height="14" rx="1" fill="#ecc94b" />
  <!-- Labels -->
  <text x="100" y="142" fill="#ffffff" font-family="sans-serif" font-size="8.5" font-weight="bold" text-anchor="middle">{part}</text>
  <text x="100" y="151" fill="#a0aec0" font-family="sans-serif" font-size="6.5" text-anchor="middle">{name[:24]}</text>
</svg>"""
    elif cat_name == 'Resistors':
        # Different bands depending on part number
        band_colors = ["#b7791f", "#2d3748", "#c53030", "#d69e2e", "#2b6cb0", "#6b46c1"]
        b1 = band_colors[h % len(band_colors)]
        b2 = band_colors[(h >> 2) % len(band_colors)]
        b3 = band_colors[(h >> 4) % len(band_colors)]
        
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100%" height="100%">
  <defs>
    <linearGradient id="g_{part}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2c3e50" />
      <stop offset="100%" stop-color="#4ca1af" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="12" fill="url(#g_{part})" />
  <!-- PCB connection points -->
  <circle cx="20" cy="100" r="6" fill="#cbd5e0" stroke="#718096" stroke-width="2" />
  <circle cx="180" cy="100" r="6" fill="#cbd5e0" stroke="#718096" stroke-width="2" />
  <!-- Lead wires -->
  <line x1="20" y1="100" x2="180" y2="100" stroke="#e2e8f0" stroke-width="5" stroke-linecap="round" />
  <line x1="20" y1="100" x2="180" y2="100" stroke="#a0aec0" stroke-width="2" stroke-linecap="round" />
  <!-- Resistor Body with detailed shape -->
  <path d="M 50 85 C 50 72, 60 72, 65 74 C 70 76, 130 76, 135 74 C 140 72, 150 72, 150 85 L 150 115 C 150 128, 140 128, 135 126 C 130 124, 70 124, 65 126 C 60 128, 50 128, 50 115 Z" fill="#eed9b3" stroke="#c09665" stroke-width="2.5" />
  <!-- Color Bands -->
  <rect x="65" y="74.5" width="10" height="51" fill="{b1}" />
  <rect x="85" y="75" width="10" height="50" fill="{b2}" />
  <rect x="105" y="75" width="10" height="50" fill="{b3}" />
  <rect x="130" y="74.5" width="10" height="51" fill="#d69e2e" /> <!-- Gold tolerance band -->
  <!-- Text overlays -->
  <text x="100" y="55" fill="#ffffff" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="middle">{part}</text>
  <text x="100" y="152" fill="#ffffff" font-family="sans-serif" font-size="8" opacity="0.9" text-anchor="middle">{name[:24]}</text>
</svg>"""
    elif cat_name == 'Capacitors':
        # Capacitor body color
        body_colors = ["#1a202c", "#1d3557", "#2e6f40", "#78281f"]
        b_col = body_colors[h % len(body_colors)]
        
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100%" height="100%">
  <defs>
    <linearGradient id="g_{part}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#11998e" />
      <stop offset="100%" stop-color="#38ef7d" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="12" fill="url(#g_{part})" />
  <!-- Lead wires -->
  <line x1="85" y1="130" x2="85" y2="175" stroke="#cbd5e0" stroke-width="4.5" stroke-linecap="round" />
  <line x1="115" y1="130" x2="115" y2="160" stroke="#cbd5e0" stroke-width="4.5" stroke-linecap="round" />
  
  <!-- Cylinder body -->
  <rect x="62" y="35" width="76" height="98" rx="6" fill="{b_col}" stroke="#2d3748" stroke-width="2.5" />
  <!-- Top Vent cap cap -->
  <ellipse cx="100" cy="35" rx="38" ry="10" fill="#718096" stroke="#2d3748" stroke-width="2" />
  <!-- Vent cross emboss -->
  <line x1="90" y1="35" x2="110" y2="35" stroke="#4a5568" stroke-width="2.5" />
  <line x1="100" y1="30" x2="100" y2="40" stroke="#4a5568" stroke-width="2.5" />
  
  <!-- Negative side indicator band -->
  <rect x="114" y="44" width="20" height="88" fill="#e2e8f0" opacity="0.95" />
  <!-- minus signs inside the band -->
  <text x="124" y="65" fill="#c53030" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">-</text>
  <text x="124" y="92" fill="#c53030" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">-</text>
  <text x="124" y="119" fill="#c53030" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">-</text>
  
  <text x="88" y="84" fill="#ffffff" font-family="sans-serif" font-size="9.5" font-weight="bold" text-anchor="middle" transform="rotate(-90 88 84)">{part}</text>
  <text x="100" y="152" fill="#1a202c" font-family="sans-serif" font-size="7.5" font-weight="bold" text-anchor="middle">{name[:25]}</text>
</svg>"""
    else: # Power & Regulators
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100%" height="100%">
  <defs>
    <linearGradient id="g_{part}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fc4a1a" />
      <stop offset="100%" stop-color="#f7b733" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="12" fill="url(#g_{part})" />
  <!-- Metal Heatsink Tab -->
  <rect x="65" y="32" width="70" height="40" rx="4" fill="#a0aec0" stroke="#718096" stroke-width="2" />
  <!-- Screw hole in heatsink -->
  <circle cx="100" cy="50" r="10" fill="#1a202c" stroke="#718096" stroke-width="2.5" />
  
  <!-- Regulator Body TO-220 shape -->
  <rect x="55" y="65" width="90" height="65" rx="3" fill="#1a202c" stroke="#4a5568" stroke-width="2.5" />
  <!-- Heatsink grooves / details -->
  <line x1="65" y1="80" x2="135" y2="80" stroke="#2d3748" stroke-width="3" />
  <line x1="65" y1="95" x2="135" y2="95" stroke="#2d3748" stroke-width="3" />
  
  <!-- Three thick lead wires -->
  <rect x="68" y="130" width="8" height="45" rx="1.5" fill="#cbd5e0" stroke="#718096" stroke-width="1" />
  <rect x="96" y="130" width="8" height="45" rx="1.5" fill="#cbd5e0" stroke="#718096" stroke-width="1" />
  <rect x="124" y="130" width="8" height="45" rx="1.5" fill="#cbd5e0" stroke="#718096" stroke-width="1" />
  
  <text x="100" y="115" fill="#ffffff" font-family="sans-serif" font-size="9" font-weight="bold" text-anchor="middle">{part}</text>
  <text x="100" y="152" fill="#ffffff" font-family="sans-serif" font-size="7.5" opacity="0.9" text-anchor="middle">{name[:25]}</text>
</svg>"""
    return svg



def seed_accounts(db):
    """Insert the 12 CV43 demo accounts and 4 wholesale profiles."""
    hasher = PBKDF2PasswordHasher()
    admin_id = None
    user_ids = {}

    for account in ACCOUNT_DATA:
        email = account['email'].strip().lower()

        user_doc = {
            'full_name': account['full_name'],
            'email': email,
            'password_hash': hasher.encode(DEMO_PASSWORD, hasher.salt()),
            'role': account['role'],
            'is_active': True,
            'is_hidden': False,
            'email_verified': True,
            'avatar_url': '',
            'failed_login_count': 0,
            'locked_until': None,
            'created_at': NOW,
            'updated_at': NOW,
        }

        result = db[USERS].insert_one(user_doc)
        user_ids[email] = result.inserted_id

        if account['role'] == 'admin':
            admin_id = result.inserted_id

    for account in ACCOUNT_DATA:
        wholesale = account.get('wholesale')
        if not wholesale:
            continue

        email = account['email'].strip().lower()
        status = wholesale['approval_status']

        profile_doc = {
            'user_id': user_ids[email],
            'company_name': wholesale['company_name'],
            'tax_code': wholesale['tax_code'],
            'company_address': wholesale['company_address'],
            'contact_person': wholesale['contact_person'],
            'approval_status': status,
            'reject_reason': '',
            'submitted_at': NOW,
            'reviewed_at': NOW if status == 'approved' else None,
            'reviewed_by': admin_id if status == 'approved' else None,
        }
        db[WHOLESALE_PROFILES].insert_one(profile_doc)

    print(
        'Inserted %d demo accounts and %d wholesale profiles. '
        'Password: %s'
        % (
            len(ACCOUNT_DATA),
            sum(1 for account in ACCOUNT_DATA if account.get('wholesale')),
            DEMO_PASSWORD,
        )
    )


def seed(keep=False):
    rnd = random.Random(2026)
    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[DB_NAME]

    if not keep:
        for c in (CATEGORIES, BRANDS, PRODUCTS, WHOLESALE_PROFILES, USERS, STOCK_MOVEMENTS):
            db[c].delete_many({})
        print('Cleared existing documents.')

    ensure_indexes(db)
    print('Indexes ready.')

    seed_accounts(db)

    names = sorted({p[2] for c in CATEGORY_DATA for p in c['products']})
    brand_ids = {n: db[BRANDS].insert_one(
        {'name': n, 'slug': slugify(n), 'country': '', 'logo': ''}).inserted_id
        for n in names}
    print('Inserted %d brands.' % len(brand_ids))

    # Ensure directory exists for product-specific unique SVGs
    img_dir = os.path.join(os.path.dirname(__file__), '..', 'Frontend', 'static', 'sales_payment', 'images', 'prods')
    os.makedirs(img_dir, exist_ok=True)

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
            
            # Generate a unique SVG image for each electronic component
            img_filename = f"prod_{slugify(part)}.svg"

            svg_content = generate_product_svg(
                name,
                part,
                cat['name'],
            )

            img_path = os.path.join(
                img_dir,
                img_filename,
            )

            with open(img_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

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
                'images': [f'/static/sales_payment/images/prods/{img_filename}'],
                'datasheet_url': DATASHEET_URLS.get(part, ''),
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