import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math' as math;

/// Logo orbital animado — evoca una lente de cámara de alta tecnología.
/// Úsalo en Splash y Login.
class AntigravityLogo extends StatelessWidget {
  final double size;

  const AntigravityLogo({super.key, this.size = 200});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [

          // ─── Resplandor de fondo (glow azul profundo) ─────────────────
          Container(
            width: size * 0.78,
            height: size * 0.78,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFF00D4FF).withValues(alpha: 0.07),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF0066FF).withValues(alpha: 0.45),
                  blurRadius: size * 0.45,
                  spreadRadius: size * 0.08,
                ),
              ],
            ),
          )
          .animate(onPlay: (c) => c.repeat(reverse: true))
          .scale(
            begin: const Offset(0.88, 0.88),
            end: const Offset(1.08, 1.08),
            duration: 2.5.seconds,
            curve: Curves.easeInOutSine,
          ),

          // ─── Anillo exterior segmentado (gira sentido horario) ─────────
          // → evoca el anillo de enfoque de un objetivo fotográfico
          CustomPaint(
            size: Size(size, size),
            painter: _RingPainter(
              color: const Color(0xFF00D4FF),
              strokeWidth: size * 0.022,
              dashes: 16,
            ),
          )
          .animate(onPlay: (c) => c.repeat())
          .rotate(duration: 10.seconds, begin: 0, end: 1, curve: Curves.linear),

          // ─── Anillo medio (gira sentido antihorario más rápido) ─────────
          // → evoca el ajuste de apertura del lente
          CustomPaint(
            size: Size(size * 0.68, size * 0.68),
            painter: _RingPainter(
              color: const Color(0xFF6633FF),
              strokeWidth: size * 0.038,
              dashes: 6,
            ),
          )
          .animate(onPlay: (c) => c.repeat())
          .rotate(duration: 5.seconds, begin: 1, end: 0, curve: Curves.linear),

          // ─── Cuerpo central — lente de la cámara ────────────────────────
          Container(
            width: size * 0.34,
            height: size * 0.34,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const RadialGradient(
                colors: [
                  Color(0xFF1A2A4A),   // azul marino oscuro (vidrio del lente)
                  Color(0xFF0A1020),
                ],
                stops: [0.0, 1.0],
              ),
              border: Border.all(
                color: const Color(0xFF00D4FF).withValues(alpha: 0.6),
                width: size * 0.015,
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00D4FF).withValues(alpha: 0.4),
                  blurRadius: size * 0.08,
                  spreadRadius: size * 0.01,
                ),
              ],
            ),
            // Reflejo interno del lente
            child: Center(
              child: Container(
                width: size * 0.10,
                height: size * 0.10,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withValues(alpha: 0.15),
                ),
              ),
            ),
          )
          .animate(onPlay: (c) => c.repeat(reverse: true))
          .shimmer(duration: 2.seconds, color: const Color(0xFF00D4FF).withValues(alpha: 0.4))
          .scale(
            begin: const Offset(0.9, 0.9),
            end: const Offset(1.05, 1.05),
            duration: 2.seconds,
            curve: Curves.easeInOut,
          ),

          // ─── Punto REC pulsante ──────────────────────────────────────────
          Positioned(
            top: size * 0.14,
            right: size * 0.14,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: size * 0.07,
                  height: size * 0.07,
                  decoration: const BoxDecoration(
                    color: Color(0xFFFF3D57),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: Color(0xFFFF3D57),
                        blurRadius: 10,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                )
                .animate(onPlay: (c) => c.repeat(reverse: true))
                .fade(begin: 0.1, end: 1.0, duration: 700.ms),
                SizedBox(width: size * 0.025),
                Text(
                  'REC',
                  style: GoogleFonts.shareTechMono(
                    color: Colors.white70,
                    fontSize: size * 0.072,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.5,
                  ),
                ),
              ],
            ),
          ),

        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  final Color color;
  final double strokeWidth;
  final int dashes;

  _RingPainter({required this.color, required this.strokeWidth, required this.dashes});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width / 2) - strokeWidth / 2;

    final sweepAngle = (2 * math.pi) / (dashes * 2);
    for (int i = 0; i < dashes * 2; i++) {
      if (i % 2 == 0) {
        canvas.drawArc(
          Rect.fromCircle(center: center, radius: radius),
          i * sweepAngle,
          sweepAngle,
          false,
          paint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
