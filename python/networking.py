import config
import network
from time import sleep

wlan = network.WLAN(network.STA_IF)

def connect():
    # Connect to WLAN
    wlan.active(True)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    print('Waiting for WLAN connection..', end='')
    while wlan.isconnected() == False:
        print('.', end='')
        sleep(1)
    print('.\nConnection successful!')
    print("IP address:", wlan.ifconfig()[0])
    
def heartbeat():
    if not wlan.isconnected():
        print("Lost connection. Reconnecting...")
        connect()
