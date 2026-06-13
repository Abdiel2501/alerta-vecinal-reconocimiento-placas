import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:math';
import '../models/user_model.dart';
import 'database_service.dart';
import 'gmail_service.dart';

class AuthResult {
  final bool exito;
  final String? mensajeError;
  final UserModel? usuario;

  AuthResult({required this.exito, this.mensajeError, this.usuario});
}

class AuthService {
  // TODO: INSERT_CLIENT_ID
  // Para que el inicio de sesión con Google sea real en Escritorio y Android,
  // asegúrate de configurar google_sign_in_windows y usar tu Client ID oficial.
  // static final GoogleSignIn _googleSignIn = GoogleSignIn(
  //   clientId: 'TU_CLIENT_ID.apps.googleusercontent.com', 
  //   scopes: ['email', 'profile'],
  // );

  static String _hashPassword(String password, String salt) {
    final bytes = utf8.encode(password + salt);
    return sha256.convert(bytes).toString();
  }

  static String _generateSalt() {
    final random = Random.secure();
    return List<int>.generate(16, (i) => random.nextInt(256))
        .map((e) => e.toRadixString(16).padLeft(2, '0'))
        .join();
  }

  static String _generatePin() {
    final random = Random.secure();
    return (100000 + random.nextInt(900000)).toString(); // PIN de 6 dígitos
  }

  // ─── LOGIN ─────────────────────────────────────────────────────────────
  static Future<AuthResult> login(String email, String password) async {
    try {
      final user = await DatabaseService.getUserByEmail(email);
      if (user == null) {
        return AuthResult(exito: false, mensajeError: 'Usuario no encontrado');
      }

      final attemptHash = _hashPassword(password, user.salt);
      if (attemptHash == user.passwordHash) {
        final updatedUser = user.copyWith(ultimoLogin: DateTime.now());
        await DatabaseService.updateUser(updatedUser);
        
        // Guardar sesión local
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('logged_user_email', updatedUser.email);

        return AuthResult(exito: true, usuario: updatedUser);
      } else {
        return AuthResult(exito: false, mensajeError: 'Contraseña incorrecta');
      }
    } catch (e) {
      return AuthResult(exito: false, mensajeError: 'Error interno de Auth: $e');
    }
  }

  // ─── REGISTRO ──────────────────────────────────────────────────────────
  static Future<AuthResult> register(String nombre, String email, String password) async {
    try {
      final existingUser = await DatabaseService.getUserByEmail(email);
      if (existingUser != null) {
        return AuthResult(exito: false, mensajeError: 'El correo ya está registrado');
      }

      final salt = _generateSalt();
      final hash = _hashPassword(password, salt);

      final newUser = UserModel(
        nombre: nombre,
        email: email,
        passwordHash: hash,
        salt: salt,
        fechaRegistro: DateTime.now(),
        ultimoLogin: DateTime.now(),
      );

      await DatabaseService.insertUser(newUser);
      
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('logged_user_email', newUser.email);

      // Enviar correo de bienvenida (no bloqueante - en segundo plano)
      GmailService.sendWelcomeEmail(newUser).catchError((e) {
        print('No se pudo enviar correo de bienvenida: $e');
      });

      return AuthResult(exito: true, usuario: newUser);

    } catch (e) {
      return AuthResult(exito: false, mensajeError: 'Error al crear la cuenta: $e');
    }
  }

