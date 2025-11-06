## ECU Simulator (OBD-II over TCP) – Windows friendly

This project simulates an OBD‑II ECU and provides a simple TCP bridge so readers/clients can run in separate processes on Windows. It includes:

- `ecu-simulator.py` – ECU simulator that responds to OBD‑II requests, emits random DTCs, and bridges CAN frames over TCP
- `obd_reader.py` – Example Python reader that queries PIDs, shows a live dashboard, and reads/clears DTCs via TCP

The TCP bridge solves a common Windows limitation: python‑can’s virtual bus is process‑local. With the bridge, any client (Python, Flutter, etc.) can talk to the simulator over a stable socket.


## Features

- OBD‑II services implemented:
	- 0x01 Current Data (selected PIDs: RPM 0x0C, Speed 0x0D, Coolant 0x05, Throttle 0x11, Engine Load 0x04, Intake Temp 0x0F)
	- 0x03 Read DTCs
	- 0x04 Clear DTCs
- Random DTC generator (periodically adds/clears codes like P0133, P0171, P0420, …)
- Windows‑friendly inter‑process comms via TCP on 127.0.0.1:55555
- Clean example reader with menu and live dashboard


## Project structure

```
ecu-simulator.py   # ECU + TCP bridge (server)
obd_reader.py      # Example reader (client)
pyproject.toml     # Dependencies (managed with uv)
README.md          # This file
```


## Prerequisites

- Windows 10/11
- Python 3.10+ installed and on PATH
- [uv](https://docs.astral.sh/uv/) (fast Python package/dependency manager)
	- Install on Windows PowerShell:

		```powershell
		irm https://astral.sh/uv/install.ps1 | iex
		```


## Setup (with uv)

Option A – Use uv’s managed venv automatically for commands:

```powershell
# From the repo root
uv sync             # creates .venv and installs dependencies from pyproject.toml

# Run the simulator
uv run python .\ecu-simulator.py

# In a second terminal, run the reader (optional)
uv run python .\obd_reader.py
```

Option B – Activate the venv explicitly:

```powershell
uv sync
. .\.venv\Scripts\Activate.ps1

python .\ecu-simulator.py
# new terminal
. .\.venv\Scripts\Activate.ps1
python .\obd_reader.py
```

Notes
- If Windows Defender Firewall prompts on first run, allow Python to accept connections on private networks.
- The reader is optional; you can replace it with your own client or a Flutter app (see below).


## How it works (protocol)

The simulator exposes a tiny TCP framing on 127.0.0.1:55555. Every frame is exactly 13 bytes:

- 4 bytes: arbitration_id (little‑endian, uint32)
- 1 byte: dlc (data length code, 0–8)
- 8 bytes: CAN data payload

Requests are sent to arbitration_id 0x7DF (functional address). Responses are sent from 0x7E8. Examples:

- Service 0x01 (current data) for RPM (PID 0x0C)
	- Request data: `[0x02, 0x01, 0x0C, 0, 0, 0, 0, 0]`
	- Response data: `[len, 0x41, 0x0C, A, B, …]`, where RPM = ((A*256)+B)/4
- Service 0x03 (read DTCs)
	- Request: `[0x01, 0x03, 0, 0, 0, 0, 0, 0]`
	- Response: `[len, 0x43, h1, l1, h2, l2, …]` (pairs of 2 bytes per DTC). DTCs in this simulator are formatted as P‑codes using the two bytes per code.
- Service 0x04 (clear DTCs)
	- Request: `[0x01, 0x04, 0, 0, 0, 0, 0, 0]`
	- Response: `[len, 0x44, 0, …]` if successful

Important: values are little‑endian for the 4‑byte arbitration_id in the TCP header. The 8‑byte data block follows standard OBD‑II PID formulas.


## Run it

1) Start the simulator in one terminal

```powershell
uv run python .\ecu-simulator.py
```

2) Optionally, run the included reader in a second terminal to see a live dashboard

```powershell
uv run python .\obd_reader.py
```

You should see the reader connect to 127.0.0.1:55555, display live RPM/speed/temps, and list/clear DTCs.


## Flutter integration (replace the reader)

You can build a Flutter client that talks directly to the simulator’s TCP socket using `dart:io`. The steps below show a minimal working approach. You can then build UI on top.

### Networking targets

- Windows Flutter desktop app: connect to `127.0.0.1:55555`
- Android emulator: use `10.0.2.2:55555` (special alias of host’s localhost)
- iOS simulator: use `127.0.0.1:55555`
- Physical device: use your PC’s LAN IP (e.g., `192.168.1.23:55555`) and allow the firewall rule

### Frame packing (Dart)

Each request is 13 bytes: 4 (arb_id, LE) + 1 (dlc) + 8 (data). Example helpers:

