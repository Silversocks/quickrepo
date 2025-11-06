import 'package:flutter/material.dart';
//import 'screens/dashboard_screen.dart';
//import 'screens/error_list_screen.dart';
//import 'screens/profile_screen.dart';
import 'widgets/bottom_nav.dart';

void main() {
  runApp(const AutopulseApp());
}

class AutopulseApp extends StatelessWidget {
  const AutopulseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AutoPulse',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        scaffoldBackgroundColor: Colors.grey[100],
        fontFamily: 'Poppins',
      ),
      home: const BottomNav(),
    );
  }
}