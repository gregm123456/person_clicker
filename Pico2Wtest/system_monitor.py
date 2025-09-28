from machine import Pin, ADC, Timer
import time
import random
import gc

led = Pin("LED", Pin.OUT)
timer = Timer()

def get_internal_temp():
    """Read the internal temperature sensor"""
    sensor_temp = ADC(4)
    conversion_factor = 3.3 / (65535)
    reading = sensor_temp.read_u16() * conversion_factor
    # The temperature sensor measures the Vbe voltage of a biased bipolar diode
    temperature = 27 - (reading - 0.706) / 0.001721
    return temperature

def memory_stats():
    """Get memory usage statistics"""
    gc.collect()
    free = gc.mem_free()
    allocated = gc.mem_alloc()
    total = free + allocated
    percent = allocated / total * 100
    return {
        'free': free,
        'allocated': allocated,
        'total': total,
        'percent': percent
    }

def blink_temp(timer):
    """Blink LED based on temperature"""
    temp = get_internal_temp()
    # Map temperature to blink rate (higher temp = faster blinks)
    # Typically Pico runs around 25-35°C
    delay = max(100, 1000 - (temp - 20) * 50)  # Faster as temp increases
    led.toggle()
    timer.init(period=int(delay), mode=Timer.ONE_SHOT, callback=blink_temp)

def system_monitor():
    """Display system information periodically"""
    try:
        print("\n--- Raspberry Pi Pico W System Monitor ---")
        print("\nPress Ctrl+C to exit\n")
        
        while True:
            temp = get_internal_temp()
            mem = memory_stats()
            
            print(f"Temperature: {temp:.2f}°C")
            print(f"Memory: {mem['allocated']/1024:.2f}kB used, {mem['free']/1024:.2f}kB free ({mem['percent']:.1f}%)")
            print(f"Uptime: {time.ticks_ms()/1000:.1f} seconds")
            print("-" * 40)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nMonitor stopped")
    finally:
        led.off()

def random_blink():
    """Random LED blinking pattern"""
    try:
        print("Random blinking pattern (press Ctrl+C to stop)")
        while True:
            # Random on time between 50ms and 500ms
            on_time = random.randint(50, 500)
            # Random off time between 50ms and 500ms
            off_time = random.randint(50, 500)
            
            led.on()
            time.sleep_ms(on_time)
            led.off()
            time.sleep_ms(off_time)
    except KeyboardInterrupt:
        led.off()
        print("Random blinking stopped")

print("Select a function to run:")
print("1. Temperature-based blinking (uses timer)")
print("2. System monitor (temp & memory)")
print("3. Random blink pattern")

choice = input("Enter your choice (1-3): ")

if choice == "1":
    print("LED will blink faster as temperature increases")
    print("Press Ctrl+C to stop")
    blink_temp(timer)  # Start the timer-based blinking
elif choice == "2":
    system_monitor()
elif choice == "3":
    random_blink()
else:
    print("Invalid choice")
