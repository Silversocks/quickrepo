import 'dart:async';
import 'package:flutter/material.dart';
import '../services/ecu_client.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final client = EcuClient(host: '127.0.0.1');
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _connectAndStartPolling();
  }

  void _connectAndStartPolling() async {
    await client.connect();
    print('✅ Connected to ECU');

    // Listen to updates from client
    client.onUpdate.listen((_) {
      setState(() {}); // rebuild UI with latest values
    });

    // Periodically request all PIDs
    _timer = Timer.periodic(const Duration(seconds: 1), (_) async {
      await client.requestAll();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text("Dashboard"),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildInfoCard(
              icon: Icons.thermostat,
              title: "Engine Temp",
              value: "${client.coolant.toStringAsFixed(1)}°C",
              color: client.coolant > 100 ? Colors.red : Colors.blueAccent,
            ),
            _buildInfoCard(
              icon: Icons.speed,
              title: "Speed",
              value: "${client.speed} km/h",
              color: Colors.deepPurpleAccent,
            ),
            _buildInfoCard(
              icon: Icons.data_usage,
              title: "RPM",
              value: client.rpm.toStringAsFixed(0),
              color: Colors.indigoAccent,
            ),
            _buildInfoCard(
              icon: Icons.air,
              title: "Throttle",
              value: "${client.throttle.toStringAsFixed(1)}%",
              color: Colors.orangeAccent,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard({
    required IconData icon,
    required String title,
    required String value,
    required Color color,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Icon(icon, color: color),
          const SizedBox(width: 16),
          Expanded(child: Text(title, style: const TextStyle(fontSize: 16))),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 17,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}