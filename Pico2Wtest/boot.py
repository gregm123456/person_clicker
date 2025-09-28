# boot.py - runs on boot-up
import machine
import time

# Brief blink to indicate boot sequence started
led = machine.Pin("LED", machine.Pin.OUT)
led.on()
time.sleep(0.5)
led.off()
time.sleep(0.5)

print("Boot sequence complete. Starting main.py...")
