import 'package:flutter/material.dart';
import 'login_screen.dart';

class VerifyPinScreen extends StatelessWidget {
  const VerifyPinScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const LoginScreen(initialMode: AuthMode.forgotPassword);
  }
}
