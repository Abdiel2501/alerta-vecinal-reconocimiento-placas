import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // ─── Fuentes ───────────────────────────────────────────────────────────
  static String fontUi = GoogleFonts.inter().fontFamily ?? 'Inter';
  static String fontMono = GoogleFonts.jetBrainsMono().fontFamily ?? 'JetBrains Mono';

  // ─── Espaciado ─────────────────────────────────────────────────────────
  static const double espacioXS = 4.0;
  static const double espacioSM = 8.0;
  static const double espacioMD = 16.0;
  static const double espacioLG = 24.0;
  static const double espacioXL = 32.0;

  // ─── Radios ────────────────────────────────────────────────────────────
  static const double radioSM = 4.0; // Bordes más finos para look táctico
  static const double radioMD = 8.0;
  static const double radioLG = 12.0;

  // ─── Tema Claro (Blancos y Azules) ─────────────────────────────────────
  static ThemeData get lightTheme {
    return ThemeData(
      brightness: Brightness.light,
      fontFamily: fontUi,
      colorScheme: const ColorScheme.light(
        surface: Color(0xFFF8FAFC), 
        surfaceContainer: Color(0xFFFFFFFF), 
        surfaceContainerHigh: Color(0xFFF1F5F9), 
        surfaceContainerHighest: Color(0xFFE2E8F0),
        primary: Color(0xFF00E5FF), // Cyan Neón brillante para el brillo
        secondary: Color(0xFF7C3AED), // Púrpura eléctrico
        tertiary: Color(0xFFD946EF), 
        onSurface: Color(0xFF0F172A), 
        onSurfaceVariant: Color(0xFF475569), 
        outline: Color(0xFFCBD5E1), 
        outlineVariant: Color(0xFF94A3B8), 
        error: Color(0xFFDC2626),
        errorContainer: Color(0xFFFEE2E2),
      ),
      scaffoldBackgroundColor: const Color(0xFFF8FAFC),
      dividerColor: const Color(0xFFCBD5E1),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFFF8FAFC),
        foregroundColor: Color(0xFF0F172A),
        elevation: 0,
      ),
    );
  }

  // ─── Tema Oscuro (Táctico) ─────────────────────────────────────────────
  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      fontFamily: fontUi,
      colorScheme: const ColorScheme.dark(
        surface: Color(0xFF0A1128), // Azul medianoche táctico
        surfaceContainer: Color(0xFF131F3A), 
        surfaceContainerHigh: Color(0xFF1E293B),
        surfaceContainerHighest: Color(0xFF2E3D52),
        primary: Color(0xFF00FFFF), // Cian Neón puro
        secondary: Color(0xFF8A2BE2), // Púrpura radiante
        tertiary: Color(0xFFFF00FF), 
        onSurface: Color(0xFFFFFFFF), 
        onSurfaceVariant: Color(0xFF94A3B8), 
        outline: Color(0xFF1E293B), // Bordes tácticos finos
        outlineVariant: Color(0xFF475569), 
        error: Color(0xFFFF003C), // Rojo Carmesí Alerta
        errorContainer: Color(0xFF3B0000),
      ),
      scaffoldBackgroundColor: const Color(0xFF0A1128),
      dividerColor: const Color(0xFF1E293B),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF0A1128),
        foregroundColor: Color(0xFFFFFFFF),
        elevation: 0,
      ),
      dataTableTheme: DataTableThemeData(
        headingRowColor: WidgetStateProperty.all(const Color(0xFF1E293B)),
        dataRowColor: WidgetStateProperty.all(const Color(0xFF131F3A)),
        decoration: BoxDecoration(
          border: Border.all(color: const Color(0xFF1E293B)),
        ),
        headingTextStyle: GoogleFonts.jetBrainsMono(
          color: const Color(0xFF00FFFF), fontWeight: FontWeight.bold
        ),
        dataTextStyle: GoogleFonts.jetBrainsMono(color: const Color(0xFFE2E8F0)),
      ),
    );
  }
}
