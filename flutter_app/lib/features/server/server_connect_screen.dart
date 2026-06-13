import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/services/server_connection_service.dart';

/// Pantalla de conexión al Servidor IA de Red Local.
///
/// Aparece después del login si no hay servidor configurado o si se perdió la conexión.
/// El cliente solo tiene que tocar "Buscar Servidor" — la app hace todo sola.
class ServerConnectScreen extends StatefulWidget {
  const ServerConnectScreen({super.key});

  @override
  State<ServerConnectScreen> createState() => _ServerConnectScreenState();
}

class _ServerConnectScreenState extends State<ServerConnectScreen>
    with SingleTickerProviderStateMixin {
  final _ipController = TextEditingController();
  final _portController = TextEditingController(text: '8765');
  bool _showManual = false;
  bool _isConnecting = false;
  String _statusMsg = '';
  late AnimationController _pulseCtrl;
  Timer? _navTimer;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    // Si ya hay un servidor guardado, intentar conectar automáticamente
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final svc = context.read<ServerConnectionService>();
      svc.addListener(_onServiceChange);
      if (svc.serverIp.isNotEmpty && svc.state != ServerConnectionState.connected) {
        svc.connect(svc.serverIp, port: svc.serverPort);
      }
    });
  }

  void _onServiceChange() {
    if (!mounted) return;
    final svc = context.read<ServerConnectionService>();
    setState(() {
      switch (svc.state) {
        case ServerConnectionState.discovering:
          _statusMsg = '🔍 Buscando servidor en la red local...';
          _isConnecting = true;
        case ServerConnectionState.connecting:
          _statusMsg = '⚡ Conectando a ${svc.serverAddress}...';
          _isConnecting = true;
        case ServerConnectionState.connected:
          _statusMsg = '✅ ¡Conectado! Abriendo sistema...';
          _isConnecting = false;
          // Navegar al dashboard tras un breve delay para que el usuario vea el mensaje
          _navTimer?.cancel();
          _navTimer = Timer(const Duration(milliseconds: 800), () {
            if (mounted) Navigator.pushReplacementNamed(context, '/dashboard');
          });
        case ServerConnectionState.error:
          _statusMsg = svc.errorMessage;
          _isConnecting = false;
        case ServerConnectionState.disconnected:
          _statusMsg = '';
          _isConnecting = false;
      }
    });
  }

  Future<void> _autoDiscover() async {
    final svc = context.read<ServerConnectionService>();
    svc.addListener(_onServiceChange);
    setState(() {
      _isConnecting = true;
      _statusMsg = '🔍 Buscando servidor en la red local...';
    });
    await svc.discoverServer();
  }

  Future<void> _connectManual() async {
    final ip = _ipController.text.trim();
    final port = int.tryParse(_portController.text.trim()) ?? 8765;
    if (ip.isEmpty) return;

    final svc = context.read<ServerConnectionService>();
    svc.addListener(_onServiceChange);
    await svc.connect(ip, port: port, saveIp: true);
  }

  @override
  void dispose() {
    _navTimer?.cancel();
    _pulseCtrl.dispose();
    _ipController.dispose();
    _portController.dispose();
    try {
      context.read<ServerConnectionService>().removeListener(_onServiceChange);
    } catch (_) {}
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: const Color(0xFF080C18),
      body: Stack(
        children: [
          // ── Fondo animado tipo radar ─────────────────────────────────────
          _buildRadarBackground(cs),

          // ── Contenido central ────────────────────────────────────────────
          Center(
            child: SizedBox(
              width: 460,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Logo / icono
                  _buildServerIcon(cs),
                  const SizedBox(height: 32),

                  // Título
                  Text(
                    'SERVIDOR IA',
                    style: GoogleFonts.shareTechMono(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: cs.primary,
                      letterSpacing: 6,
                    ),
                  ).animate().fadeIn(duration: 600.ms),
                  const SizedBox(height: 8),
                  Text(
                    'Conecta tu dispositivo al Motor de Inteligencia Artificial\nde la red local para comenzar la vigilancia.',
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: Colors.white38,
                      height: 1.6,
                    ),
                    textAlign: TextAlign.center,
                  ).animate().fadeIn(duration: 600.ms, delay: 200.ms),

                  const SizedBox(height: 48),

                  // ── Botón principal: Auto-descubrimiento ─────────────────
                  if (!_isConnecting)
                    _buildMainButton(cs)
                  else
                    _buildConnectingIndicator(cs),

                  const SizedBox(height: 24),

                  // Mensaje de estado
                  if (_statusMsg.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      decoration: BoxDecoration(
                        color: _statusMsg.contains('✅')
                            ? cs.primary.withValues(alpha: 0.15)
                            : _statusMsg.contains('❌') || _statusMsg.contains('No se encontró')
                                ? cs.error.withValues(alpha: 0.15)
                                : Colors.white.withValues(alpha: 0.05),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: _statusMsg.contains('✅')
                              ? cs.primary.withValues(alpha: 0.4)
                              : _statusMsg.contains('❌') || _statusMsg.contains('No se encontró')
                                  ? cs.error.withValues(alpha: 0.4)
                                  : Colors.white12,
                        ),
                      ),
                      child: Text(
                        _statusMsg,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 12,
                          color: _statusMsg.contains('✅')
                              ? cs.primary
                              : _statusMsg.contains('No se encontró')
                                  ? cs.error
                                  : Colors.white54,
                          height: 1.5,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ).animate().fadeIn(duration: 300.ms),

                  const SizedBox(height: 32),

                  // ── Sección de IP Manual (colapsable) ────────────────────
                  _buildManualSection(cs),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRadarBackground(ColorScheme cs) {
    return AnimatedBuilder(
      animation: _pulseCtrl,
      builder: (context, _) {
        return CustomPaint(
          painter: _RadarPainter(
            progress: _pulseCtrl.value,
            color: cs.primary,
          ),
          child: const SizedBox.expand(),
        );
      },
    );
  }

  Widget _buildServerIcon(ColorScheme cs) {
    return AnimatedBuilder(
      animation: _pulseCtrl,
      builder: (_, __) => Container(
        width: 100,
        height: 100,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(
            color: cs.primary.withValues(alpha: 0.3 + 0.4 * _pulseCtrl.value),
            width: 2,
          ),
          color: cs.primary.withValues(alpha: 0.08),
          boxShadow: [
            BoxShadow(
              color: cs.primary.withValues(alpha: 0.15 * _pulseCtrl.value),
              blurRadius: 40,
              spreadRadius: 10,
            ),
          ],
        ),
        child: Icon(Icons.dns_rounded, size: 48, color: cs.primary),
      ),
    ).animate().fadeIn(duration: 800.ms).scale(begin: const Offset(0.8, 0.8));
  }

  Widget _buildMainButton(ColorScheme cs) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          height: 54,
          child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: cs.primary,
              foregroundColor: cs.onPrimary,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              elevation: 8,
              shadowColor: cs.primary.withValues(alpha: 0.5),
            ),
            icon: const Icon(Icons.radar, size: 22),
            label: Text(
              'BUSCAR SERVIDOR EN MI RED',
              style: GoogleFonts.shareTechMono(
                fontWeight: FontWeight.bold,
                fontSize: 14,
                letterSpacing: 1.5,
              ),
            ),
            onPressed: _autoDiscover,
          ),
        ).animate().fadeIn(duration: 500.ms, delay: 400.ms).slideY(begin: 0.2, end: 0),
        const SizedBox(height: 12),
        TextButton(
          onPressed: () => setState(() => _showManual = !_showManual),
          child: Text(
            _showManual ? '▲ Ocultar entrada manual' : '▼ Ingresar IP manualmente',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 12,
              color: Colors.white30,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildConnectingIndicator(ColorScheme cs) {
    return Column(
      children: [
        SizedBox(
          width: 48,
          height: 48,
          child: CircularProgressIndicator(
            color: cs.primary,
            strokeWidth: 2,
          ),
        ),
        const SizedBox(height: 16),
        TextButton(
          onPressed: () {
            context.read<ServerConnectionService>().disconnect();
            setState(() => _isConnecting = false);
          },
          child: Text(
            'Cancelar',
            style: GoogleFonts.jetBrainsMono(fontSize: 12, color: Colors.white30),
          ),
        ),
      ],
    );
  }

  Widget _buildManualSection(ColorScheme cs) {
    if (!_showManual) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'CONEXIÓN MANUAL',
            style: GoogleFonts.shareTechMono(
              fontSize: 11,
              color: Colors.white38,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                flex: 3,
                child: TextField(
                  controller: _ipController,
                  style: GoogleFonts.jetBrainsMono(color: Colors.white, fontSize: 14),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(RegExp(r'[0-9\.]'))
                  ],
                  decoration: InputDecoration(
                    labelText: 'IP del servidor',
                    hintText: '192.168.1.105',
                    labelStyle: const TextStyle(color: Colors.white38),
                    hintStyle: const TextStyle(color: Colors.white12),
                    border: const OutlineInputBorder(),
                    enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: cs.primary.withValues(alpha: 0.3)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: cs.primary),
                    ),
                    prefixIcon: const Icon(Icons.computer, color: Colors.white24),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 1,
                child: TextField(
                  controller: _portController,
                  style: GoogleFonts.jetBrainsMono(color: Colors.white, fontSize: 14),
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: InputDecoration(
                    labelText: 'Puerto',
                    labelStyle: const TextStyle(color: Colors.white38),
                    border: const OutlineInputBorder(),
                    enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: cs.primary.withValues(alpha: 0.3)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: cs.primary),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              style: OutlinedButton.styleFrom(
                foregroundColor: cs.primary,
                side: BorderSide(color: cs.primary.withValues(alpha: 0.5)),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              onPressed: _connectManual,
              child: Text(
                'CONECTAR',
                style: GoogleFonts.shareTechMono(
                  fontWeight: FontWeight.bold,
                  letterSpacing: 2,
                ),
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms);
  }
}

// ─── Painter: Radar animado de fondo ─────────────────────────────────────────

class _RadarPainter extends CustomPainter {
  final double progress;
  final Color color;
  _RadarPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxR = size.longestSide * 0.8;

    for (int i = 1; i <= 4; i++) {
      final r = maxR * i / 4;
      final alpha = (0.03 + 0.04 * progress * (1 - i / 5)).clamp(0.0, 1.0);
      final paint = Paint()
        ..color = color.withValues(alpha: alpha)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.0;
      canvas.drawCircle(center, r, paint);
    }

    // Pulso que se expande
    final pulseR = maxR * 0.5 * progress;
    final pulsePaint = Paint()
      ..color = color.withValues(alpha: (0.15 * (1 - progress)).clamp(0.0, 1.0))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawCircle(center, pulseR, pulsePaint);
  }

  @override
  bool shouldRepaint(_RadarPainter old) => old.progress != progress;
}
