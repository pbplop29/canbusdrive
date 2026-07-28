import evdev

# used the device path as we found it in the checkcontroller.py script
DEVICE_PATH = "/dev/input/event12"

dev = evdev.InputDevice(DEVICE_PATH)    
print(f"Device path: {dev.path}")
print(f"Device name: {dev.name}")

caps=dev.capabilities(verbose=True)

for event_type, event_codes in caps.items():
    print(f"Event type: {event_type}")
    for event_code in event_codes:
        print(f"  Event code: {event_code}")
    print()