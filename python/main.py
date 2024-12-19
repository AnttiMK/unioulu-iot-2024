'''
Raspberry Pico W weather station for University of Oulu IoT course
Author: Antti Koponen
'''

import ssl
from collections import deque
from time import sleep

import config
import dht
import networking
from machine import Pin, I2C, WDT, reset
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

def calc_movavg(values: deque, new_value: float) -> float:
    '''
    Calculates moving average for a set of values.
    :param values: deque containing previous values
    :param new_value: the latest value to calculate against
    :return: the moving average of the humidity readings
    '''
    values.append(new_value)
    return sum(values) / len(values)

def clamp(value: float, min_value: float, max_value: float) -> float:
    '''
    Clamp a value between a minimum and maximum value.
    :param value: the value to clamp
    :param min: the minimum value
    :param max: the maximum value
    :return: the clamped value
    '''
    return max(min_value, min(value, max_value))

try:
    # Enable 30s watchdog timer to reset the Pico if it hangs
    wdt = WDT(timeout=30000)
    wdt.feed()

    networking.connect(PICO_LED)

    client = init_mqtt()
    bmp, dht_sensor = init_sensors()

    # Deque size determines moving average window size
    humidity_readings = deque([], 4)
    pressure_readings = deque([], 6)

    while True:
        # Watchdog
        wdt.feed()

        # Network heartbeat to verify WLAN is up
        networking.heartbeat(PICO_LED)

        dht_sensor.measure()
        temp = clamp(bmp.temperature, -40, 80)
        pres = clamp(bmp.pressure / 100, 900, 1100) # Pa to hPa
        hum = clamp(dht_sensor.humidity(), 0, 100)
        hum_smooth = calc_movavg(humidity_readings, hum)
        pres_smooth = calc_movavg(pressure_readings, pres)

        print(f"Temperature: {temp:.2f} °C")
        print(f"Pressure: {pres:.2f} hPa")
        print(f"Humidity: {hum:.1f} %")
        print(f"Humidity (3avg): {hum_smooth:.1f} %")

        # Publish sensor data to MQTT broker
        client.publish("sensor/data", f'{temp:.2f},{pres_smooth:.2f},{hum_smooth:.1f}', qos=1)
        sleep(1)

        # Check for incoming MQTT messages
        client.check_msg()
        sleep(1)
except (OSError, ValueError) as e:
    print('Error when running program:', e)
    reset()
