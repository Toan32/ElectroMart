"""
Update the six seeded ElectroMart news articles with full article content.

Safe one-off script:
- DOES NOT wipe or reseed the database.
- DOES NOT create duplicate news documents.
- Updates only existing news documents matched by slug.

Run from the project root:
    python Database/update_news_content.py

Connection settings:
    MONGO_URI       default mongodb://localhost:27017/
    MONGO_DB_NAME   default electromart_db
"""

import os
from datetime import datetime, timezone

from pymongo import MongoClient


MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://localhost:27017/",
)

DB_NAME = os.environ.get(
    "MONGO_DB_NAME",
    "electromart_db",
)

NEWS_COLLECTION = "news"


NEWS_CONTENT = {
    "electromart-launches-new-stm32-development-kits": """
ElectroMart is expanding its development board catalogue with a new selection of STM32 development kits for students, makers and embedded-system developers.

The new boards are designed to make prototyping easier, whether you are learning microcontrollers for the first time or building a more advanced IoT, automation or robotics project. Customers can compare available kits by processor family, memory, connectivity and supported peripherals before choosing the right board for their application.

STM32 development boards are suitable for projects such as sensor monitoring, motor control, smart devices, data logging and industrial prototypes. Many boards also provide accessible GPIO headers that make it easier to connect displays, sensors and other modules.

Visit the ElectroMart catalogue to explore the latest STM32 development kits, check specifications and find compatible electronic components for your next project.
""".strip(),

    "scheduled-system-maintenance-this-weekend": """
ElectroMart will perform scheduled system maintenance this weekend to improve website stability, security and overall performance.

During the maintenance period, some services may be temporarily unavailable or respond more slowly than usual. Customers may experience interruptions when browsing products, signing in, managing their account or checking order information.

Existing customer data and orders will remain safely stored during the maintenance process. Our technical team will work to restore all services as quickly as possible.

We recommend completing any urgent purchases or account changes before the maintenance window. Thank you for your patience and understanding while we continue improving the ElectroMart shopping experience.
""".strip(),

    "how-to-choose-the-right-capacitor-for-your-project": """
Choosing the correct capacitor is important for the reliability and performance of an electronic circuit. Before purchasing a capacitor, you should consider its capacitance, voltage rating, tolerance, type and operating conditions.

Capacitance indicates how much electrical charge the component can store and is normally measured in farads, microfarads, nanofarads or picofarads. The required value depends on the role of the capacitor in your circuit, such as filtering, timing, coupling or power stabilization.

The voltage rating should always be equal to or higher than the maximum voltage expected in the circuit. Using a capacitor below the required voltage rating may cause unstable operation or damage the component.

Different capacitor types are also suitable for different applications. Ceramic capacitors are commonly used for high-frequency filtering and decoupling, while electrolytic capacitors are often used when larger capacitance values are required.

Always check the component specifications and your circuit requirements before making a selection. ElectroMart product pages provide technical information to help you compare compatible capacitor options.
""".strip(),

    "new-sensor-modules-added-to-our-catalogue": """
ElectroMart has added a new range of sensor modules to help developers build smarter monitoring, automation and IoT projects.

The expanded catalogue includes modules designed for measuring environmental and physical conditions such as temperature, humidity, pressure and motion. These modules can be used in applications including smart homes, weather stations, security systems, robotics and classroom projects.

When choosing a sensor module, customers should consider factors such as measurement range, accuracy, operating voltage, communication interface and compatibility with their development platform.

Many sensor modules can be integrated with popular microcontroller and development boards, allowing developers to quickly collect real-world data and use it in their applications.

Browse the ElectroMart sensor catalogue to compare available modules and find the components that best match your project requirements.
""".strip(),

    "holiday-shipping-schedule-update": """
ElectroMart is updating its shipping schedule for the upcoming holiday period.

Due to increased order volume and changes to courier operating schedules, some orders may require additional processing or delivery time. We recommend placing important orders early to reduce the possibility of delays.

Orders that have already been confirmed will continue to be processed in the order they were received. Customers can use their ElectroMart account to review order information and follow available delivery updates.

Normal processing and shipping schedules will resume after the holiday period.

Thank you for choosing ElectroMart. We appreciate your understanding and wish all of our customers a safe and enjoyable holiday.
""".strip(),

    "understanding-resistor-color-codes": """
Resistor color codes provide a quick way to identify the resistance value and tolerance of through-hole resistors.

Most common resistors use four or five colored bands. For a standard four-band resistor, the first two bands represent significant digits, the third band is the multiplier and the fourth band indicates tolerance.

For example, a resistor with brown, black, red and gold bands represents 1,000 ohms, or 1 kΩ, with a tolerance of ±5%.

Common digit colors are:
Black = 0
Brown = 1
Red = 2
Orange = 3
Yellow = 4
Green = 5
Blue = 6
Violet = 7
Grey = 8
White = 9

Tolerance bands are also important. Gold commonly represents ±5%, while silver represents ±10%. Some precision resistors use additional bands to provide more accurate resistance values.

Understanding resistor color codes can help you quickly identify components during prototyping, repair and circuit assembly. When accuracy is critical, you can also verify the resistor value with a multimeter before installing it.
""".strip(),
}


def main():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    # Fail early if MongoDB is unavailable.
    client.admin.command("ping")

    db = client[DB_NAME]
    collection = db[NEWS_COLLECTION]

    now = datetime.now(timezone.utc)

    updated = 0
    missing = []

    print(
        f'Updating ElectroMart news content in database "{DB_NAME}"...'
    )

    for slug, content in NEWS_CONTENT.items():
        result = collection.update_one(
            {"slug": slug},
            {
                "$set": {
                    "content": content,
                    "updated_at": now,
                }
            },
        )

        if result.matched_count == 1:
            updated += 1
            print(f"[OK] {slug}")
        else:
            missing.append(slug)
            print(f"[MISSING] {slug}")

    print()
    print(
        f"Finished: {updated}/{len(NEWS_CONTENT)} article(s) matched and updated."
    )

    if missing:
        print(
            "These slugs were not found in MongoDB:"
        )
        for slug in missing:
            print(f"  - {slug}")

        print(
            "\nNo missing document was created automatically, "
            "so existing News data remains safe."
        )


if __name__ == "__main__":
    main()
