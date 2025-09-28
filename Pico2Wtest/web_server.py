import network
import socket
import time
from machine import Pin
import gc
from patterns import sos, heartbeat, breathe

# WiFi credentials - replace with your own
SSID = "Peace"
PASSWORD = "chocolatefreakR2D2!"

# Create LED object
led = Pin("LED", Pin.OUT)

# Global variables to track pattern state
current_pattern = None
running = False

def connect_to_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Check if already connected
    if wlan.isconnected():
        print("Already connected to WiFi")
        return wlan
    
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
        return wlan
    else:
        print("Connection failed!")
        # Blink LED slowly to indicate failed connection
        for _ in range(3):
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
        return None

def start_pattern(pattern_name):
    """Start a specific LED pattern"""
    global current_pattern, running
    
    # Stop any current pattern
    running = False
    time.sleep(0.5)  # Give time for any running pattern to stop
    
    current_pattern = pattern_name
    if pattern_name != "off":
        running = True

def web_page():
    """Generate the web page with buttons for controlling LED patterns"""
    gc.collect()  # Free up memory before creating the HTML
    
    # Determine which pattern is active
    sos_selected = "selected" if current_pattern == "sos" else ""
    heartbeat_selected = "selected" if current_pattern == "heartbeat" else ""
    breathe_selected = "selected" if current_pattern == "breathe" else ""
    off_selected = "selected" if current_pattern == "off" else ""
    
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
            transition: background-color 0.3s;
        }
        .button:hover { background-color: #0c7384; }
        .button:active { background-color: #0c6a79; }
        .selected { background-color: #2ebd71; }
        .container { max-width: 400px; margin: 0 auto; }
        h1 { color: #0f8a9d; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Pico W LED Control</h1>
        <p>Control your Pico W LED patterns from anywhere on your network!</p>
        
        <a href="/sos"><button class="button %s">SOS Pattern</button></a>
        <a href="/heartbeat"><button class="button %s">Heartbeat</button></a>
        <a href="/breathe"><button class="button %s">Breathing Effect</button></a>
        <a href="/off"><button class="button %s">Turn Off</button></a>
    </div>
</body>
</html>
""" % (sos_selected, heartbeat_selected, breathe_selected, off_selected)
    return html

def run_web_server():
    """Start a web server to control LED patterns"""
    # Connect to WiFi first
    wlan = connect_to_wifi()
    if not wlan or not wlan.isconnected():
        print("Could not connect to WiFi. Check credentials and try again.")
        return
    
    # Get IP address
    ip = wlan.ifconfig()[0]
    
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
    
    # Pattern control thread
    import _thread
    
    def pattern_controller():
        global running, current_pattern
        
        while True:
            if running:
                if current_pattern == "sos":
                    sos()
                elif current_pattern == "heartbeat":
                    heartbeat()
                elif current_pattern == "breathe":
                    breathe()
            else:
                time.sleep(0.1)  # Reduce CPU usage when not running a pattern
    
    # Start pattern controller in a separate thread
    _thread.start_new_thread(pattern_controller, ())
    
    # Web server main loop
    while True:
        try:
            cl, addr = s.accept()
            print('Client connected from', addr)
            request = cl.recv(1024)
            request = str(request)
            
            # Process requests
            if request.find('/sos') > 0:
                start_pattern("sos")
                print("SOS pattern selected")
            elif request.find('/heartbeat') > 0:
                start_pattern("heartbeat")
                print("Heartbeat pattern selected")
            elif request.find('/breathe') > 0:
                start_pattern("breathe")
                print("Breathing pattern selected")
            elif request.find('/off') > 0:
                start_pattern("off")
                led.off()
                print("LED turned off")
            
            # Send response
            response = web_page()
            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            cl.send(response)
            cl.close()
            
        except OSError as e:
            print('Connection error:', e)
            cl.close()
            print('Connection closed')
            
        except KeyboardInterrupt:
            print("Keyboard interrupt")
            break
    
    # Clean up
    s.close()
    led.off()
    print("Web server stopped")

# Main execution
if __name__ == "__main__":
    print("Starting Pico W Web Server...")
    # This will run forever and not return to the REPL
    try:
        run_web_server()
    except KeyboardInterrupt:
        print("Web server stopped by user")
        led.off()
    except Exception as e:
        print(f"Error: {e}")
        # Error pattern - three slow blinks
        for _ in range(3):
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
