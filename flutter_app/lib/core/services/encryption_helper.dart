import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:pointycastle/export.dart';

class EncryptionHelper {
  // Clave maestra (en producción debe estar oculta o derivarse con PBKDF2)
  static final Uint8List _key = _generateKey('AlertaVecinalSecureKey_2026_AES256!');

  static Uint8List _generateKey(String seed) {
    final keyBytes = utf8.encode(seed);
    final hash = SHA256Digest().process(Uint8List.fromList(keyBytes));
    return hash;
  }

  static String encrypt(String plainText) {
    try {
      final plainBytes = utf8.encode(plainText);
      final cipher = GCMBlockCipher(AESEngine());
      final iv = _generateRandomBytes(12);
      
      final parameters = AEADParameters(
        KeyParameter(_key),
        128, // MAC size in bits
        iv,
        Uint8List(0), // Additional Authenticated Data
      );
      
      cipher.init(true, parameters);
      final cipherText = cipher.process(Uint8List.fromList(plainBytes));
      
      // Combine IV + CipherText and encode to Base64
      final result = Uint8List(iv.length + cipherText.length);
      result.setAll(0, iv);
      result.setAll(iv.length, cipherText);
      
      return base64Encode(result);
    } catch (e) {
      return plainText; // Fallback, shouldn't happen
    }
  }

  static String decrypt(String encryptedBase64) {
    try {
      final encryptedBytes = base64Decode(encryptedBase64);
      final iv = encryptedBytes.sublist(0, 12);
      final cipherText = encryptedBytes.sublist(12);
      
      final cipher = GCMBlockCipher(AESEngine());
      final parameters = AEADParameters(
        KeyParameter(_key),
        128,
        iv,
        Uint8List(0),
      );
      
      cipher.init(false, parameters);
      final plainBytes = cipher.process(cipherText);
      return utf8.decode(plainBytes);
    } catch (e) {
      return encryptedBase64;
    }
  }

  static Uint8List _generateRandomBytes(int length) {
    final random = Random.secure();
    return Uint8List.fromList(List<int>.generate(length, (i) => random.nextInt(256)));
  }
}
