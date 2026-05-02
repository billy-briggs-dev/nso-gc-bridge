# NSO GC Bridge Native Compatibility Implementation Plan

## Goal

Build a native macOS bridge that lets Dolphin discover and use the NSO GameCube controller as close to a normal controller as possible, while preserving analogue trigger support and keeping DSU available as a fallback.

## Principles

1. Separate transport, protocol, and output layers immediately.
2. Treat the current Python implementation as the protocol reference, not the long-term runtime.
3. Target virtual HID as the primary compatibility path.
4. Keep DSU as an optional compatibility backend during migration.
5. Preserve analogue `L` and `R` trigger semantics end to end.

## Phase 0: Freeze Existing Behavior

Use the current Python codebase as the protocol oracle and write down the parts that must survive the rewrite.

### Reference Surfaces

- `main.py`
  - USB initialization handshake
  - BLE handshake and characteristic discovery
  - input report parsing
  - stick calibration
  - rumble and LED commands
- `dsu_server.py`
  - Dolphin compatibility path
- `controller_storage.py`
  - persistence patterns for saved controllers and slot assignment

### Deliverables

1. A short protocol specification covering:
   - USB report layout
   - BLE report variants
   - analogue trigger semantics
   - canonical button naming
   - player LED commands
   - rumble commands
2. A fixture set captured from real hardware:
   - USB neutral reports
   - USB trigger sweeps
   - BLE neutral reports
   - BLE button/stick reports
   - LED and rumble command confirmations

## Phase 1: Create the Native Project Structure

Create an Xcode workspace with a strict module split.

### Targets

1. `NSOBridgeCore`
2. `NSOBridgeTransportUSB`
3. `NSOBridgeTransportBLE`
4. `NSOBridgeVirtualHID`
5. `NSOBridgeDSU`
6. `NSOBridgeApp`

### Core Types

Define a canonical controller state model in `NSOBridgeCore` with:

- controller identifier
- player slot
- transport type
- button state
- main stick
- C-stick
- analogue `L`
- analogue `R`
- digital shoulder states if applicable
- battery state if available
- timestamp or sequence number

Define transport-independent output commands in `NSOBridgeCore`:

- `setPlayerLED(slot)`
- `setRumble(strength:)`
- `setInputMode(...)`

## Phase 2: Port the Protocol Layer First

Port the parsing and command-building logic before writing native transport code.

### Scope

Reimplement the logic currently embedded in:

- `main.py` USB parsing
- `main.py` BLE parsing
- `main.py` BLE notification handling
- `main.py` calibration
- `main.py` rumble and LED command generation

### Requirements

1. Make the parser pure and testable.
2. Keep calibration separate from transport callbacks.
3. Add fixture-driven unit tests for:
   - button mapping
   - stick decoding
   - analogue trigger decoding
   - BLE variant detection
   - calibration application

### Output

The protocol layer should accept raw bytes plus transport metadata and emit only canonical controller state.

## Phase 3: Implement Native USB Transport

Build a USB transport using macOS-native HID or USB APIs.

### Responsibilities

1. Discover the controller by VID and PID.
2. Open the device and perform the required initialization sequence.
3. Read input reports.
4. Send output commands for rumble and LEDs.
5. Forward raw reports to the protocol layer.

### Constraints

- The transport layer must remain byte-oriented.
- It must not know about Dolphin mapping.
- It must not contain button-name logic.

### Validation

1. Confirm connect and reconnect behavior.
2. Verify full analogue trigger range over USB.
3. Log report rate and dropped-report behavior.

## Phase 4: Implement Native BLE Transport

Build a CoreBluetooth transport layer for wireless support.

### Responsibilities

1. Scan and discover controllers.
2. Pair and connect.
3. Discover notification and write characteristics.
4. Subscribe to input notifications.
5. Send rumble and LED commands.
6. Reconnect cleanly after disconnects.

### Constraints

1. Port only proven handshake paths from the Python implementation.
2. Normalize BLE and USB into identical canonical state output.
3. Validate whether BLE preserves analogue trigger precision or needs normalization.

## Phase 5: Publish a Virtual HID Controller

This is the main native-compatibility milestone.

### Implementation

Use `IOHIDUserDevice` to publish a virtual gamepad to macOS.

### HID Descriptor Requirements

Expose:

- face buttons
- D-pad
- left stick
- right stick
- digital shoulders if needed
- analogue left trigger
- analogue right trigger
- start/home/capture equivalents if needed

### Success Criteria

1. Dolphin discovers the controller without DSU configuration.
2. Buttons map correctly.
3. Main stick and C-stick behave correctly.
4. `L` and `R` bind as analogue inputs.
5. Rumble and LEDs still work through the native pipeline.

## Phase 6: Keep DSU as a Fallback Backend

Retain DSU as a compatibility plugin, not as the core architecture.

### Design

1. Feed DSU from canonical controller state.
2. Support output modes:
   - virtual HID only
   - DSU only
   - both
3. Route rumble callbacks back through the shared output command path.

### Purpose

This keeps existing Dolphin setups working while native HID support is validated.

## Phase 7: Replace the Python Launcher

Build a thin SwiftUI app for user-facing configuration.

### App Responsibilities

1. Show paired and saved controllers.
2. Assign slots.
3. Select USB, BLE, virtual HID, or DSU fallback modes.
4. Display logs and diagnostics.
5. Start and stop the background runtime.

### Constraint

The app should not own protocol parsing or transport logic.

## Phase 8: Packaging, Signing, and Permissions

Replace `py2app` packaging with an Xcode-native macOS app bundle.

### Requirements

1. Configure app signing.
2. Add required Bluetooth permissions and entitlements.
3. Verify first-launch and permission flows on a clean machine.
4. Test reconnect after reboot and after controller power cycles.

## Recommended Execution Order

To reach native Dolphin support as early as possible, do the work in this order:

1. Protocol spec and fixture capture
2. Core state model and parser tests
3. USB transport
4. Virtual HID output
5. Dolphin validation over USB
6. BLE transport
7. DSU fallback backend
8. SwiftUI app and packaging

## Risks

1. Virtual HID behavior may vary across apps, so Dolphin must be validated early.
2. BLE may expose slightly different semantics or lower precision than USB.
3. Some low-level HID surfaces may require a small Objective-C or C shim even if Swift is the main language.

## Definition of Done

The rewrite is successful when:

1. Dolphin discovers the controller without DSU setup.
2. The controller works over USB, and ideally BLE.
3. Analogue `L` and `R` are bindable and behave as analogue inputs.
4. Rumble and player LEDs still work.
5. Reconnect and multi-controller behavior are stable.
6. DSU is optional rather than required.