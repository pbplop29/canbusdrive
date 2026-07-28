# Design

## Goal

![Goal](docsResources/goal.png)

- Use an XBOX controller as the input device to drive a simulated car.
- **Input ECU**: reads controller state, derives `throttle`, `brake`, `steering`; broadcasts on CAN bus.
- **Powertrain ECU**: subscribes to `throttle`/`brake`; computes `speed` and `rpm`; broadcasts result on CAN bus.
- **Dashboard ECU**: subscribes to input (`steering`) and powertrain (`speed`, `rpm`); renders car position/heading and speed/RPM HUD as shown above.
- End result: controller input drives the car on-screen with live speed/RPM readout, entirely via CAN bus pub/sub between ECUs.

## Architecture

![Architecture](docsResources/architecture.png)
