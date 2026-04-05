import 'dart:async';
import 'package:flutter_v2ray/flutter_v2ray.dart';
import '../config/server_config.dart';

class VpnService {
  static final VpnService _instance = VpnService._internal();
  factory VpnService() => _instance;
  VpnService._internal();

  late final FlutterV2ray _flutterV2ray;
  final StreamController<V2RayStatus> _statusController = StreamController<V2RayStatus>.broadcast();
  
  Stream<V2RayStatus> get statusStream => _statusController.stream;
  V2RayStatus _lastStatus = V2RayStatus();
  V2RayStatus get lastStatus => _lastStatus;
  String _currentConfig = kServerLink;
  bool _isInitialized = false;

  void init(Function(V2RayStatus) onStatus) {
    _flutterV2ray = FlutterV2ray(
      onStatusChanged: (status) {
        _lastStatus = status;
        _statusController.add(status);
        onStatus(status);
      },
    );
  }

  Future<void> updateConfig(String newConfig) async {
    _currentConfig = newConfig;
  }

  Future<void> initializeV2Ray() async {
    if (_isInitialized) return;
    await _flutterV2ray.initializeV2Ray();
    _isInitialized = true;
  }

  Future<bool> connect() async {
    await initializeV2Ray();
    if (await _flutterV2ray.requestPermission()) {
      V2RayURL parser = FlutterV2ray.parseFromURL(_currentConfig);
      await _flutterV2ray.startV2Ray(
        remark: parser.remark,
        config: parser.getFullConfiguration(),
        proxyOnly: false,
      );
      return true;
    }
    return false;
  }

  Future<void> disconnect() async {
    await _flutterV2ray.stopV2Ray();
  }

  Future<int> getDelay() async {
    V2RayURL parser = FlutterV2ray.parseFromURL(_currentConfig);
    return await _flutterV2ray.getServerDelay(config: parser.getFullConfiguration());
  }
}
