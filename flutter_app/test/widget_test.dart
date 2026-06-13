import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:vigilancia_bot_config/core/providers/app_provider.dart';
import 'package:vigilancia_bot_config/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppProvider(),
        child: const AlertaVecinalApp(),
      ),
    );
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
