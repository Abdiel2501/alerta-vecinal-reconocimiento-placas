import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const VigSystemApp());
}

class VigSystemApp extends StatelessWidget {
  const VigSystemApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sistema de Vigilancia Inteligente',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.obtener_Tema(),
      home: const LoginScreen(),
    );
  }
}
