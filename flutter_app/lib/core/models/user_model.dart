class UserModel {
  final int? id;
  final String nombre;
  final String email;
  final String passwordHash;
  final String salt;
  final String? telegramAlias;
  final DateTime fechaRegistro;
  final DateTime? ultimoLogin;
  final bool gmailHabilitado;
  final String? gmailEmail;
  final String? gmailAppPassword;
  final bool notifAlertas;
  final bool notifLogin;
  final bool notifActualizaciones;

  UserModel({
    this.id,
    required this.nombre,
    required this.email,
    required this.passwordHash,
    required this.salt,
    this.telegramAlias,
    required this.fechaRegistro,
    this.ultimoLogin,
    this.gmailHabilitado = false,
    this.gmailEmail,
    this.gmailAppPassword,
    this.notifAlertas = true,
    this.notifLogin = true,
    this.notifActualizaciones = true,
  });

  UserModel copyWith({
    int? id,
    String? nombre,
    String? email,
    String? passwordHash,
    String? salt,
    String? telegramAlias,
    DateTime? fechaRegistro,
    DateTime? ultimoLogin,
    bool? gmailHabilitado,
    String? gmailEmail,
    String? gmailAppPassword,
    bool? notifAlertas,
    bool? notifLogin,
    bool? notifActualizaciones,
  }) {
    return UserModel(
      id: id ?? this.id,
      nombre: nombre ?? this.nombre,
      email: email ?? this.email,
      passwordHash: passwordHash ?? this.passwordHash,
      salt: salt ?? this.salt,
      telegramAlias: telegramAlias ?? this.telegramAlias,
      fechaRegistro: fechaRegistro ?? this.fechaRegistro,
      ultimoLogin: ultimoLogin ?? this.ultimoLogin,
      gmailHabilitado: gmailHabilitado ?? this.gmailHabilitado,
      gmailEmail: gmailEmail ?? this.gmailEmail,
      gmailAppPassword: gmailAppPassword ?? this.gmailAppPassword,
      notifAlertas: notifAlertas ?? this.notifAlertas,
      notifLogin: notifLogin ?? this.notifLogin,
      notifActualizaciones: notifActualizaciones ?? this.notifActualizaciones,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'nombre': nombre,
      'email': email,
      'passwordHash': passwordHash,
      'salt': salt,
      'telegramAlias': telegramAlias,
      'fechaRegistro': fechaRegistro.toIso8601String(),
      'ultimoLogin': ultimoLogin?.toIso8601String(),
      'gmailHabilitado': gmailHabilitado ? 1 : 0,
      'gmailEmail': gmailEmail,
      'gmailAppPassword': gmailAppPassword,
      'notifAlertas': notifAlertas ? 1 : 0,
      'notifLogin': notifLogin ? 1 : 0,
      'notifActualizaciones': notifActualizaciones ? 1 : 0,
    };
  }

  factory UserModel.fromMap(Map<String, dynamic> map) {
    return UserModel(
      id: map['id'],
      nombre: map['nombre'],
      email: map['email'],
      passwordHash: map['passwordHash'],
      salt: map['salt'],
      telegramAlias: map['telegramAlias'],
      fechaRegistro: DateTime.parse(map['fechaRegistro']),
      ultimoLogin: map['ultimoLogin'] != null ? DateTime.parse(map['ultimoLogin']) : null,
      gmailHabilitado: map['gmailHabilitado'] == 1,
      gmailEmail: map['gmailEmail'],
      gmailAppPassword: map['gmailAppPassword'],
      notifAlertas: map['notifAlertas'] == 1,
      notifLogin: map['notifLogin'] == 1,
      notifActualizaciones: map['notifActualizaciones'] == 1,
    );
  }
}
