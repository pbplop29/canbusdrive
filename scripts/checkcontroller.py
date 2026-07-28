import evdev

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

if not devices:
    print("No input devices found.")

for device in devices:
        print(f"{device.path}\tname={device.name!r}\tphys={device.phys!r}")