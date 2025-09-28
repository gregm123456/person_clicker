import machine
import time
import os
import gc

led = machine.Pin("LED", machine.Pin.OUT)

# Flash quickly 3 times to show script is running
for _ in range(3):
    led.on()
    time.sleep(0.1)
    led.off()
    time.sleep(0.1)

print("\n--- DIAGNOSTIC INFORMATION ---")

# 1. List all files
print("\nFiles on Pico:")
try:
    files = os.listdir()
    for file in files:
        print(f"- {file}")
except Exception as e:
    print(f"Error listing files: {e}")

# 2. Check main.py content
print("\nChecking main.py content:")
try:
    with open('main.py', 'r') as f:
        content = f.read()
        print(content[:200] + "..." if len(content) > 200 else content)
        if 'web_server' in content:
            print("main.py contains reference to web_server - Good!")
        else:
            print("ERROR: main.py does NOT contain web_server reference!")
except Exception as e:
    print(f"Error reading main.py: {e}")

# 3. Check for web_server.py
print("\nChecking for web_server.py:")
try:
    if 'web_server.py' in files:
        print("web_server.py exists - Good!")
        with open('web_server.py', 'r') as f:
            content = f.read()
            if 'network' in content and 'socket' in content:
                print("web_server.py contains networking code - Good!")
            else:
                print("ERROR: web_server.py might be incomplete!")
    else:
        print("ERROR: web_server.py not found!")
except Exception as e:
    print(f"Error checking web_server.py: {e}")

# 4. Memory information
print("\nMemory information:")
gc.collect()
free = gc.mem_free()
alloc = gc.mem_alloc()
print(f"Free memory: {free} bytes")
print(f"Allocated memory: {alloc} bytes")
print(f"Total: {free + alloc} bytes")

# 5. Check network module
print("\nChecking network module:")
try:
    import network
    wlan = network.WLAN(network.STA_IF)
    print(f"Network module available - Good!")
    print(f"WiFi active: {wlan.active()}")
    print(f"Connected: {wlan.isconnected()}")
    if wlan.isconnected():
        print(f"IP address: {wlan.ifconfig()[0]}")
except Exception as e:
    print(f"Error with network module: {e}")

print("\n--- END DIAGNOSTIC ---")

# Signal completion with two long flashes
for _ in range(2):
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
