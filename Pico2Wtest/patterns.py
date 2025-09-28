from machine import Pin
from utime import sleep_ms

led = Pin("LED", Pin.OUT)

def sos():
    """SOS pattern in Morse code"""
    # S: three short blinks
    for _ in range(3):
        led.on()
        sleep_ms(200)
        led.off()
        sleep_ms(200)
    sleep_ms(300)  # gap between letters
    
    # O: three long blinks
    for _ in range(3):
        led.on()
        sleep_ms(600)
        led.off()
        sleep_ms(200)
    sleep_ms(300)  # gap between letters
    
    # S: three short blinks again
    for _ in range(3):
        led.on()
        sleep_ms(200)
        led.off()
        sleep_ms(200)
    sleep_ms(1000)  # longer pause before repeating

def heartbeat():
    """Simulates a heartbeat pattern"""
    led.on()
    sleep_ms(100)
    led.off()
    sleep_ms(100)
    led.on()
    sleep_ms(100)
    led.off()
    sleep_ms(700)  # pause between beats

def breathe():
    """LED breathing effect simulated with delays"""
    # On Pico W, the onboard LED is tied to GPIO 25 but needs special handling
    # We'll simulate the breathing effect with varying delays instead of PWM
    
    # Fade in (gradually decreasing off time)
    for i in range(10, 0, -1):
        led.on()
        sleep_ms(10)
        led.off()
        sleep_ms(i * 20)
    
    # Full brightness
    led.on()
    sleep_ms(300)
    
    # Fade out (gradually increasing off time)
    for i in range(1, 11):
        led.on()
        sleep_ms(10)
        led.off()
        sleep_ms(i * 20)
    
    sleep_ms(300)  # pause before next pattern

# Only execute patterns when this file is run directly (not when imported)
if __name__ == "__main__":
    print("LED patterns starting...")
    try:
        while True:
            print("SOS pattern")
            for _ in range(3):
                sos()
            
            print("Heartbeat pattern")
            for _ in range(10):
                heartbeat()
                
            print("Breathing pattern")
            for _ in range(3):
                breathe()
                
    except KeyboardInterrupt:
        led.off()
        print("Pattern stopped.")
