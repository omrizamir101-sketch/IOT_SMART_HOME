import sys
import sqlite3
import json
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, 
    QGroupBox, QHeaderView
)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor

# הגדרות רשת וטופיקים
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_DHT = "pr/home/OZ_4637_dht/sts"
TOPIC_RELAY = "pr/home/OZ_4637_relay/sts"
TOPIC_ALARMS = "pr/home/OZ_4637/alarms"
DB_NAME = "smarthome.db"

class MqttBridge(QObject):
    msg_received = pyqtSignal(str, str)

class MainSmartHomeGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Home IoT Central Monitor - OZ_4637")
        self.setGeometry(150, 150, 850, 650)
        
        self.bridge = MqttBridge()
        self.bridge.msg_received.connect(self.handle_mqtt_message)
        
        self.relay_state = 0
        self.init_ui()
        self.init_mqtt()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. אזור ניטור נתוני חיישנים
        telemetry_group = QGroupBox("Real-Time Telemetry & Devices")
        telemetry_layout = QHBoxLayout()

        self.lbl_temp = QLabel("Temperature: -- °C")
        self.lbl_temp.setFont(QFont("Arial", 14, QFont.Bold))
        self.lbl_temp.setStyleSheet("color: #2b5797; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")

        self.lbl_hum = QLabel("Humidity: -- %")
        self.lbl_hum.setFont(QFont("Arial", 14, QFont.Bold))
        self.lbl_hum.setStyleSheet("color: #1e7145; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")

        self.lbl_relay = QLabel("Relay Status: OFF")
        self.lbl_relay.setFont(QFont("Arial", 14, QFont.Bold))
        self.lbl_relay.setStyleSheet("color: gray; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")

        telemetry_layout.addWidget(self.lbl_temp)
        telemetry_layout.addWidget(self.lbl_hum)
        telemetry_layout.addWidget(self.lbl_relay)
        telemetry_group.setLayout(telemetry_layout)
        main_layout.addWidget(telemetry_group)

        # 2. אזור שליטה בממסר
        control_group = QGroupBox("Actuator Control")
        control_layout = QHBoxLayout()
        self.btn_toggle_relay = QPushButton("Toggle Relay (On / Off)")
        self.btn_toggle_relay.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_toggle_relay.setStyleSheet("background-color: #0078d7; color: white; padding: 8px; border-radius: 5px;")
        self.btn_toggle_relay.clicked.connect(self.toggle_relay)
        control_layout.addWidget(self.btn_toggle_relay)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        # 3. חלון התראות וסטטוס (Alarms & Logs)
        alarm_group = QGroupBox("System Status & Alarms Log")
        alarm_layout = QVBoxLayout()
        self.txt_alarms = QTextEdit()
        self.txt_alarms.setReadOnly(True)
        self.txt_alarms.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 11pt;")
        alarm_layout.addWidget(self.txt_alarms)
        alarm_group.setLayout(alarm_layout)
        main_layout.addWidget(alarm_group)

        # 4. תצוגת מסד נתונים (SQLite History)
        db_group = QGroupBox("Local DB Telemetry History (smarthome.db)")
        db_layout = QVBoxLayout()
        self.btn_refresh_db = QPushButton("Refresh Data from SQLite")
        self.btn_refresh_db.clicked.connect(self.load_db_data)
        db_layout.addWidget(self.btn_refresh_db)

        self.table_db = QTableWidget()
        self.table_db.setColumnCount(4)
        self.table_db.setHorizontalHeaderLabels(["ID", "Timestamp", "Temperature (°C)", "Humidity (%)"])
        self.table_db.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        db_layout.addWidget(self.table_db)
        db_group.setLayout(db_layout)
        main_layout.addWidget(db_group)

    def init_mqtt(self):
        self.client = mqtt.Client("OZ_4637_MainGUI")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            self.log_message("[System INFO] Connected to MQTT Broker successfully.")
        except Exception as e:
            self.log_message(f"[System ERROR] MQTT Connection failed: {e}")

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe([(TOPIC_DHT, 0), (TOPIC_RELAY, 0), (TOPIC_ALARMS, 0)])

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8')
        self.bridge.msg_received.emit(msg.topic, payload)

    def handle_mqtt_message(self, topic, payload):
        if topic == TOPIC_DHT:
            try:
                if "Temperature:" in payload:
                    parts = payload.split()
                    t = parts[1]
                    h = parts[3]
                else:
                    d = json.loads(payload)
                    t = d.get("temperature", "--")
                    h = d.get("humidity", "--")

                self.lbl_temp.setText(f"Temperature: {t} °C")
                self.lbl_hum.setText(f"Humidity: {h} %")
            except Exception:
                pass

        elif topic == TOPIC_RELAY:
            if payload in ["1", "on", "ON"]:
                self.relay_state = 1
                self.lbl_relay.setText("Relay Status: ON")
                self.lbl_relay.setStyleSheet("color: white; background-color: green; padding: 10px; font-weight: bold; border-radius: 5px;")
                self.log_message("[Event INFO] Relay turned ON")
            else:
                self.relay_state = 0
                self.lbl_relay.setText("Relay Status: OFF")
                self.lbl_relay.setStyleSheet("color: white; background-color: gray; padding: 10px; font-weight: bold; border-radius: 5px;")
                self.log_message("[Event INFO] Relay turned OFF")

        elif topic == TOPIC_ALARMS:
            try:
                alarm = json.loads(payload)
                sev = alarm.get("severity", "Info")
                msg = alarm.get("msg", payload)
                if sev == "Critical":
                    self.log_message(f"[ALARM CRITICAL] {msg}", "#ff4d4d")
                elif sev == "Warning":
                    self.log_message(f"[WARNING] {msg}", "#ffa500")
                else:
                    self.log_message(f"[INFO] {msg}", "#00ff00")
            except Exception:
                self.log_message(f"[ALARM] {payload}", "#ff4d4d")

    def toggle_relay(self):
        new_val = "0" if self.relay_state == 1 else "1"
        self.client.publish(TOPIC_RELAY, new_val)

    def log_message(self, message, color_hex="#00ff00"):
        self.txt_alarms.append(f"<span style='color:{color_hex};'>{message}</span>")

    def load_db_data(self):
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, temperature, humidity FROM telemetry ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()

            self.table_db.setRowCount(0)
            for row_idx, row_data in enumerate(rows):
                self.table_db.insertRow(row_idx)
                for col_idx, col_value in enumerate(row_data):
                    self.table_db.setItem(row_idx, col_idx, QTableWidgetItem(str(col_value)))
            self.log_message("[DB INFO] Successfully refreshed 10 latest records from SQLite.")
        except Exception as e:
            self.log_message(f"[DB ERROR] Could not read from DB: {e}", "#ff4d4d")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainSmartHomeGUI()
    window.show()
    sys.exit(app.exec_())