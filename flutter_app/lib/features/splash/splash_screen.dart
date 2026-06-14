import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../core/providers/app_provider.dart';
import '../../core/services/server_connection_service.dart';
import '../../widgets/antigravity_logo.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkSession();
  }

  Future<void> _checkSession() async {
    await Future.delayed(const Duration(milliseconds: 2800));
    if (!mounted) return;
    final provider = Provider.of<AppProvider>(context, listen: false);
    final hasSession = await provider.verificarSesionActiva();
    if (!mounted) return;
    if (hasSession) {
      // Iniciar conexión al servidor en paralelo mientras navegamos directamente al dashboard
      final serverSvc = Provider.of<ServerConnectionService>(context, listen: false);
      serverSvc.initialize(); // No-await: se conecta en segundo plano
      Navigator.pushReplacementNamed(context, '/dashboard');
    } else {
      Navigator.pushReplacementNamed(context, '/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF060912), Color(0xFF0D1120), Color(0xFF101828)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const AntigravityLogo(size: 220)
              .animate()
              .fadeIn(duration: 600.ms)
              .scale(begin: const Offset(0.7, 0.7), end: const Offset(1.0, 1.0), duration: 700.ms, curve: Curves.easeOutBack),

            const SizedBox(height: 48),

            Text(
              'ALERTA VECINAL',
              style: GoogleFonts.inter(
                fontSize: 30,
                fontWeight: FontWeight.w900,
                letterSpacing: 6,
                color: Colors.white,
              ),
            ).animate().fadeIn(delay: 500.ms, duration: 700.ms).slideY(begin: 0.3, end: 0),

            const SizedBox(height: 8),

            Text(
              'Sistema de Vigilancia Inteligente',
              style: GoogleFonts.inter(
                fontSize: 13,
                letterSpacing: 1.5,
                color: const Color(0xFF00D4FF).withValues(alpha: 0.8),
                fontWeight: FontWeight.w400,
              ),
            ).animate().fadeIn(delay: 800.ms, duration: 700.ms),

            const SizedBox(height: 64),

            SizedBox(
              width: 120,
              child: LinearProgressIndicator(
                backgroundColor: Colors.white.withValues(alpha: 0.06),
                valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF00D4FF)),
                minHeight: 2,
              ),
            ).animate().fadeIn(delay: 1000.ms, duration: 500.ms),
          ],
        ),
      ),
    );
  }
}
