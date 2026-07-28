import os
import sys

# Make the top-level `ui` package importable regardless of the CWD this
# script is launched from (it lives next to `ecus/`, not inside it).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import can
import cantools

from ui.renderer import GameRenderer

DBC_PATH = "dbc/car.dbc"
CAN_CHANNEL = "vcan0"


def main():
    db = cantools.database.load_file(DBC_PATH)
    driver_input = db.get_message_by_name("DriverInput")
    powertrain_status = db.get_message_by_name("PowertrainStatus")
    # Derived from dbc/car.dbc : BO_ 1024 PlaybackStatus: 1 MultimediaECU
    playback_status = db.get_message_by_name("PlaybackStatus")

    bus = can.Bus(
        channel=CAN_CHANNEL,
        interface="socketcan",
        can_filters=[
            {"can_id": driver_input.frame_id, "can_mask": 0x7FF, "extended": False},
            {"can_id": powertrain_status.frame_id, "can_mask": 0x7FF, "extended": False},
            {"can_id": playback_status.frame_id, "can_mask": 0x7FF, "extended": False},
        ],
    )

    renderer = GameRenderer()

    steering_deg = 0.0
    speed_kmh = 0.0
    rpm = 0.0
    track_label = ""

    running = True
    try:
        while running:
            running = renderer.poll_events()
            dt = renderer.tick()

            while True:
                msg = bus.recv(timeout=0)
                if msg is None:
                    break
                if msg.arbitration_id == driver_input.frame_id:
                    steering_deg = driver_input.decode(msg.data)["SteeringAngle"]
                elif msg.arbitration_id == powertrain_status.frame_id:
                    decoded = powertrain_status.decode(msg.data)
                    speed_kmh = decoded["Speed"]
                    rpm = decoded["RPM"]
                elif msg.arbitration_id == playback_status.frame_id:
                    track_index = playback_status.decode(msg.data)["CurrentTrack"]
                    track_label = f"Track {track_index + 1}"

            renderer.render(steering_deg, speed_kmh, rpm, track_label, dt)
    except KeyboardInterrupt:
        print("\nStopping DashboardECU.")
    finally:
        bus.shutdown()
        renderer.close()


if __name__ == "__main__":
    main()
