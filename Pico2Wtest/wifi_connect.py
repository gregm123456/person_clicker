import network
import time
from machine import Pin

# WiFi credentials
SSID = "Peace"
PASSWORD = "chocolatefreakR2D2!"

# Create LED object
led = Pin("LED", Pin.OUT)

def connect_wifi():
    print("Starting WiFi connection test...")
    
    # Create and activate the WiFi interface
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)  # This is critical!
    
    # Flash quickly to indicate active WiFi module
    for _ in range(3):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
    
    print(f"Connecting to {SSID}...")
    wlan.connect(SSID, PASSWORD)
    
    # Wait for connection with timeout
    max_wait = 20
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print("Waiting for connection...")
        time.sleep(1)
        led.toggle()  # Blink while connecting
    
    # Check connection result
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"Connected! IP address: {ip}")
        
        # Success pattern - 5 quick blinks
        for _ in range(5):
            led.on()
            time.sleep(0.1)
            led.off()
            time.sleep(0.1)
        
        return ip
    else:
        print("Connection failed!")
        
        # Failure pattern - 3 slow blinks
        for _ in range(3):
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
        
        return None

# Run the test
ip = connect_wifi()
if ip:
    print(f"Your Pico W is now connected at: {ip}")
    print("You can access the web server at this address")
    
    # Keep the LED on to indicate successful connection
    led.on()
else:
    print("WiFi connection failed. Please check credentials and try again.")
