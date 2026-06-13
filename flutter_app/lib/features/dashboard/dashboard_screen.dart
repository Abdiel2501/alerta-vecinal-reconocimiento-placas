import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/providers/app_provider.dart';
import '../../widgets/sidebar_nav.dart';
import 'home_tab.dart';
import 'alerts_tab.dart';
import 'cameras_tab.dart';
import 'recordings_tab.dart';
import 'settings_tab.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final List<Widget> _tabs = const [
    HomeTab(),
    CamerasTab(),
    AlertsTab(),
    RecordingsTab(),
    SettingsTab(),
  ];

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();

    return Scaffold(
      body: Row(
        children: [
          SidebarNav(
            indexActual: provider.tabActual,
            alSeleccionar: provider.setTabActual,
            nombreUsuario: provider.usuario?.nombre ?? 'Operador Anónimo',
          ),
          Expanded(
            child: Container(
              color: Theme.of(context).colorScheme.surface,
              child: IndexedStack(
                index: provider.tabActual,
                children: _tabs,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
