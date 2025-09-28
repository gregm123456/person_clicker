from machine import Pin
import network
import time
import urequests
import json

# WiFi credentials - replace with your own
SSID = "Peace"
PASSWORD = "chocolatefreakR2D2!"

led = Pin("LED", Pin.OUT)

def connect_to_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
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
        return wlan
    else:
        print("Connection failed!")
        return None

def create_main():
    """Create a main.py that automatically starts the web server on boot"""
    with open('main.py', 'w') as f:
        f.write('''
# Autostart web server on boot
print("Starting LED web server...")

try:
    # Import dependencies first
    import time
    from machine import Pin
    
    # Show startup indication
    led = Pin("LED", Pin.OUT)
    for _ in range(3):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
    
    # Import and explicitly start the web server
    import web_server
    web_server.run_web_server()  # Actually call the function to start the server
except Exception as e:
    import time
    from machine import Pin
    led = Pin("LED", Pin.OUT)
    print(f"Error starting web server: {e}")
    # Error pattern - blink rapidly as error indicator
    for _ in range(10):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
''')
    print("Created main.py - Your Pico W will now start the web server automatically on boot")

# Run setup tasks
if __name__ == "__main__":
    print("Setting up your Pico W as a web server...")
    
    # Step 1: Test WiFi connection
    wlan = connect_to_wifi()
    if not wlan:
        print("WiFi connection failed. Please check your credentials.")
        for _ in range(5):  # Error indication
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
        exit()
    
    # Step 2: Create main.py for autostart
    print("Creating main.py for autostart...")
    create_main()
    
    # Step 3: Final success indication
    print("Setup complete! Your Pico W will now run as a web server on boot.")
    print(f"Access it at http://{wlan.ifconfig()[0]}")
    
    # Blink LED in success pattern
    for _ in range(10):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
