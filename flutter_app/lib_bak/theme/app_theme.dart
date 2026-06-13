import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color color_Fondo = Color(0xFF070C18);
  static const Color color_Superficie = Color(0xFF0D1526);
  static const Color color_Tarjeta = Color(0xFF111E35);
  static const Color color_Acento = Color(0xFF00D4FF);
  static const Color color_AcentoSecundario = Color(0xFF0099CC);
  static const Color color_AcentoGradiente = Color(0xFF7C3AED);
  static const Color color_Texto = Color(0xFFE2E8F0);
  static const Color color_TextoTenue = Color(0xFF64748B);
  static const Color color_Borde = Color(0xFF1E3A5F);
  static const Color color_BordereActivo = Color(0xFF00D4FF);

  static ThemeData obtener_Tema() {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: color_Fondo,
      colorScheme: const ColorScheme.dark(
        primary: color_Acento,
        surface: color_Superficie,
        onSurface: color_Texto,
        secondary: color_AcentoSecundario,
      ),
      textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).apply(
        bodyColor: color_Texto,
        displayColor: color_Texto,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF0D1526),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: color_Borde, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: color_Borde, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: color_BordereActivo, width: 1.5),
        ),
        labelStyle: const TextStyle(color: color_TextoTenue, fontSize: 14),
        hintStyle: const TextStyle(color: color_TextoTenue, fontSize: 14),
      ),
    );
  }
}
