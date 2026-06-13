import 'dart:io';
import 'package:path/path.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../models/user_model.dart';
import 'encryption_helper.dart';

class DatabaseService {
  static Database? _db;

  static Future<void> initialize() async {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
  }

  static Future<Database> get database async {
    if (_db != null) return _db!;
    _db = await _initDB();
    return _db!;
  }

  static Future<Database> _initDB() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'alerta_vecinal_v2.db');

    return await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, version) async {
          await db.execute('''
            CREATE TABLE users(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              nombre TEXT,
              email TEXT UNIQUE,
              passwordHash TEXT,
              salt TEXT,
              telegramAlias TEXT,
              fechaRegistro TEXT,
              ultimoLogin TEXT,
              gmailHabilitado INTEGER,
              gmailEmail TEXT,
              gmailAppPassword TEXT,
              notifAlertas INTEGER,
              notifLogin INTEGER,
              notifActualizaciones INTEGER
            )
          ''');
          
          await db.execute('''
            CREATE TABLE alerts(
              id TEXT PRIMARY KEY,
              placa TEXT,
              tipo TEXT,
              color TEXT,
              marca TEXT,
              confianza REAL,
              timestamp TEXT,
              ubicacion TEXT,
              imagenUrl TEXT
            )
          ''');

          await db.execute('''
            CREATE TABLE password_resets(
              email TEXT PRIMARY KEY,
              pin TEXT,
              expiresAt TEXT
            )
          ''');
        },
      ),
    );
  }

  // ─── Usuarios ────────────────────────────────────────────────────────
  static Future<void> insertUser(UserModel user) async {
    final db = await database;
    
    // Encriptar campos sensibles antes de guardar
    final map = user.toMap();
    map['nombre'] = EncryptionHelper.encrypt(map['nombre']);
    map['email'] = EncryptionHelper.encrypt(map['email']);
    map['telegramAlias'] = map['telegramAlias'] != null ? EncryptionHelper.encrypt(map['telegramAlias']) : null;
    map['gmailEmail'] = map['gmailEmail'] != null ? EncryptionHelper.encrypt(map['gmailEmail']) : null;
    map['gmailAppPassword'] = map['gmailAppPassword'] != null ? EncryptionHelper.encrypt(map['gmailAppPassword']) : null;

    await db.insert('users', map, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  static Future<UserModel?> getUserByEmail(String plainEmail) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query('users');
    
    for (var map in maps) {
      final decEmail = EncryptionHelper.decrypt(map['email']);
      if (decEmail == plainEmail) {
        // Desencriptar los campos devueltos
        final decryptedMap = Map<String, dynamic>.from(map);
        decryptedMap['nombre'] = EncryptionHelper.decrypt(map['nombre']);
        decryptedMap['email'] = decEmail;
        if (map['telegramAlias'] != null) decryptedMap['telegramAlias'] = EncryptionHelper.decrypt(map['telegramAlias']);
        if (map['gmailEmail'] != null) decryptedMap['gmailEmail'] = EncryptionHelper.decrypt(map['gmailEmail']);
        if (map['gmailAppPassword'] != null) decryptedMap['gmailAppPassword'] = EncryptionHelper.decrypt(map['gmailAppPassword']);
        
        return UserModel.fromMap(decryptedMap);
      }
    }
    return null;
  }

  static Future<void> updateUser(UserModel user) async {
    await insertUser(user);
  }

  static Future<void> deleteUser(String plainEmail) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query('users');
    for (var map in maps) {
      final decEmail = EncryptionHelper.decrypt(map['email']);
      if (decEmail == plainEmail) {
        await db.delete('users', where: 'id = ?', whereArgs: [map['id']]);
        break;
      }
    }
  }

  // ─── Password Resets ──────────────────────────────────────────────────
  static Future<void> savePasswordResetPin(String email, String pinHash) async {
    final db = await database;
    await db.insert(
      'password_resets',
      {
        'email': email,
        'pin': pinHash,
        'expiresAt': DateTime.now().add(const Duration(minutes: 15)).toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<Map<String, dynamic>?> getPasswordResetData(String email) async {
    final db = await database;
    final res = await db.query('password_resets', where: 'email = ?', whereArgs: [email]);
    if (res.isNotEmpty) return res.first;
    return null;
  }

  static Future<void> deletePasswordResetPin(String email) async {
    final db = await database;
    await db.delete('password_resets', where: 'email = ?', whereArgs: [email]);
  }
}
