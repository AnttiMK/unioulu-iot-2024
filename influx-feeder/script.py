import influxdb_client
import paho.mqtt.client as mqtt
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point
import logging
import os
import ssl

logging.basicConfig(level=logging.DEBUG)

url = "https://influxdb-test-rahti2.2.rahtiapp.fi/"
token = os.getenv("INFLUXDB_TOKEN")
org = "Iot2024"
bucket = "sensor-data"


MQTT_BROKER = "otitdell.otit.fi"
MQTT_PORT = 60020
MQTT_TOPIC = "sensor/data"
LED_TOPIC = "pico/led"


def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        values = payload.split(',')

        if len(values) != 3:
            logging.error("Invalid data received. Expected 3 values (temperature, pressure, humidity).")
            return

        temperature = float(values[0])
        pressure = float(values[1])
        humidity = float(values[2])
        
        point = Point("sensor_data") \
            .tag("temperature", temperature) \
            .tag("pressure", pressure ) \
            .field("value", humidity)

        point1 = Point("temperature") \
            .field("value", temperature)
                    
        point2 = Point("pressure") \
            .field("value", pressure)
            
        point3 = Point("humidity") \
            .field("value", humidity)
            
        write_api.write(bucket=bucket, org=org, record=point)
        write_api.write(bucket=bucket, org=org, record=point1)
        write_api.write(bucket=bucket, org=org, record=point2)
        write_api.write(bucket=bucket, org=org, record=point3)

        if temperature > 25:
            logging.info("turning LED ON")
            client.publish(LED_TOPIC, 1)
        else:
            client.publish(LED_TOPIC, 0)

    except Exception as e:
        logging.error(f"Error processing message: {e}")

try:

    with influxdb_client.InfluxDBClient(url=url, token=token, org=org) as client:

        write_api = client.write_api(write_options=SYNCHRONOUS)


        mqtt_client = mqtt.Client()


        mqtt_client.on_message = on_message
        mqtt_client.enable_logger()

        try:
            mqtt_client.tls_set_context(ssl.create_default_context())
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            mqtt_client.subscribe(MQTT_TOPIC)
            logging.info("Connected to MQTT Broker and subscribed to topic.")
            
            mqtt_client.loop_forever()

        except Exception as mqtt_error:
            logging.error(f"Error connecting to MQTT Broker: {mqtt_error}")

except Exception as e:
    logging.error(f"Unexpected error: {e}")
