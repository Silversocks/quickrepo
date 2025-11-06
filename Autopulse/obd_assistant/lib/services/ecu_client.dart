import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

class EcuClient {
  final String host;
  final int port;
  Socket? _socket;

  EcuClient({required this.host, this.port = 55554});
  // Latest live values
  double rpm = 0;
  int speed = 0;
  double throttle = 0;
  int coolant = 0;
  double engineLoad = 0;
  int intakeTemp = 0;

  // StreamController to notify UI
  final StreamController<void> _updateController = StreamController.broadcast();
  Stream<void> get onUpdate => _updateController.stream;

  static const int requestId = 0x7DF;
  static const int responseId = 0x7E8;

  // Buffer for incoming bytes
  final BytesBuilder _buffer = BytesBuilder();

  Future<void> connect({Duration timeout = const Duration(seconds: 5)}) async {
    _socket = await Socket.connect(host, port, timeout: timeout);

    // Single socket listener
    _socket!.listen(_handleTcpData, onDone: () {
      print('Socket closed by ECU');
    }, onError: (e) {
      print('Socket error: $e');
    });
  }

  Future<void> close() async {
    await _socket?.close();
    await _updateController.close();
  }

  void sendFrame(int arbitrationId, List<int> data) {
    if (_socket == null) throw StateError('Not connected');
    final dlc = data.length.clamp(0, 8);
    final payload = Uint8List(13);
    final bd = ByteData.view(payload.buffer);
    bd.setUint32(0, arbitrationId, Endian.little);
    bd.setUint8(4, dlc);
    for (var i = 0; i < 8; i++) {
      payload[5 + i] = i < dlc ? data[i] : 0;
    }
    _socket!.add(payload);
  }

  void _handleTcpData(List<int> data) {
    _buffer.add(data);

    while (_buffer.length >= 13) {
      final frameBytes = _buffer.takeBytes().sublist(0, 13);
      _buffer.add(frameBytes.sublist(13)); // keep leftover bytes

      final bd = ByteData.sublistView(frameBytes);
      final arbId = bd.getUint32(0, Endian.little);
      final dlc = bd.getUint8(4);
      final frameData = frameBytes.sublist(5, 5 + 8);

      // Parse only responses from ECU
      if (arbId == responseId && dlc > 0) {
        if (frameData[1] == 0x41) {
          switch (frameData[2]) {
            case 0x0C: // RPM
              rpm = ((frameData[3] * 256) + frameData[4]) / 4.0;
              break;
            case 0x0D: // Speed
              speed = frameData[3];
              break;
            case 0x05: // Coolant
              coolant = frameData[3] - 40;
              break;
            case 0x11: // Throttle
              throttle = (frameData[3] * 100) / 255;
              break;
            case 0x04: // Engine load
              engineLoad = (frameData[3] * 100) / 255;
              break;
            case 0x0F: // Intake Temp
              intakeTemp = frameData[3] - 40;
              break;
          }

          // Notify UI
          _updateController.add(null);
        }
      }
    }
  }

  // High-level helpers
  void requestCurrentData(int pid) {
    sendFrame(requestId, [0x02, 0x01, pid, 0, 0, 0, 0, 0]);
  }

  Future<void> requestAll() async {
    for (var pid in [0x0C, 0x0D, 0x05, 0x11, 0x04, 0x0F]) {
      requestCurrentData(pid);
    }
  }
}