# canbusdrive

## What is DBC?

- **DBC** = CAN bus Database— a text file format for describing the contents of CAN bus messages.
- Vital for CAN bus data logging and analysis.
- Contains the information needed to decode raw CAN bus data into physical values, e.g.:

  | CAN ID     | Data bytes                |
  |------------|----------------------------|
  | `0CF00400` | `FF FF FF 68 13 FF FF FF`  |

  decodes to:

  | Message | Signal      | Value | Unit |
  |---------|-------------|-------|------|
  | EEC1    | EngineSpeed | 621   | rpm  |

![DBC syntax explained](docsResources/dbcsyntaxexplain.png)

For more information, see:
- [CAN DBC File & Database Intro (CSS Electronics)](https://www.csselectronics.com/pages/can-dbc-file-database-intro)
- [Youtube|Comma: DBC file explained](https://www.youtube.com/watch?v=nNU6ipme878&t=11m50s)

## Setting up DBC

- Created [`dbc/car.dbc`](dbc/car.dbc) defining the CAN messages/signals from the architecture:
  - `DriverInput` (0x100, sent by `InputECU`): `Throttle`, `Brake`, `SteeringAngle`
  - `PowertrainStatus` (0x200, sent by `PowertrainECU`): `Speed`, `RPM`
- Verified the DBC parses correctly with `cantools`:
  ```
  cantools dump dbc/car.dbc
  ```
- Output:
  ```
  =================================Messages=================================

  ------------------------------------------------------------------------

  Name:           DriverInput
  Id:             0x100
  Length:         4 bytes
  Cycle time:     - ms
  Senders:        InputECU
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |<-----------------------------x|
           +---+---+---+---+---+---+---+---+
             +-- Throttle
           +---+---+---+---+---+---+---+---+
     B   1 |<-----------------------------x|
     y     +---+---+---+---+---+---+---+---+
     t       +-- Brake
     e     +---+---+---+---+---+---+---+---+
         2 |------------------------------x|
           +---+---+---+---+---+---+---+---+
         3 |<------------------------------|
           +---+---+---+---+---+---+---+---+
             +-- SteeringAngle

  Signal tree:

    -- {root}
       +-- Throttle
       +-- Brake
       +-- SteeringAngle

  ------------------------------------------------------------------------

  Name:           PowertrainStatus
  Id:             0x200
  Length:         4 bytes
  Cycle time:     - ms
  Senders:        PowertrainECU
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |------------------------------x|
           +---+---+---+---+---+---+---+---+
         1 |<------------------------------|
     B     +---+---+---+---+---+---+---+---+
     y       +-- Speed
     t     +---+---+---+---+---+---+---+---+
     e   2 |------------------------------x|
           +---+---+---+---+---+---+---+---+
         3 |<------------------------------|
           +---+---+---+---+---+---+---+---+
             +-- RPM

  Signal tree:

    -- {root}
       +-- Speed
       +-- RPM

  ------------------------------------------------------------------------
  ```

## Finding the Controller

- Created [`scripts/checkcontroller.py`](scripts/checkcontroller.py) to list all connected input devices (via `evdev`) and identify the correct one to use as the XBOX controller.
- For more on the underlying `evdev` interface used here, see the [Linux kernel input documentation](https://docs.kernel.org/input/input.html).

- Ran it:
  ```
  python scripts/checkcontroller.py
  ```
- Output:
  ```
  /dev/input/event12      name='Microsoft X-Box 360 pad'  phys='usb-0000:02:00.0-8/input0'
  /dev/input/event11      name='Razer Razer Viper Mini'   phys='usb-0000:02:00.0-10/input2'
  /dev/input/event10      name='Razer Razer Viper Mini'   phys='usb-0000:02:00.0-10/input1'
  .
  .
  .
  .
  .
  
  ```
- Controller identified: `/dev/input/event12`, name `Microsoft X-Box 360 pad` — this is the device the Input ECU will read from.

## Controller Diagnosis

- Created [`scripts/controllerdiagnosis.py`](scripts/controllerdiagnosis.py) to inspect the capabilities of the identified controller (`/dev/input/event12`) — its supported event types, codes, and axis ranges.
- Ran it and got:
  ```
  Device path: /dev/input/event12
  Device name: Microsoft X-Box 360 pad
  Event type: ('EV_SYN', 0)
    Event code: ('SYN_REPORT', 0)
    Event code: ('SYN_CONFIG', 1)
    Event code: ('SYN_DROPPED', 3)
    Event code: ('?', 21)

  Event type: ('EV_KEY', 1)
    Event code: (('BTN_A', 'BTN_GAMEPAD', 'BTN_SOUTH'), 304)
    Event code: (('BTN_B', 'BTN_EAST'), 305)
    Event code: (('BTN_NORTH', 'BTN_X'), 307)
    Event code: (('BTN_WEST', 'BTN_Y'), 308)
    Event code: ('BTN_TL', 310)
    Event code: ('BTN_TR', 311)
    Event code: ('BTN_SELECT', 314)
    Event code: ('BTN_START', 315)
    Event code: ('BTN_MODE', 316)
    Event code: ('BTN_THUMBL', 317)
    Event code: ('BTN_THUMBR', 318)

  Event type: ('EV_ABS', 3)
    Event code: (('ABS_X', 0), AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0))
    Event code: (('ABS_Y', 1), AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0))
    Event code: (('ABS_Z', 2), AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0))
    Event code: (('ABS_RX', 3), AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0))
    Event code: (('ABS_RY', 4), AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0))
    Event code: (('ABS_RZ', 5), AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0))
    Event code: (('ABS_HAT0X', 16), AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0))
    Event code: (('ABS_HAT0Y', 17), AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0))

  Event type: ('EV_FF', 21)
    Event code: ('FF_RUMBLE', 80)
    Event code: ('FF_PERIODIC', 81)
    Event code: (('FF_SQUARE', 'FF_WAVEFORM_MIN'), 88)
    Event code: ('FF_TRIANGLE', 89)
    Event code: ('FF_SINE', 90)
    Event code: (('FF_GAIN', 'FF_MAX_EFFECTS'), 96)
  ```
- Why this matters: these ranges are needed to write the conversion code from raw controller values to the `DriverInput` signal ranges defined in the DBC.


## Finding Relevant Buttons/Axes

- Used [`scripts/buttonfinder.py`](scripts/buttonfinder.py) to press each button/move each stick individually and observe the exact axis/code fired, to confirm which physical input maps to which `DriverInput` signal.
- Sample output while pressing left trigger, right trigger, then moving the right stick:
  ```
  python scripts/buttonfinder.py
  Listening on Microsoft X-Box 360 pad (/dev/input/event12) - press buttons/move sticks, Ctrl+C to stop
  AXIS ABS_Z = 145
  AXIS ABS_Z = 255
  AXIS ABS_Z = 0
  AXIS ABS_RZ = 100
  AXIS ABS_RZ = 185
  AXIS ABS_RZ = 255
  AXIS ABS_RZ = 95
  AXIS ABS_RZ = 0
  AXIS ABS_RX = -3072
  AXIS ABS_RX = -11776
  AXIS ABS_RX = -21760
  AXIS ABS_RX = -32768
  AXIS ABS_RX = -20480
  AXIS ABS_RX = 13312
  AXIS ABS_RX = 0
  AXIS ABS_RX = 5376
  AXIS ABS_RX = 16384
  AXIS ABS_RX = 28416
  AXIS ABS_RX = 32512
  AXIS ABS_RX = -1024
  AXIS ABS_RX = 256
  AXIS ABS_RX = 0
  ```
- Confirmed mapping to be used for the Input ECU:

  | DBC signal      | Controller input        | Raw range        | Rationale                              |
  |-----------------|--------------------------|-------------------|-----------------------------------------|
  | `Throttle`      | `ABS_RZ` (right trigger) | 0–255             | RT = gas |
  | `Brake`         | `ABS_Z` (left trigger)   | 0–255             | LT = brake                              |
  | `SteeringAngle` | `ABS_X` (left stick)     | −32768–32767      | left/right on the primary stick         |

## Input ECU: Reading Controller Input and Publishing to CAN Bus

- Created [`ecus/inputecu.py`](ecus/inputecu.py) — reads controller axes, converts them to `Throttle`/`Brake`/`SteeringAngle` per the DBC ranges, encodes a `DriverInput` frame, and publishes it on `vcan0`.
- Ran it alongside `candump vcan0` to verify the published values:
  ```
  Throttle= 30%  Brake=  0%  Steering=   0.0 deg
  Throttle= 65%  Brake=  0%  Steering=   0.0 deg
  Throttle=100%  Brake=  0%  Steering=   0.0 deg
  Throttle= 84%  Brake=  0%  Steering=   0.0 deg
  Throttle= 55%  Brake=  0%  Steering=   0.0 deg
  Throttle= 32%  Brake=  0%  Steering=   0.0 deg
  Throttle=  0%  Brake=  0%  Steering=   0.0 deg
  Throttle=  0%  Brake= 20%  Steering=   0.0 deg
  Throttle=  0%  Brake=100%  Steering=   0.0 deg
  Throttle=  0%  Brake= 86%  Steering=   0.0 deg
  Throttle=  0%  Brake= 36%  Steering=   0.0 deg
  Throttle=  0%  Brake=  0%  Steering=   0.0 deg
  Throttle=  0%  Brake=  0%  Steering= -16.9 deg
  Throttle=  0%  Brake=  0%  Steering= -73.1 deg
  Throttle=  0%  Brake=  0%  Steering= -90.0 deg
  Throttle=  0%  Brake=  0%  Steering= -54.8 deg
  Throttle=  0%  Brake=  0%  Steering=  15.5 deg
  Throttle=  0%  Brake=  0%  Steering=   0.0 deg
  Throttle=  0%  Brake=  0%  Steering=   4.2 deg
  Throttle=  0%  Brake=  0%  Steering=  22.5 deg
  Throttle=  0%  Brake=  0%  Steering=  57.0 deg
  Throttle=  0%  Brake=  0%  Steering=  89.3 deg
  Throttle=  0%  Brake=  0%  Steering=   0.0 deg
  ```
  ```
  vcan0  100   [4]  1E 00 00 00
  vcan0  100   [4]  41 00 00 00
  vcan0  100   [4]  64 00 00 00
  vcan0  100   [4]  54 00 00 00
  vcan0  100   [4]  37 00 00 00
  vcan0  100   [4]  20 00 00 00
  vcan0  100   [4]  00 00 00 00
  vcan0  100   [4]  00 14 00 00
  vcan0  100   [4]  00 64 00 00
  vcan0  100   [4]  00 56 00 00
  vcan0  100   [4]  00 24 00 00
  vcan0  100   [4]  00 00 00 00
  vcan0  100   [4]  00 00 57 FF
  vcan0  100   [4]  00 00 25 FD
  vcan0  100   [4]  00 00 7C FC
  vcan0  100   [4]  00 00 DC FD
  vcan0  100   [4]  00 00 9B 00
  vcan0  100   [4]  00 00 00 00
  vcan0  100   [4]  00 00 2A 00
  vcan0  100   [4]  00 00 E1 00
  vcan0  100   [4]  00 00 3A 02
  vcan0  100   [4]  00 00 7D 03
  vcan0  100   [4]  00 00 00 00
  ```
- Checking some random payload (`100` = `0x100`, the `DriverInput` ID):

  | InputECU log         | candump bytes      | Check                                      |
  |-----------------------|---------------------|---------------------------------------------|
  | Throttle=30%          | `1E 00 00 00`       | byte0 `0x1E` = 30                            |
  | Brake=20%             | `00 14 00 00`       | byte1 `0x14` = 20                            |
  | Steering=-16.9 deg    | `00 00 57 FF`       | bytes2-3 LE signed `0x57FF`&rarr;`-169`, ×0.1 = -16.9 |
  | Steering=89.3 deg     | `00 00 7D 03`       | bytes2-3 LE signed `0x037D`&rarr;`893`, ×0.1 = 89.3   |

 - Validated to be in sync.

 
