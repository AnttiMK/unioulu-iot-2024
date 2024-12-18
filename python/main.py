import config
import dht
import networking
import ssl
from machine import Pin, I2C
from bmp280 import *
from time import sleep
from umqtt.robust import MQTTClient

networking.connect()

sda = Pin(20)
scl = Pin(21)
bus = I2C(0, sda = sda, scl = scl)
sleep(1) # warm up I2C

bmp = BMP280(bus, use_case=BMP280_CASE_INDOOR)
dht = dht.DHT22(Pin(2))

# Load LetsEncrypt ISRG Root X1 CA certificate
with open("isrgrootx1.der", "rb") as file:
    CA_DER = file.read()

context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.verify_mode = ssl.CERT_REQUIRED
context.load_verify_locations(cadata=CA_DER)

client = MQTTClient(
    client_id=config.MQTT_CLIENT_ID,
    server=config.MQTT_HOST,
    port=config.MQTT_PORT,
    user=config.MQTT_USERNAME,
    password=config.MQTT_PASSWORD,
    keepalive=7200,
    ssl=context
)

client.connect()

while True:
  try:
    # Network heartbeat to verify WLAN is up
    networking.heartbeat()
    
    dht.measure()
    temp = bmp.temperature
    pres = bmp.pressure / 100
    hum = dht.humidity()
    print(f"Temperature: {temp:.2f} °C")
    print(f"Pressure: {pres:.2f} hPa")
    print(f"Humidity: {hum:.1f} %")
    client.publish("sensor/data", f'{temp:.2f},{pres:.2f},{hum:.1f}')
    
    sleep(2)
  except OSError as e:
    print('Failed to read sensor.')
