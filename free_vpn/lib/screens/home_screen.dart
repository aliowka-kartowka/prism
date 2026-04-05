import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_v2ray/flutter_v2ray.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:app_links/app_links.dart';
import '../services/vpn_service.dart';
import '../theme/app_theme.dart';
import '../config/server_config.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Stream<V2RayStatus> _statusStream;
  V2RayStatus _currentStatus = V2RayStatus();
  final VpnService _vpnService = VpnService();
  late final AppLinks _appLinks;
  StreamSubscription<Uri>? _linkSubscription;

  @override
  void initState() {
    super.initState();
    _vpnService.init((status) {
      if (mounted) {
        setState(() {
          _currentStatus = status;
        });
      }
    });
    _statusStream = _vpnService.statusStream;

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );

    _initDeepLinking();
  }

  void _initDeepLinking() {
    _appLinks = AppLinks();
    _linkSubscription = _appLinks.uriLinkStream.listen((uri) {
      debugPrint('Deep Link received: $uri');
      if (uri.path.contains('/sub/')) {
        _handleDeepLink(uri.toString());
      }
    });
  }

  void _handleDeepLink(String url) async {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('⚡️ Importing new configuration...'),
        backgroundColor: AppTheme.accent,
      ),
    );
    await _vpnService.updateConfig(url);
    // Automatically try to connect after import
    if (_currentStatus.state != 'CONNECTED') {
      _handleToggle();
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _linkSubscription?.cancel();
    super.dispose();
  }

  Color get _statusColor {
    switch (_currentStatus.state.toUpperCase()) {
      case 'CONNECTED':
        return AppTheme.online;
      case 'CONNECTING':
        return AppTheme.connecting;
      case 'DISCONNECTED':
      default:
        return AppTheme.offline;
    }
  }

  String get _buttonText {
    switch (_currentStatus.state.toUpperCase()) {
      case 'CONNECTED':
        return 'TAP TO DISCONNECT';
      case 'CONNECTING':
        return 'CONNECTING...';
      case 'DISCONNECTED':
      default:
        return 'TAP TO CONNECT';
    }
  }

  void _handleToggle() async {
    if (_currentStatus.state == 'CONNECTED' || _currentStatus.state == 'CONNECTING') {
      await _vpnService.disconnect();
    } else {
      await _vpnService.connect();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_currentStatus.state == 'CONNECTING') {
      _pulseController.repeat(reverse: true);
    } else {
      _pulseController.stop();
    }

    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppTheme.background, Color(0xFF1A1F2C)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 40),
              Text(
                kAppName,
                style: GoogleFonts.orbitron(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 4,
                  color: AppTheme.accent,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                kAppSubtitle,
                style: GoogleFonts.rajdhani(
                  fontSize: 16,
                  color: Colors.white70,
                  letterSpacing: 2,
                ),
              ),
              const Spacer(),
              // The Big Power Button
              GestureDetector(
                onTap: _handleToggle,
                child: AnimatedBuilder(
                  animation: _pulseController,
                  builder: (context, child) {
                    return Container(
                      width: 240,
                      height: 240,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: _statusColor.withOpacity(0.3 + (_pulseController.value * 0.4)),
                            blurRadius: 30 + (_pulseController.value * 50),
                            spreadRadius: 10 + (_pulseController.value * 20),
                          ),
                          BoxShadow(
                            color: _statusColor.withOpacity(0.5),
                            blurRadius: 10,
                            spreadRadius: 2,
                          ),
                        ],
                        color: AppTheme.surface,
                        border: Border.all(
                          color: _statusColor.withOpacity(0.6),
                          width: 4,
                        ),
                      ),
                      child: Center(
                        child: Icon(
                          Icons.power_settings_new,
                          size: 100,
                          color: _statusColor,
                        ),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 40),
              Text(
                _currentStatus.state.toUpperCase(),
                style: GoogleFonts.rajdhani(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: _statusColor,
                  letterSpacing: 2,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _buttonText,
                style: const TextStyle(color: Colors.white38),
              ),
              const Spacer(),
              // Stats Panel
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildStatCard(
                      label: 'UPLOAD',
                      value: _currentStatus.uploadSpeed.toString(),
                      icon: Icons.unfold_less,
                    ),
                    _buildStatCard(
                      label: 'DOWNLOAD',
                      value: _currentStatus.downloadSpeed.toString(),
                      icon: Icons.unfold_more,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatCard({required String label, required String value, required IconData icon}) {
    return Column(
      children: [
        Icon(icon, color: AppTheme.accent, size: 20),
        const SizedBox(height: 8),
        Text(
          value.isEmpty ? '0 B/s' : value,
          style: GoogleFonts.rajdhani(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: GoogleFonts.rajdhani(
            fontSize: 12,
            color: Colors.white38,
            letterSpacing: 1,
          ),
        ),
      ],
    );
  }
}
