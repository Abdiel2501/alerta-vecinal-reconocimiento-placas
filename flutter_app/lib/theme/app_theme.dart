import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // ─── Paleta Táctica ─────────────────────────────────────────────────────
  // Fondo y superficies
  static const Color darkBg       = Color(0xFF060B18); // Negro táctico profundo
  static const Color darkSurface  = Color(0xFF0D1726); // Azul medianoche
  static const Color darkCard     = Color(0xFF111F35); // Tarjetas
  static const Color darkElevated = Color(0xFF1A2D47); // Elementos elevados
  static const Color darkBorder   = Color(0xFF1E3352); // Bordes sutiles

  // Acentos funcionales
  static const Color accentCyan   = Color(0xFF00E5FF); // Primario — acciones
  static const Color accentGreen  = Color(0xFF00C853); // Seguro / En línea
  static const Color accentRed    = Color(0xFFFF1744); // Alerta / Peligro
  static const Color accentAmber  = Color(0xFFFFAB00); // Advertencia
  static const Color accentPurple = Color(0xFF7C4DFF); // Secundario

  // Texto
  static const Color textPrimary   = Color(0xFFECF0F6); // Texto principal
  static const Color textSecondary = Color(0xFF7B90A8); // Texto secundario
  static const Color textMuted     = Color(0xFF4A6080); // Texto apagado

  // ─── Fuentes ────────────────────────────────────────────────────────────
  // UI general: Outfit (moderno, premium, legible en pantallas táctiles)
  static String get fontUi   => GoogleFonts.outfit().fontFamily   ?? 'Outfit';
  // Datos técnicos: JetBrains Mono (IPs, placas, timestamps)
  static String get fontMono => GoogleFonts.jetBrainsMono().fontFamily ?? 'JetBrains Mono';

  // ─── Espaciado ──────────────────────────────────────────────────────────
  static const double espacioXS = 4.0;
  static const double espacioSM = 8.0;
  static const double espacioMD = 16.0;
  static const double espacioLG = 24.0;
  static const double espacioXL = 32.0;

  // ─── Radios ─────────────────────────────────────────────────────────────
  static const double radioSM = 4.0;
  static const double radioMD = 8.0;
  static const double radioLG = 12.0;
  static const double radioXL = 16.0;

  // ─── TextTheme base (Outfit) ─────────────────────────────────────────────
  static TextTheme _buildTextTheme(Color baseColor) {
    return GoogleFonts.outfitTextTheme(TextTheme(
      displayLarge:  TextStyle(color: baseColor, fontWeight: FontWeight.w700, letterSpacing: -0.5),
      displayMedium: TextStyle(color: baseColor, fontWeight: FontWeight.w600),
      displaySmall:  TextStyle(color: baseColor, fontWeight: FontWeight.w600),
      headlineLarge: TextStyle(color: baseColor, fontWeight: FontWeight.w700, letterSpacing: -0.3),
      headlineMedium:TextStyle(color: baseColor, fontWeight: FontWeight.w600),
      headlineSmall: TextStyle(color: baseColor, fontWeight: FontWeight.w600),
      titleLarge:    TextStyle(color: baseColor, fontWeight: FontWeight.w600),
      titleMedium:   TextStyle(color: baseColor, fontWeight: FontWeight.w500),
      titleSmall:    TextStyle(color: baseColor, fontWeight: FontWeight.w500, letterSpacing: 0.1),
      bodyLarge:     TextStyle(color: baseColor, fontWeight: FontWeight.w400),
      bodyMedium:    TextStyle(color: baseColor, fontWeight: FontWeight.w400),
      bodySmall:     TextStyle(color: baseColor.withValues(alpha: 0.8), fontWeight: FontWeight.w400),
      labelLarge:    TextStyle(color: baseColor, fontWeight: FontWeight.w600, letterSpacing: 0.5),
      labelMedium:   TextStyle(color: baseColor, fontWeight: FontWeight.w500, letterSpacing: 0.4),
      labelSmall:    TextStyle(color: baseColor.withValues(alpha: 0.7), fontWeight: FontWeight.w500, letterSpacing: 0.3),
    ));
  }

  // ─── Tema Claro ──────────────────────────────────────────────────────────
  static ThemeData get lightTheme {
    const cs = ColorScheme.light(
      surface:                  Color(0xFFF4F7FC),
      surfaceContainer:         Color(0xFFFFFFFF),
      surfaceContainerHigh:     Color(0xFFEEF2F8),
      surfaceContainerHighest:  Color(0xFFE2E9F3),
      primary:                  Color(0xFF0077B6),
      secondary:                Color(0xFF5A00C8),
      tertiary:                 Color(0xFF006D5B),
      onSurface:                Color(0xFF0C1C30),
      onSurfaceVariant:         Color(0xFF4A6080),
      outline:                  Color(0xFFBCC8D8),
      outlineVariant:           Color(0xFF8CA5BF),
      error:                    Color(0xFFD32F2F),
      errorContainer:           Color(0xFFFFEBEE),
      onPrimary:                Color(0xFFFFFFFF),
      onSecondary:              Color(0xFFFFFFFF),
    );

    return ThemeData(
      brightness:              Brightness.light,
      colorScheme:             cs,
      textTheme:               _buildTextTheme(cs.onSurface),
      scaffoldBackgroundColor: cs.surface,
      dividerColor:            cs.outline,
      appBarTheme: AppBarTheme(
        backgroundColor:  cs.surface,
        foregroundColor:  cs.onSurface,
        elevation:        0,
        titleTextStyle: GoogleFonts.outfit(
          color: cs.onSurface,
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),
      cardTheme: CardThemeData(
        color:       cs.surfaceContainer,
        elevation:   0,
        shape:       RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radioMD),
          side: BorderSide(color: cs.outline.withValues(alpha: 0.5), width: 0.5),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled:           true,
        fillColor:        cs.surfaceContainerHigh,
        contentPadding:   const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border:           OutlineInputBorder(
          borderRadius:  BorderRadius.circular(radioMD),
          borderSide:    BorderSide(color: cs.outline, width: 0.8),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius:  BorderRadius.circular(radioMD),
          borderSide:    BorderSide(color: cs.outline, width: 0.8),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius:  BorderRadius.circular(radioMD),
          borderSide:    BorderSide(color: cs.primary, width: 1.5),
        ),
        labelStyle: GoogleFonts.outfit(color: cs.onSurfaceVariant, fontSize: 13),
        hintStyle:  GoogleFonts.outfit(color: cs.onSurfaceVariant.withValues(alpha: 0.6), fontSize: 13),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          shape:      RoundedRectangleBorder(borderRadius: BorderRadius.circular(radioMD)),
          textStyle:  GoogleFonts.outfit(fontWeight: FontWeight.w600, letterSpacing: 0.4),
          padding:    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          shape:      RoundedRectangleBorder(borderRadius: BorderRadius.circular(radioMD)),
          textStyle:  GoogleFonts.outfit(fontWeight: FontWeight.w600, letterSpacing: 0.4),
          padding:    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        ),
      ),
    );
  }

  // ─── Tema Oscuro Táctico ─────────────────────────────────────────────────
  static ThemeData get darkTheme {
    const cs = ColorScheme.dark(
      surface:                  darkBg,
      surfaceContainer:         darkSurface,
      surfaceContainerHigh:     darkCard,
      surfaceContainerHighest:  darkElevated,
      primary:                  accentCyan,
      secondary:                accentPurple,
      tertiary:                 accentGreen,
      onSurface:                textPrimary,
      onSurfaceVariant:         textSecondary,
      outline:                  darkBorder,
      outlineVariant:           Color(0xFF2E4A66),
      error:                    accentRed,
      errorContainer:           Color(0xFF3D000A),
      onPrimary:                Color(0xFF000000),
      onSecondary:              Color(0xFFFFFFFF),
      onTertiary:               Color(0xFF000000),
    );

    return ThemeData(
      brightness:              Brightness.dark,
      colorScheme:             cs,
      textTheme:               _buildTextTheme(textPrimary),
      scaffoldBackgroundColor: darkBg,
      dividerColor:            darkBorder,

      appBarTheme: AppBarTheme(
        backgroundColor:  darkBg,
        foregroundColor:  textPrimary,
        elevation:        0,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: GoogleFonts.outfit(
          color:       textPrimary,
          fontSize:    18,
          fontWeight:  FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),

      cardTheme: CardThemeData(
        color:     darkCard,
        elevation: 0,
        shape:     RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radioMD),
          side: const BorderSide(color: darkBorder, width: 0.5),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled:         true,
        fillColor:      darkCard,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radioMD),
          borderSide:   const BorderSide(color: darkBorder, width: 0.8),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radioMD),
          borderSide:   const BorderSide(color: darkBorder, width: 0.8),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radioMD),
          borderSide:   const BorderSide(color: accentCyan, width: 1.5),
        ),
        labelStyle: GoogleFonts.outfit(color: textSecondary, fontSize: 13),
        hintStyle:  GoogleFonts.outfit(color: textMuted, fontSize: 13),
      ),

      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accentCyan,
          foregroundColor: Colors.black,
          shape:     RoundedRectangleBorder(borderRadius: BorderRadius.circular(radioMD)),
          textStyle: GoogleFonts.outfit(fontWeight: FontWeight.w700, letterSpacing: 0.5),
          padding:   const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          elevation: 0,
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: accentCyan,
          side:      const BorderSide(color: accentCyan, width: 1),
          shape:     RoundedRectangleBorder(borderRadius: BorderRadius.circular(radioMD)),
          textStyle: GoogleFonts.outfit(fontWeight: FontWeight.w600, letterSpacing: 0.4),
          padding:   const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: accentCyan,
          textStyle: GoogleFonts.outfit(fontWeight: FontWeight.w600),
        ),
      ),

      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(foregroundColor: textSecondary),
      ),

      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color:        darkElevated,
          borderRadius: BorderRadius.circular(radioSM),
          border:       const Border.fromBorderSide(BorderSide(color: darkBorder, width: 0.5)),
        ),
        textStyle: GoogleFonts.outfit(color: textPrimary, fontSize: 11),
        padding:   const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor:   darkElevated,
        contentTextStyle:  GoogleFonts.outfit(color: textPrimary, fontSize: 13),
        shape:             RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radioMD),
          side: const BorderSide(color: darkBorder, width: 0.5),
        ),
        behavior: SnackBarBehavior.floating,
        insetPadding: const EdgeInsets.all(12),
      ),

      dialogTheme: DialogThemeData(
        backgroundColor:  darkCard,
        surfaceTintColor: Colors.transparent,
        shape:            RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radioLG),
          side: const BorderSide(color: darkBorder, width: 0.5),
        ),
        titleTextStyle: GoogleFonts.outfit(
          color: textPrimary, fontSize: 18, fontWeight: FontWeight.w700,
        ),
        contentTextStyle: GoogleFonts.outfit(color: textSecondary, fontSize: 14),
      ),

      dataTableTheme: DataTableThemeData(
        headingRowColor: WidgetStateProperty.all(darkElevated),
        dataRowColor:    WidgetStateProperty.all(darkSurface),
        decoration:      BoxDecoration(border: Border.all(color: darkBorder, width: 0.5)),
        headingTextStyle: GoogleFonts.jetBrainsMono(
          color: accentCyan, fontWeight: FontWeight.w700, fontSize: 12, letterSpacing: 0.5,
        ),
        dataTextStyle: GoogleFonts.jetBrainsMono(
          color: textPrimary, fontSize: 12,
        ),
        columnSpacing: 24,
      ),

      chipTheme: ChipThemeData(
        backgroundColor:  darkCard,
        side:             const BorderSide(color: darkBorder, width: 0.5),
        labelStyle:       GoogleFonts.outfit(color: textSecondary, fontSize: 12),
        shape:            RoundedRectangleBorder(borderRadius: BorderRadius.circular(radioSM)),
        padding:          const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      ),

      tabBarTheme: TabBarThemeData(
        labelColor:        accentCyan,
        unselectedLabelColor: textMuted,
        indicatorColor:    accentCyan,
        indicatorSize:     TabBarIndicatorSize.tab,
        labelStyle:        GoogleFonts.outfit(fontWeight: FontWeight.w700, fontSize: 12, letterSpacing: 0.5),
        unselectedLabelStyle: GoogleFonts.outfit(fontWeight: FontWeight.w500, fontSize: 12),
      ),

      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color:            accentCyan,
        linearTrackColor: darkBorder,
      ),

      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((s) =>
          s.contains(WidgetState.selected) ? accentCyan : textMuted),
        trackColor: WidgetStateProperty.resolveWith((s) =>
          s.contains(WidgetState.selected)
            ? accentCyan.withValues(alpha: 0.3)
            : darkElevated),
      ),

      listTileTheme: ListTileThemeData(
        iconColor:    textSecondary,
        textColor:    textPrimary,
        tileColor:    Colors.transparent,
        shape:        RoundedRectangleBorder(borderRadius: BorderRadius.circular(radioSM)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      ),
    );
  }
}

