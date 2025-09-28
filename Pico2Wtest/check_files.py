import os

print("\n--- Files on Pico: ---")
files = os.listdir()
for file in files:
    print(f"- {file}")
print("---------------------\n")

# Also check if main.py contains the web server code
try:
    with open('main.py', 'r') as f:
        content = f.read()
        if 'web_server' in content:
            print("main.py contains web server code - Good!")
        else:
            print("main.py does NOT contain web server code - needs updating!")
except:
    print("Couldn't read main.py")
