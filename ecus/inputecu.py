import can
import cantools
import evdev

DBC_PATH = "dbc/car.dbc"
CONTROLLER_PATH = "/dev/input/event12"
CAN_CHANNEL = "vcan0"

# Found these values by running scripts/controllerdiagnosis.py 
TRIGGER_MIN, TRIGGER_MAX = 0, 255
STICK_MIN, STICK_MAX = -32768, 32767

def limit(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def main():
    # Initialization of dbc, message, xbox controller and CAN bus
    dbc = cantools.database.load_file(DBC_PATH)
    # Derived from dbc/car.dbc : BO_ 256 DriverInput: 4 InputECU
    driver_input = dbc.get_message_by_name("DriverInput")
    # Derived from dbc/car.dbc : BO_ 768 MediaControl: 1 InputECU
    media_control = dbc.get_message_by_name("MediaControl")
    controller = evdev.InputDevice(CONTROLLER_PATH)
    bus = can.Bus(channel=CAN_CHANNEL, interface="socketcan")

    # Initial state of the values to be sent over CAN bus
    state = {"throttle_raw": 0, "brake_raw": 0, "steering_raw": 0}
    press_counter = 0

    # Logic to publish to CAN bus
    def publish():
        throttle = limit(round(state["throttle_raw"]/ TRIGGER_MAX * 100), 0, 100)
        brake = limit(round(state["brake_raw"]/ TRIGGER_MAX * 100), 0, 100)
        steering = limit(state["steering_raw"]/ STICK_MAX * 90, -90, 90)

        # Data Creation based on the dbc configuration we had for the Signals
        # SG_ Throttle : 0|8@1+ (1,0) [0|100] "%" PowertrainECU
        # SG_ Brake : 8|8@1+ (1,0) [1|100] "%" PowertrainECU
        # SG_ SteeringAngle : 16|16@1- (0.1,0) [-90|90] "deg" DashboardECU`
        data = driver_input.encode({
            "Throttle": throttle,
            "Brake": brake, 
            "SteeringAngle": steering})
        
        frame = can.Message(
            arbitration_id=driver_input.frame_id,
            data=data,
            is_extended_id=driver_input.is_extended_frame
        )
        
        bus.send(frame)
        # Logging the values that were published to CAN Bus
        print(f"Throttle={throttle:3d}%  Brake={brake:3d}%  Steering={steering:6.1f} deg")

    # Play next or previous track on the media player based on the button pressed on the controller
    def publish_media(direction):
        nonlocal press_counter
        press_counter = (press_counter + 1) % 256

        # SG_ Direction : 0|8@1+ (1,0) [0|2] "" MultimediaECU
        # SG_ PressCounter : 8|8@1+ (1,0) [0|255] "" MultimediaECU
        data = media_control.encode({"Direction": direction, "PressCounter": press_counter})
        frame = can.Message(
            arbitration_id=media_control.frame_id,
            data=data,
            is_extended_id=media_control.is_extended_frame
        )
        bus.send(frame)
        print(f"{'Previous' if direction == 1 else 'Next'} track requested (press={press_counter})")

    try:
        for event in controller.read_loop():
            if event.type == evdev.ecodes.EV_ABS:
                if event.code == evdev.ecodes.ABS_RZ:
                    state["throttle_raw"] = event.value
                elif event.code == evdev.ecodes.ABS_Z:
                    state["brake_raw"] = event.value
                elif event.code == evdev.ecodes.ABS_X:
                    state["steering_raw"] = event.value
            elif event.type == evdev.ecodes.EV_KEY:
                if event.value == 1 and event.code == evdev.ecodes.BTN_TL:
                    publish_media(1)  # previous
                elif event.value == 1 and event.code == evdev.ecodes.BTN_TR:
                    publish_media(2)  # next
            elif event.type == evdev.ecodes.EV_SYN and event.code == evdev.ecodes.SYN_REPORT:
                publish()
    except KeyboardInterrupt:
        print("InputECU Exiting...")
    finally:
        bus.shutdown()
    

if __name__ == "__main__":
    main()