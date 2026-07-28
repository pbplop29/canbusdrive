import os
import subprocess
import sys
import time

# Make the top-level `ui` package importable regardless of the CWD this
# script is launched from (it lives next to `ecus/`, not inside it).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import can
import cantools

DBC_PATH = "dbc/car.dbc"
CAN_CHANNEL = "vcan0"
MUSIC_DIR = "resources/music"
AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav")


PLAYER_CMD = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error"]

# If a track exits sooner than this, treat it as a failed start (bad file,
# audio device momentarily busy, etc) rather than "song finished" -- log it
# and back off briefly instead of hammering the player in a tight loop.
MIN_PLAY_SECONDS = 1.0
FAILURE_BACKOFF_SECONDS = 0.5

# No window of its own - DashboardECU displays the current track (as a
# plain index, "Track N") in the driving-view HUD, so this loop just needs
# to poll the bus/player at a steady rate.
TICK_SECONDS = 0.1

# CAN messages aren't retained on the bus -- a one-shot broadcast on track
# change is invisible to any ECU that starts listening even a moment later.
# Re-sending the current track on this interval means DashboardECU always
# converges to the right label within ~1s, regardless of start order.
HEARTBEAT_SECONDS = 1.0


def load_playlist():
    if not os.path.isdir(MUSIC_DIR):
        return []
    return sorted(
        os.path.join(MUSIC_DIR, name)
        for name in os.listdir(MUSIC_DIR)
        if name.lower().endswith(AUDIO_EXTENSIONS)
    )


def step_index(count, current, delta):
    if count <= 1:
        return 0
    if current is None:
        return 0
    return (current + delta) % count


def main():
    dbc = cantools.database.load_file(DBC_PATH)
    # Derived from dbc/car.dbc : BO_ 768 MediaControl: 1 InputECU
    media_control = dbc.get_message_by_name("MediaControl")
    # Derived from dbc/car.dbc : BO_ 1024 PlaybackStatus: 1 MultimediaECU
    playback_status = dbc.get_message_by_name("PlaybackStatus")

    bus = can.Bus(
        channel=CAN_CHANNEL,
        interface="socketcan",
        can_filters=[{"can_id": media_control.frame_id, "can_mask": 0x7FF, "extended": False}],
    )

    playlist = load_playlist()
    if not playlist:
        print(f"No songs found in {MUSIC_DIR}/ -- add some .mp3/.ogg/.wav files and restart.")

    current_index = None
    current_process = None
    current_started_at = 0.0
    last_press_counter = None
    last_broadcast = 0.0

    def broadcast_track(index):
        nonlocal last_broadcast
        data = playback_status.encode({"CurrentTrack": index})
        frame = can.Message(
            arbitration_id=playback_status.frame_id,
            data=data,
            is_extended_id=playback_status.is_extended_frame,
        )
        bus.send(frame)
        last_broadcast = time.monotonic()

    def play(index):
        nonlocal current_index, current_process, current_started_at
        if current_process is not None:
            current_process.terminate()
            current_process.wait()
        current_index = index
        current_started_at = time.monotonic()
        track = playlist[index]
        current_process = subprocess.Popen([*PLAYER_CMD, track])
        broadcast_track(index)
        print(f"Now playing Track {index + 1}/{len(playlist)}: {os.path.basename(track)}")

    if playlist:
        play(step_index(len(playlist), None, 1))

    print(f"MultimediaECU listening on {CAN_CHANNEL} ...")
    print("Ctrl+C to stop.")

    try:
        while True:
            message = bus.recv(timeout=TICK_SECONDS)
            if message is not None and message.arbitration_id == media_control.frame_id:
                decoded = media_control.decode(message.data)
                press_counter = decoded["PressCounter"]
                direction = decoded["Direction"]
                if playlist and direction and press_counter != last_press_counter:
                    last_press_counter = press_counter
                    delta = -1 if direction == 1 else 1  # 1=previous, 2=next
                    play(step_index(len(playlist), current_index, delta))

            # A song finishing on its own also advances the playlist, same
            # as a real head unit -- shuffle isn't only triggered by LB/RB.
            if playlist and current_process is not None and current_process.poll() is not None:
                elapsed = time.monotonic() - current_started_at
                if elapsed < MIN_PLAY_SECONDS:
                    print(
                        f"Track {current_index + 1} exited after {elapsed:.2f}s "
                        f"(exit code {current_process.returncode}) -- treating as a failed "
                        f"start, backing off {FAILURE_BACKOFF_SECONDS}s"
                    )
                    time.sleep(FAILURE_BACKOFF_SECONDS)
                play(step_index(len(playlist), current_index, 1))
                continue

            if playlist and time.monotonic() - last_broadcast >= HEARTBEAT_SECONDS:
                broadcast_track(current_index)
    except KeyboardInterrupt:
        print("\nStopping MultimediaECU.")
    finally:
        if current_process is not None:
            current_process.terminate()
            current_process.wait()
        bus.shutdown()


if __name__ == "__main__":
    main()
