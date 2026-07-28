import time
import can
import cantools

DBC_PATH = "dbc/car.dbc"
CAN_CHANNEL = "vcan0"

# 20KHz frequency
TICK_SECONDS = 0.05

MAX_SPEED = 200.0
THROTTLE_ACCELERATION_GAIN = 0.15
BRAKE_DECELERATION_GAIN = 0.40
DRAG_COEFFICIENT = 0.03

IDLE_RPM = 800.0
RPM_PER_KMH = 45.0
MAX_RPM = 8000.0

def limit(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def main():
    dbc = cantools.database.load_file(DBC_PATH)
    driver_input = dbc.get_message_by_name("DriverInput")
    powertrain_status = dbc.get_message_by_name("PowertrainStatus")

    bus = can.Bus(
        channel=CAN_CHANNEL,
        interface="socketcan", 
        can_filters=[{
            "can_id": driver_input.frame_id, 
            "can_mask": 0x7FF, 
            "extended": False}]
        )

    throttle = 0.0
    brake = 0.0
    speed = 0.0
    rpm = IDLE_RPM

    try:
        while True:
            message = bus.recv(timeout=TICK_SECONDS)
            if message is not None and message.arbitration_id == driver_input.frame_id:
                decoded = driver_input.decode(message.data)
                throttle = decoded["Throttle"] 
                brake = decoded["Brake"] 

            acceleration = (throttle * THROTTLE_ACCELERATION_GAIN 
            - brake * BRAKE_DECELERATION_GAIN 
            - speed * DRAG_COEFFICIENT)

            speed = limit(speed + acceleration*TICK_SECONDS, 0.0, MAX_SPEED)
            rpm = limit(IDLE_RPM + speed * RPM_PER_KMH, IDLE_RPM, MAX_RPM)

            data = powertrain_status.encode({
                "Speed": round(speed),
                "RPM": round(rpm)
            })
            frame = can.Message(
                arbitration_id=powertrain_status.frame_id,
                data=data,
                is_extended_id=powertrain_status.is_extended_frame
            )
            bus.send(frame)
            print(f"Speed={speed:6.2f} km/h  RPM={rpm:6.0f}")

    except KeyboardInterrupt:
        print("PowertrainECU Exiting...")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()