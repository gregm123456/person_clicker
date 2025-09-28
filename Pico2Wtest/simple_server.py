import network
import socket
import time
from machine import Pin
import gc

# WiFi credentials
SSID = "Peace"
PASSWORD = "chocolatefreakR2D2!"

# Initialize LED
led = Pin("LED", Pin.OUT)

# Flash 3 times to indicate script start
for _ in range(3):
    led.on()
    time.sleep(0.2)
    led.off()
    time.sleep(0.2)

print("Starting fresh web server setup...")

def connect_to_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)  # CRITICAL: Activate the interface
    
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
        return wlan, ip
    else:
        print("Connection failed!")
        # Blink LED slowly to indicate failed connection
        for _ in range(3):
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
        return None, None

def web_page():
    """Generate the web page with buttons for controlling LED patterns"""
    gc.collect()  # Free up memory before creating the HTML
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Pico W LED Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; text-align: center; margin: 0px auto; padding-top: 30px; }
        .button { 
            padding: 15px 20px; 
            font-size: 24px; 
            text-align: center; 
            outline: none; 
            color: #fff; 
            background-color: #0f8a9d; 
            border: none; 
            border-radius: 5px; 
            margin: 10px;
            cursor: pointer;
        }
        .button:hover { background-color: #0c7384; }
        .button:active { background-color: #0c6a79; }
        .container { max-width: 400px; margin: 0 auto; }
        h1 { color: #0f8a9d; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Pico W LED Control</h1>
        <p>Control your Pico W LED from anywhere on your network!</p>
        
        <a href="/on"><button class="button">LED ON</button></a>
        <a href="/off"><button class="button">LED OFF</button></a>
        <a href="/sos"><button class="button">SOS Pattern</button></a>
        <a href="/blink"><button class="button">Blink</button></a>
    </div>
</body>
</html>
"""
    return html

# Simplified server that just turns LED on/off
def run_web_server():
    """Start a web server to control LED"""
    # Connect to WiFi first
    wlan, ip = connect_to_wifi()
    if not wlan or not wlan.isconnected():
        print("Could not connect to WiFi. Check credentials and try again.")
        return
    
    # Create socket
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)
    print(f"Web server started at http://{ip}")
    
    # Turn LED on briefly to indicate server is running
    led.on()
    time.sleep(1)
    led.off()
    
    # Define LED patterns
    def blink_pattern(times=10):
        for _ in range(times):
            led.on()
            time.sleep(0.2)
            led.off()
            time.sleep(0.2)
    
    def sos_pattern():
        # S: 3 short
        for _ in range(3):
            led.on()
            time.sleep(0.2)
            led.off()
            time.sleep(0.2)
        time.sleep(0.3)
        # O: 3 long
        for _ in range(3):
            led.on()
            time.sleep(0.6)
            led.off()
            time.sleep(0.2)
        time.sleep(0.3)
        # S: 3 short
        for _ in range(3):
            led.on()
            time.sleep(0.2)
            led.off()
            time.sleep(0.2)
    
    # Web server main loop
    pattern_running = False
    try:
        while True:
            if not pattern_running:
                cl, addr = s.accept()
                print('Client connected from', addr)
                request = cl.recv(1024)
                request = str(request)
                
                # Process requests - SIMPLIFIED
                if '/on' in request:
                    led.on()
                    print("LED turned ON")
                elif '/off' in request:
                    led.off()
                    print("LED turned OFF")
                elif '/sos' in request:
                    print("Running SOS pattern")
                    sos_pattern()
                elif '/blink' in request:
                    print("Running blink pattern")
                    blink_pattern()
                
                # Send response
                response = web_page()
                cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                cl.send(response)
                cl.close()
    except Exception as e:
        print(f"Error in web server: {e}")
    finally:
        s.close()
        print("Web server stopped")
        led.off()

# Auto-run the web server
print("Starting web server...")
run_web_server()
