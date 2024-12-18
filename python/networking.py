'''
Networking functions
Inspired by https://projects.raspberrypi.org/en/projects/get-started-pico-w/2
'''

from time import sleep

import config
import network

wlan = network.WLAN(network.STA_IF)

def connect(led):
    '''
    Connect to WLAN
    '''
    wlan.active(True)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    print('Waiting for WLAN connection..', end='')
    while wlan.isconnected() is False:
        led.on()
        print('.', end='')
        sleep(0.5)
        led.off()
        sleep(0.5)
    print('.\nConnection successful!')
    ip_address = wlan.ifconfig()[0]
    print("IP address:", ip_address)

def heartbeat(led):
    '''
    Network heartbeat to verify WLAN is up
    '''
    if not wlan.isconnected():
        print("Lost connection. Reconnecting...")
        connect(led)
