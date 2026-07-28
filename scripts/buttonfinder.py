import evdev

# used the device path as we found it in the checkcontroller.py script
DEVICE_PATH = "/dev/input/event12"

dev = evdev.InputDevice(DEVICE_PATH)
print(f"Listening on {dev.name} ({dev.path}) - press buttons/move sticks, Ctrl+C to stop")

for event in dev.read_loop():
    if event.type == evdev.ecodes.EV_KEY:
        key = evdev.ecodes.keys[event.code]
        state = "pressed" if event.value == 1 else "released"
        print(f"BUTTON {key} {state}")
    elif event.type == evdev.ecodes.EV_ABS:
        axis = evdev.ecodes.ABS[event.code]
        print(f"AXIS {axis} = {event.value}")
