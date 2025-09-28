# reset_to_run.py - Run this script to soft reset the Pico and start the web server
import machine

print("Performing soft reset to launch web server...")
print("Wait for LED to indicate connection status...")
machine.soft_reset()  # This will restart the Pico and run boot.py followed by main.py