```dart
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

class EcuClient {
	final String host;
	final int port;
	Socket? _socket;

	EcuClient({required this.host, this.port = 55555});

	static const int requestId = 0x7DF;
	static const int responseId = 0x7E8;

	Future<void> connect({Duration timeout = const Duration(seconds: 5)}) async {
		_socket = await Socket.connect(host, port, timeout: timeout);
	}

	Future<void> close() async {
		await _socket?.close();
	}

	// Send a single 13-byte frame
	void sendFrame(int arbitrationId, List<int> data) {
		if (_socket == null) throw StateError('Not connected');
		final dlc = data.length.clamp(0, 8);
		final payload = Uint8List(13);
		final bd = ByteData.view(payload.buffer);
		bd.setUint32(0, arbitrationId, Endian.little);
		bd.setUint8(4, dlc);
		// copy data, pad with zeros
		for (var i = 0; i < 8; i++) {
			payload[5 + i] = i < dlc ? data[i] : 0;
		}
		_socket!.add(payload);
	}

	// Read exactly 13 bytes as one frame
	Future<Uint8List> _readExact(int count) async {
		if (_socket == null) throw StateError('Not connected');
		final completer = Completer<Uint8List>();
		final buffer = BytesBuilder();
		late StreamSubscription<List<int>> sub;
		sub = _socket!.listen((chunk) {
			buffer.add(chunk);
			if (buffer.length >= count) {
				sub.cancel();
				final bytes = buffer.toBytes();
				completer.complete(Uint8List.fromList(bytes.sublist(0, count)));
			}
		}, onError: completer.completeError, onDone: () {
			if (!completer.isCompleted) {
				completer.completeError(StateError('Socket closed'));
			}
		}, cancelOnError: true);
		return completer.future;
	}

	Future<_CanFrame> readFrame({Duration timeout = const Duration(seconds: 1)}) async {
		final bytes = await _readExact(13).timeout(timeout);
		final bd = ByteData.sublistView(bytes);
		final arbId = bd.getUint32(0, Endian.little);
		final dlc = bd.getUint8(4);
		final data = bytes.sublist(5, 13);
		return _CanFrame(arbitrationId: arbId, dlc: dlc, data: Uint8List.fromList(data));
	}

	// High-level OBD helpers
	void requestCurrentData(int pid) {
		sendFrame(requestId, [0x02, 0x01, pid, 0, 0, 0, 0, 0]);
	}

	void requestReadDtcs() {
		sendFrame(requestId, [0x01, 0x03, 0, 0, 0, 0, 0, 0]);
	}

	void requestClearDtcs() {
		sendFrame(requestId, [0x01, 0x04, 0, 0, 0, 0, 0, 0]);
	}

	Future<double?> readRpm() async {
		requestCurrentData(0x0C);
		final f = await readFrame();
		if (f.arbitrationId == responseId && f.data[1] == 0x41 && f.data[2] == 0x0C) {
			final a = f.data[3];
			final b = f.data[4];
			return ((a * 256) + b) / 4.0;
		}
		return null;
	}
}

class _CanFrame {
	final int arbitrationId;
	final int dlc;
	final Uint8List data;
	_CanFrame({required this.arbitrationId, required this.dlc, required this.data});
}
```

Usage in a widget (quick test):

```dart
final client = EcuClient(host: '127.0.0.1'); // or 10.0.2.2 on Android emulator
await client.connect();
final rpm = await client.readRpm();
print('RPM: $rpm');
await client.close();
```

You can expand similarly for Speed (PID 0x0D), Coolant Temp (0x05), etc. For DTCs:

```dart
client.requestReadDtcs();
final f = await client.readFrame();
if (f.arbitrationId == EcuClient.responseId && f.data[1] == 0x43) {
	// DTC bytes are pairs: (h, l)
	final dtcs = <String>[];
	for (var i = 2; i + 1 < f.dlc && i + 1 < f.data.length; i += 2) {
		final h = f.data[i];
		final l = f.data[i + 1];
		if (h == 0 && l == 0) break;
		dtcs.add('P${h.toRadixString(16).padLeft(2, '0').toUpperCase()}${l.toRadixString(16).padLeft(2, '0').toUpperCase()}');
	}
	print('DTCs: $dtcs');
}
```

UI tips
- Poll at ~2–5 Hz for dashboard values to keep CPU/battery low
- Debounce DTC reads (only on demand)
- Handle timeouts gracefully and show connection status


## OBD‑II PID formulas used

- RPM (0x0C): `RPM = ((A*256) + B) / 4`
- Speed (0x0D): `km/h = A`
- Coolant Temp (0x05): `°C = A - 40`
- Throttle Position (0x11): `% = A*100/255`
- Engine Load (0x04): `% = A*100/255`
- Intake Air Temp (0x0F): `°C = A - 40`


## Troubleshooting

- “Connection refused” – Start the simulator first; verify it prints that it’s listening on 127.0.0.1:55555
- Firewall blocks – Allow Python in Windows Defender Firewall for Private networks, or add inbound rule for port 55555
- Android emulator can’t reach `127.0.0.1` – use `10.0.2.2` instead
- No responses in app – Ensure you pack frames exactly 13 bytes and use little‑endian for the 4‑byte arbitration_id
- Mixed processes using the virtual CAN bus directly – Don’t. Use the TCP bridge; the virtual bus is process‑local on Windows


## Limitations and next steps

- Single‑frame responses only (no ISO‑TP multi‑frame handling)
- Minimal validation/logging on the wire protocol
- If you prefer a more app‑friendly protocol, consider adding a parallel JSON endpoint in the simulator (e.g., on port 55556) and map requests/responses to JSON. This repo currently ships the binary 13‑byte frame only.


## License

MIT (or your preferred license). Add a LICENSE file if you plan to distribute.

