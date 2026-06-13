import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/providers/app_provider.dart';
import '../../core/services/auth_service.dart';
import '../../widgets/glass_container.dart';
import '../../widgets/boton_primario.dart';
import '../../widgets/antigravity_logo.dart';

enum AuthMode { login, register, forgotPassword }

class LoginScreen extends StatefulWidget {
  final AuthMode initialMode;
  const LoginScreen({super.key, this.initialMode = AuthMode.login});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  AuthMode _mode = AuthMode.login;
  bool _initializedMode = false;

  // Controllers
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _nombreCtrl = TextEditingController();
  final _passConfirmCtrl = TextEditingController();
  final _pinCtrl = TextEditingController();
  final _newPassCtrl = TextEditingController();

  // Premium Alert Cards Selection
  bool _alertTelegram = true;
  bool _alertGmail = false;

  // Recover Password State
  bool _pinSent = false;
  bool _resetLoading = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initializedMode) {
      _mode = widget.initialMode;
      final routeName = ModalRoute.of(context)?.settings.name;
      if (routeName == '/register') {
        _mode = AuthMode.register;
      } else if (routeName == '/verify_pin') {
        _mode = AuthMode.forgotPassword;
      }
      _initializedMode = true;
    }
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    _nombreCtrl.dispose();
    _passConfirmCtrl.dispose();
    _pinCtrl.dispose();
    _newPassCtrl.dispose();
    super.dispose();
  }

  void _toggleTelegram() {
    setState(() {
      if (_alertTelegram && !_alertGmail) {
        _alertTelegram = false;
        _alertGmail = true;
      } else {
        _alertTelegram = !_alertTelegram;
      }
    });
  }

  void _toggleGmail() {
    setState(() {
      if (_alertGmail && !_alertTelegram) {
        _alertGmail = false;
        _alertTelegram = true;
      } else {
        _alertGmail = !_alertGmail;
      }
    });
  }

  String get _selectedNotificationTarget {
    if (_alertTelegram && _alertGmail) return 'both';
    if (_alertGmail) return 'email';
    return 'telegram';
  }

  Future<void> _login(BuildContext context) async {
    final prov = context.read<AppProvider>();
    final res = await prov.login(_emailCtrl.text.trim(), _passCtrl.text);
    if (!context.mounted) return;
    if (res.exito) {
      // Ir a la pantalla de servidor — se conectará automáticamente o pedirá la IP
      Navigator.pushReplacementNamed(context, '/server');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res.mensajeError ?? 'Error al iniciar sesión')),
      );
    }
  }

  Future<void> _loginGoogle(BuildContext context) async {
    final prov = context.read<AppProvider>();
    final res = await prov.iniciarSesionGoogle();
    if (!context.mounted) return;
    if (res.exito) {
      Navigator.pushReplacementNamed(context, '/server');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res.mensajeError ?? 'Error con Google')),
      );
    }
  }

  Future<void> _register(BuildContext context) async {
    if (_nombreCtrl.text.trim().isEmpty || _emailCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor completa todos los campos obligatorios')),
      );
      return;
    }
    if (_passCtrl.text != _passConfirmCtrl.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Las contraseñas no coinciden')),
      );
      return;
    }

    final prov = context.read<AppProvider>();
    final res = await prov.registrar(_nombreCtrl.text.trim(), _emailCtrl.text.trim(), _passCtrl.text);
    if (!context.mounted) return;
    
    if (res.exito) {
      await prov.setNotificationTarget(_selectedNotificationTarget);
      Navigator.pushReplacementNamed(context, '/server');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res.mensajeError ?? 'Error de registro')),
      );
    }
  }

  Future<void> _sendPin(BuildContext context) async {
    if (_emailCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingresa tu correo para enviar el PIN.')),
      );
      return;
    }
    setState(() => _resetLoading = true);
    final res = await AuthService.requestPasswordReset(_emailCtrl.text.trim());
    setState(() => _resetLoading = false);

    if (!context.mounted) return;
    if (res.exito) {
      setState(() => _pinSent = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('PIN enviado a su correo.')),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res.mensajeError ?? 'Error al enviar PIN')),
      );
    }
  }

  Future<void> _resetPassword(BuildContext context) async {
    if (_pinCtrl.text.trim().isEmpty || _newPassCtrl.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor completa el PIN y la nueva contraseña.')),
      );
      return;
    }
    setState(() => _resetLoading = true);
    final res = await AuthService.resetPasswordWithPin(
      _emailCtrl.text.trim(),
      _pinCtrl.text.trim(),
      _newPassCtrl.text,
    );
    setState(() => _resetLoading = false);

    if (!context.mounted) return;
    if (res.exito) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Contraseña restablecida con éxito.')),
      );
      setState(() {
        _mode = AuthMode.login;
        _pinSent = false;
        _pinCtrl.clear();
        _newPassCtrl.clear();
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res.mensajeError ?? 'Error de validación')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      body: Stack(
        children: [
          _construir_FondoAnimado(),
          Row(
            children: [
              // Lado Izquierdo: Ojo del Halcón Digital Holográfico Animado (Sigue activo continuamente)
              Expanded(
                flex: 5,
                child: Center(
                  child: const AntigravityLogo(size: 300)
                      .animate(onPlay: (c) => c.repeat(reverse: true))
                      .moveY(begin: -10, end: 10, duration: 4.seconds, curve: Curves.easeInOut),
                ).animate().fadeIn(duration: 1.seconds).scale(begin: const Offset(0.8, 0.8)),
              ),
              // Lado Derecho: Formulario con Transición Fluida
              Expanded(
                flex: 4,
                child: Center(
                  child: SingleChildScrollView(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 24.0, horizontal: 16.0),
                      child: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 400),
                        switchInCurve: Curves.easeOutCubic,
                        switchOutCurve: Curves.easeInCubic,
                        transitionBuilder: (child, animation) {
                          return FadeTransition(
                            opacity: animation,
                            child: SlideTransition(
                              position: Tween<Offset>(
                                begin: const Offset(0.15, 0.0),
                                end: Offset.zero,
                              ).animate(animation),
                              child: child,
                            ),
                          );
                        },
                        child: _buildFormContent(cs),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFormContent(ColorScheme cs) {
    switch (_mode) {
      case AuthMode.login:
        return _buildLoginForm(cs);
      case AuthMode.register:
        return _buildRegisterForm(cs);
      case AuthMode.forgotPassword:
        return _buildForgotPasswordForm(cs);
    }
  }

  Widget _buildLoginForm(ColorScheme cs) {
    return GlassContainer(
      key: const ValueKey('login_form'),
      width: 400,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildShieldHeader(cs),
          const SizedBox(height: 24),
          Text(
            'ACCESO RESTRINGIDO',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 22, 
              fontWeight: FontWeight.bold,
              letterSpacing: 2,
              color: cs.onSurface,
            ),
          ),
          const SizedBox(height: 32),
          TextField(
            controller: _emailCtrl,
            decoration: const InputDecoration(labelText: 'Correo Electrónico', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _passCtrl,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Contraseña', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 24),
          BotonPrimario(
            text: 'INICIAR SESIÓN',
            onPressed: () => _login(context),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            height: 56,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              icon: const Icon(Icons.g_mobiledata, size: 28),
              label: const Text('ACCESO CON GOOGLE', style: TextStyle(letterSpacing: 1)),
              onPressed: () => _loginGoogle(context),
            ),
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              TextButton(
                onPressed: () {
                  setState(() {
                    _mode = AuthMode.register;
                  });
                },
                child: const Text('Crear Cuenta'),
              ),
              TextButton(
                onPressed: () {
                  setState(() {
                    _mode = AuthMode.forgotPassword;
                  });
                },
                child: const Text('Olvidé mi contraseña'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRegisterForm(ColorScheme cs) {
    return GlassContainer(
      key: const ValueKey('register_form'),
      width: 400,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildShieldHeader(cs),
          const SizedBox(height: 20),
          Text(
            'REGISTRO DE OPERADOR',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 20, 
              fontWeight: FontWeight.bold,
              letterSpacing: 1.5,
              color: cs.onSurface,
            ),
          ),
          const SizedBox(height: 24),
          TextField(
            controller: _nombreCtrl,
            decoration: const InputDecoration(labelText: 'Nombre Completo', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _emailCtrl,
            decoration: const InputDecoration(labelText: 'Correo Electrónico', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _passCtrl,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Contraseña', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _passConfirmCtrl,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Confirmar Contraseña', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 20),
          // Dynamic Custom Toggles for alerts target
          _buildAlertChannelCards(cs),
          const SizedBox(height: 24),
          BotonPrimario(
            text: 'CREAR CUENTA',
            onPressed: () => _register(context),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () {
              setState(() {
                _mode = AuthMode.login;
              });
            },
            child: const Text('Ya tengo una cuenta'),
          )
        ],
      ),
    );
  }

  Widget _buildForgotPasswordForm(ColorScheme cs) {
    return GlassContainer(
      key: const ValueKey('forgot_form'),
      width: 400,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildShieldHeader(cs),
          const SizedBox(height: 20),
          Text(
            'RECUPERAR ACCESO',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 20, 
              fontWeight: FontWeight.bold,
              letterSpacing: 1.5,
              color: cs.onSurface,
            ),
          ),
          const SizedBox(height: 24),
          TextField(
            controller: _emailCtrl,
            enabled: !_pinSent,
            decoration: const InputDecoration(labelText: 'Correo Electrónico', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          if (!_pinSent)
            BotonPrimario(
              text: 'ENVIAR PIN AL CORREO',
              isLoading: _resetLoading,
              onPressed: () => _sendPin(context),
            ),
          if (_pinSent) ...[
            TextField(
              controller: _pinCtrl,
              decoration: const InputDecoration(labelText: 'PIN de 6 dígitos', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _newPassCtrl,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Nueva Contraseña', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 24),
            BotonPrimario(
              text: 'RESTABLECER CONTRASEÑA',
              isLoading: _resetLoading,
              onPressed: () => _resetPassword(context),
            ),
          ],
          const SizedBox(height: 16),
          TextButton(
            onPressed: () {
              setState(() {
                _mode = AuthMode.login;
                _pinSent = false;
              });
            },
            child: const Text('Volver al inicio de sesión'),
          )
        ],
      ),
    );
  }

  Widget _buildShieldHeader(ColorScheme cs) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          colors: [cs.primary, cs.secondary],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: const Icon(Icons.shield_outlined, color: Colors.white, size: 32),
    )
        .animate(onPlay: (controller) => controller.repeat())
        .shimmer(duration: 2000.ms, color: Colors.white);
  }

  Widget _buildAlertChannelCards(ColorScheme cs) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Text(
            'CANALES DE NOTIFICACIÓN',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: cs.primary,
              letterSpacing: 1.5,
            ),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            // Card 1: Telegram
            Expanded(
              child: InkWell(
                onTap: _toggleTelegram,
                borderRadius: BorderRadius.circular(12),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _alertTelegram 
                        ? cs.primary.withValues(alpha: 0.1) 
                        : cs.surfaceContainerHigh.withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: _alertTelegram 
                          ? cs.primary 
                          : cs.outlineVariant.withValues(alpha: 0.5),
                      width: _alertTelegram ? 2.0 : 1.0,
                    ),
                    boxShadow: _alertTelegram ? [
                      BoxShadow(
                        color: cs.primary.withValues(alpha: 0.25),
                        blurRadius: 10,
                        spreadRadius: 1,
                      )
                    ] : null,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Icon(
                            Icons.send_rounded,
                            color: _alertTelegram ? cs.primary : cs.onSurfaceVariant,
                            size: 20,
                          ),
                          if (_alertTelegram)
                            Icon(
                              Icons.check_circle_rounded,
                              color: cs.primary,
                              size: 16,
                            ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Telegram',
                          style: GoogleFonts.jetBrainsMono(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            color: _alertTelegram ? cs.onSurface : cs.onSurfaceVariant,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Alertas instantáneas vía Bot.',
                          style: TextStyle(
                            fontSize: 10,
                            color: _alertTelegram ? cs.onSurfaceVariant : cs.onSurfaceVariant.withValues(alpha: 0.7),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            // Card 2: Gmail
            Expanded(
              child: InkWell(
                onTap: _toggleGmail,
                borderRadius: BorderRadius.circular(12),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _alertGmail 
                        ? cs.secondary.withValues(alpha: 0.1) 
                        : cs.surfaceContainerHigh.withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: _alertGmail 
                          ? cs.secondary 
                          : cs.outlineVariant.withValues(alpha: 0.5),
                      width: _alertGmail ? 2.0 : 1.0,
                    ),
                    boxShadow: _alertGmail ? [
                      BoxShadow(
                        color: cs.secondary.withValues(alpha: 0.25),
                        blurRadius: 10,
                        spreadRadius: 1,
                      )
                    ] : null,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Icon(
                            Icons.mail_outline_rounded,
                            color: _alertGmail ? cs.secondary : cs.onSurfaceVariant,
                            size: 20,
                          ),
                          if (_alertGmail)
                            Icon(
                              Icons.check_circle_rounded,
                              color: cs.secondary,
                              size: 16,
                            ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Gmail',
                          style: GoogleFonts.jetBrainsMono(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            color: _alertGmail ? cs.onSurface : cs.onSurfaceVariant,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Reportes directos en tu email.',
                          style: TextStyle(
                            fontSize: 10,
                            color: _alertGmail ? cs.onSurfaceVariant : cs.onSurfaceVariant.withValues(alpha: 0.7),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _construir_FondoAnimado() {
    return Stack(
      children: [
        Positioned(
          top: -120,
          left: -120,
          child: _construir_BlobbeFondo(const Color(0xFF1F6FEB), 400),
        ),
        Positioned(
          bottom: -150,
          right: -100,
          child: _construir_BlobbeFondo(const Color(0xFF7C3AED), 450),
        ),
      ],
    );
  }

  Widget _construir_BlobbeFondo(Color color_Blob, double tamano_Blob) {
    return Container(
      width: tamano_Blob,
      height: tamano_Blob,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color_Blob.withValues(alpha: 0.12),
        boxShadow: [
          BoxShadow(
            color: color_Blob.withValues(alpha: 0.3),
            blurRadius: 120,
            spreadRadius: 40,
          ),
        ],
      ),
    );
  }
}

class ShieldPainter extends CustomPainter {
  final Color color;
  ShieldPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;

    final path = Path();
    path.moveTo(size.width / 2, 0);
    path.quadraticBezierTo(size.width * 0.9, size.height * 0.05, size.width, size.height * 0.2);
    path.quadraticBezierTo(size.width, size.height * 0.65, size.width / 2, size.height);
    path.quadraticBezierTo(0, size.height * 0.65, 0, size.height * 0.2);
    path.quadraticBezierTo(size.width * 0.1, size.height * 0.05, size.width / 2, 0);
    path.close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class AnimatedShieldCameraLogo extends StatelessWidget {
  final double size;
  const AnimatedShieldCameraLogo({super.key, this.size = 280});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Círculo de fondo con glow oscuro profundo
          Container(
            width: size * 0.72,
            height: size * 0.72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const RadialGradient(
                colors: [Color(0xFF1A2035), Color(0xFF0D1120)],
                center: Alignment.center,
                radius: 0.9,
              ),
              boxShadow: [
                BoxShadow(color: const Color(0xFF2979FF).withValues(alpha: 0.35), blurRadius: 40, spreadRadius: 8),
                BoxShadow(color: const Color(0xFF0D1120).withValues(alpha: 0.9), blurRadius: 2, spreadRadius: 0),
              ],
              border: Border.all(color: const Color(0xFF2979FF).withValues(alpha: 0.2), width: 1.5),
            ),
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Ícono cámara sutil de fondo
                Icon(
                  Icons.videocam_rounded,
                  size: size * 0.38,
                  color: Colors.white.withValues(alpha: 0.85),
                ),
                // Punto REC en esquina superior derecha
                Positioned(
                  top: size * 0.1,
                  right: size * 0.1,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: size * 0.055,
                        height: size * 0.055,
                        decoration: const BoxDecoration(
                          color: Color(0xFFFF3D57),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(color: Color(0xFFFF3D57), blurRadius: 10, spreadRadius: 2),
                          ],
                        ),
                      ).animate(onPlay: (c) => c.repeat(reverse: true))
                       .fade(begin: 0.15, end: 1.0, duration: 700.ms),
                      const SizedBox(width: 6),
                      Text(
                        'REC',
                        style: GoogleFonts.shareTechMono(
                          color: Colors.white70,
                          fontSize: size * 0.065,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 2,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          )
          .animate(onPlay: (c) => c.repeat(reverse: true))
          .moveY(begin: -6, end: 6, duration: 3.5.seconds, curve: Curves.easeInOut),
        ],
      ),
    );
  }
}
