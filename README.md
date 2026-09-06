# Smart Home IoT Central Monitoring & Actuation System

An End-to-End IoT Smart Home system built with Python, MQTT (HiveMQ), SQLite database, and PyQt5 graphical interface.

## System Architecture & Features
- **Edge Emulators:** Virtual DHT sensor publishing telemetry, Relay actuator, and Push Button.
- **Data Manager (`data_manager.py`):** Standalone background service processing telemetry, managing SQLite storage, and dispatching threshold alarms.
- **Local Database (`smarthome.db`):** SQLite database logging sensor readings and actuator events.
- **Central Dashboard (`main_gui.py`):** PyQt5 desktop application for live telemetry display, remote actuator toggling, alarm logging, and historical data retrieval.

## Requirements
```bash
pip install paho-mqtt PyQt5