  // ─── GOOGLE SIGN IN (Mocked for Compilation) ─────────────────────────
  static Future<AuthResult> signInWithGoogle() async {
    try {
      // Simulación de OAuth (Reemplazar con _googleSignIn.signIn() cuando configure Client ID)
      await Future.delayed(const Duration(seconds: 1));
      
      final String mockEmail = 'admin@alertavecinal.com';
      final String mockName = 'Operador Google';
      final String mockId = 'google_id_12345';

      UserModel? user = await DatabaseService.getUserByEmail(mockEmail);
      
      if (user == null) {
        final salt = _generateSalt();
        final hash = _hashPassword(mockId, salt);

        user = UserModel(
          nombre: mockName,
          email: mockEmail,
          passwordHash: hash,
          salt: salt,
          fechaRegistro: DateTime.now(),
          ultimoLogin: DateTime.now(),
        );
        await DatabaseService.insertUser(user);
      } else {
        user = user.copyWith(ultimoLogin: DateTime.now());
        await DatabaseService.updateUser(user);
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('logged_user_email', user.email);

      return AuthResult(exito: true, usuario: user);
    } catch (error) {
      return AuthResult(
        exito: false, 
        mensajeError: 'Google Auth Error (Asegúrate de agregar el Client ID). Detalles: $error'
      );
    }
  }

  // ─── RECUPERACIÓN DE CONTRASEÑA (EMAIL REAL) ───────────────────────────
  static Future<AuthResult> requestPasswordReset(String email) async {
    try {
      final user = await DatabaseService.getUserByEmail(email);
      if (user == null) {
        return AuthResult(exito: false, mensajeError: 'Correo no registrado');
      }

      final pin = _generatePin();
      // Guardar hash del PIN
      final pinSalt = _generateSalt();
      final pinHash = _hashPassword(pin, pinSalt);
      
      // Guardamos la sal en el hash como "pinHash:salt"
      final payload = "$pinHash:$pinSalt";
      await DatabaseService.savePasswordResetPin(email, payload);

      final success = await GmailService.sendPasswordRecoveryEmail(user, pin);
      
      if (success) {
        return AuthResult(exito: true);
      } else {
        return AuthResult(exito: false, mensajeError: 'Error al enviar el correo. Verifica SMTP.');
      }
    } catch (e) {
      return AuthResult(exito: false, mensajeError: 'Error procesando la solicitud: $e');
    }
  }

  static Future<AuthResult> resetPasswordWithPin(String email, String pin, String newPassword) async {
    try {
      final data = await DatabaseService.getPasswordResetData(email);
      if (data == null) {
        return AuthResult(exito: false, mensajeError: 'No hay solicitud pendiente para este correo');
      }

      final expiresAt = DateTime.parse(data['expiresAt']);
      if (DateTime.now().isAfter(expiresAt)) {
        await DatabaseService.deletePasswordResetPin(email);
        return AuthResult(exito: false, mensajeError: 'El código de recuperación ha expirado');
      }

      final parts = data['pin'].toString().split(':');
      if (parts.length != 2) return AuthResult(exito: false, mensajeError: 'Datos de PIN corruptos');
      
      final savedHash = parts[0];
      final salt = parts[1];
      
      final attemptHash = _hashPassword(pin, salt);
      if (attemptHash != savedHash) {
        return AuthResult(exito: false, mensajeError: 'El PIN ingresado es incorrecto');
      }

      // PIN correcto, actualizar contraseña
      final user = await DatabaseService.getUserByEmail(email);
      if (user == null) return AuthResult(exito: false, mensajeError: 'Usuario no encontrado');

      final newSalt = _generateSalt();
      final newHash = _hashPassword(newPassword, newSalt);
      final updatedUser = user.copyWith(passwordHash: newHash, salt: newSalt);
      
      await DatabaseService.updateUser(updatedUser);
      await DatabaseService.deletePasswordResetPin(email);

      return AuthResult(exito: true, usuario: updatedUser);
    } catch (e) {
      return AuthResult(exito: false, mensajeError: 'Error al restablecer contraseña: $e');
    }
  }

  // ─── LOGOUT / SESIÓN ───────────────────────────────────────────────────
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('logged_user_email');
    // if (await _googleSignIn.isSignedIn()) {
    //   await _googleSignIn.signOut();
    // }
  }

  static Future<UserModel?> checkActiveSession() async {
    final prefs = await SharedPreferences.getInstance();
    final email = prefs.getString('logged_user_email');
    if (email != null) {
      return await DatabaseService.getUserByEmail(email);
    }
    return null;
  }
}
