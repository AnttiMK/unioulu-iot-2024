'''
Raspberry Pico W weather station for University of Oulu IoT course
'''

import ssl
from collections import deque
from time import sleep

import config
import dht
import networking
from machine import Pin, I2C
from bmp280 import BMP280, BMP280_CASE_INDOOR
from umqtt.robust import MQTTClient

PICO_LED = Pin("LED", Pin.OUT)

def init_sensors() -> tuple[BMP280, dht.DHT22]:
    '''
    Initialize BMP280 and DHT22 sensors
    '''
    sda = Pin(20)
    scl = Pin(21)
    bus = I2C(0, sda = sda, scl = scl)
    sleep(1) # warm up I2C

    bmp = BMP280(bus, use_case=BMP280_CASE_INDOOR)
    dht_sensor = dht.DHT22(Pin(2))
    return bmp, dht_sensor


def mqtt_callback(topic, message) -> None:
    '''
    Callback function for MQTT messages
    '''
    if topic == b'pico/led':
        if message == b'1':
            PICO_LED.on()
        elif message == b'0':
            PICO_LED.off()


def init_mqtt() -> MQTTClient:
    '''
    Initialize MQTT client
    '''

    # Load LetsEncrypt ISRG Root X1 CA certificate
    with open("isrgrootx1.der", "rb") as file:
        ca_der = file.read()

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    # If certificate verification isn't needed or is broken, use CERT_OPTIONAL
    # context.verify_mode = ssl.CERT_OPTIONAL
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cadata=ca_der)

    mqtt_client = MQTTClient(
        client_id=config.MQTT_CLIENT_ID,
        server=config.MQTT_HOST,
        port=config.MQTT_PORT,
        user=config.MQTT_USERNAME,
        password=config.MQTT_PASSWORD,
        keepalive=7200,
        ssl=context
    )

    PICO_LED.on()
    mqtt_client.connect()
    PICO_LED.off()

    # Subscribe to "pico/led" topic
    mqtt_client.set_callback(mqtt_callback)
    mqtt_client.subscribe("pico/led")
    return mqtt_client

try:
    networking.connect(PICO_LED)

    client = init_mqtt()
    bmp, dht_sensor = init_sensors()

    while True:
        # Network heartbeat to verify WLAN is up
        networking.heartbeat(PICO_LED)

        dht_sensor.measure()
        temp = bmp.temperature
        pres = bmp.pressure / 100
        hum = dht_sensor.humidity()
        print(f"Temperature: {temp:.2f} °C")
        print(f"Pressure: {pres:.2f} hPa")
        print(f"Humidity: {hum:.1f} %")

        # Publish sensor data to MQTT broker
        client.publish("sensor/data", f'{temp:.2f},{pres:.2f},{hum:.1f}')
        sleep(1)

        # Check for incoming MQTT messages
        client.check_msg()
        sleep(1)
except (OSError, ValueError) as e:
    print('Error when running program:', e)
