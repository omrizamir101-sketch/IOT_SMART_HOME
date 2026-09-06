import sqlite3
import json
import time
import paho.mqtt.client as mqtt

# הגדרות רשת וטופיקים
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_DHT = "pr/home/OZ_4637_dht/sts"
TOPIC_RELAY = "pr/home/OZ_4637_relay/sts"
TOPIC_ALARMS = "pr/home/OZ_4637/alarms"

DB_NAME = "smarthome.db"

# 1. אתחול מסד נתונים SQLite
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # טבלת נתוני חיישנים
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            topic TEXT,
            temperature REAL,
            humidity REAL
        )
    ''')
    
    # טבלת אירועים והתראות
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT,
            payload TEXT
        )
    ''')
    conn.commit()
    conn.close()

# 2. פונקציות שמירה למסד הנתונים
def save_telemetry(topic, temp, hum):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO telemetry (topic, temperature, humidity)
        VALUES (?, ?, ?)
    ''', (topic, temp, hum))
    conn.commit()
    conn.close()

def save_event(event_type, payload):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (event_type, payload)
        VALUES (?, ?)
    ''', (event_type, payload))
    conn.commit()
    conn.close()

# 3. טיפול בהודעות MQTT נכנסות
def on_connect(client, userdata, flags, rc):
    print(f"[Data Manager] Connected to broker with result code {rc}")
    client.subscribe([(TOPIC_DHT, 0), (TOPIC_RELAY, 0)])
    print(f"[Data Manager] Subscribed to {TOPIC_DHT} and {TOPIC_RELAY}")

def on_message(client, userdata, msg):
    payload_str = msg.payload.decode('utf-8')
    topic = msg.topic
    print(f"[Incoming] {topic} -> {payload_str}")
    
    # עיבוד נתוני DHT
    if topic == TOPIC_DHT:
        try:
            # תמיכה במבנה טקסט: "Temperature: 22.5 Humidity: 75.3" או JSON
            if "Temperature:" in payload_str and "Humidity:" in payload_str:
                parts = payload_str.split()
                temp = float(parts[1])
                hum = float(parts[3])
            elif "{" in payload_str:
                data = json.loads(payload_str)
                temp = float(data.get("temperature", 0))
                hum = float(data.get("humidity", 0))
            else:
                return

            save_telemetry(topic, temp, hum)
            
            # בדיקת חריגה מסיפי אזהרה/התראה
            if temp > 30.0:
                alarm_msg = json.dumps({
                    "severity": "Critical",
                    "type": "High Temperature",
                    "value": temp,
                    "msg": f"Temperature exceeded threshold: {temp}C!"
                })
                client.publish(TOPIC_ALARMS, alarm_msg)
                save_event("ALARM_CRITICAL", alarm_msg)
                print(f"[ALARM TRIGGERED] {alarm_msg}")
            elif temp > 28.0:
                warning_msg = json.dumps({
                    "severity": "Warning",
                    "type": "Warm Temperature",
                    "value": temp,
                    "msg": f"Temperature is getting high: {temp}C"
                })
                client.publish(TOPIC_ALARMS, warning_msg)
                save_event("WARNING", warning_msg)

        except Exception as e:
            print(f"[Error parsing DHT]: {e}")

    # עיבוד נתוני Relay / Button
    elif topic == TOPIC_RELAY:
        save_event("RELAY_STATE", payload_str)

# 4. הפעלה ראשית
if __name__ == "__main__":
    init_db()
    client = mqtt.Client("OZ_4637_DataManager")
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("[Data Manager] Starting service...")
    client.connect(BROKER, PORT, 60)
    client.loop_forever()