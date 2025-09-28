import network
import time
from machine import Pin

# WiFi credentials - replace with your own
SSID = "Peace"
PASSWORD = "chocolatefreakR2D2!"

# Create LED object
led = Pin("LED", Pin.OUT)

def connect_to_wifi():
    """Connect to WiFi network and return IP address"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Flash LED quickly during connection attempt
    for _ in range(5):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
    
    print(f"Connecting to WiFi: {SSID}...")
    wlan.connect(SSID, PASSWORD)
    
    # Wait for connection with timeout
    max_wait = 20
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print("Waiting for connection...")
        time.sleep(1)
        led.toggle()  # Blink LED while connecting
    
    # Check if connection successful
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"Connected! IP Address: {ip}")
        # Blink LED rapidly to indicate successful connection
        for _ in range(5):
            led.on()
            time.sleep(0.1)
            led.off()
            time.sleep(0.1)
        return ip
    else:
        print("Connection failed!")
        # Blink LED slowly to indicate failed connection
        for _ in range(3):
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
        return None

# Run this script to just test WiFi connection
if __name__ == "__main__":
    ip = connect_to_wifi()
    if ip:
        print(f"WiFi test successful! IP: {ip}")
        print("Now you can run web_server.py to start the web server")
        # Keep LED on to indicate success
        led.on()
    else:
        print("WiFi test failed. Check your credentials.")
        # LED off to indicate failure
        led.off()
