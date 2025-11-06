import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'error_detail_screen.dart';

class ErrorListScreen extends StatefulWidget {
  const ErrorListScreen({super.key});

  @override
  State<ErrorListScreen> createState() => _ErrorListScreenState();
}

class _ErrorListScreenState extends State<ErrorListScreen> {
  final List<Map<String, dynamic>> _errors = [];
  Timer? _pollTimer;

  // change this to your FastAPI backend IP
  final String backendBaseUrl = "http://127.0.0.1:8000";

  @override
  void initState() {
    super.initState();
    _startPollingECU();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _startPollingECU() {
    // poll ECU simulator every 3 seconds
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      final newCode = await _getLatestDtc();
      if (newCode != null && !_errors.any((e) => e["code"] == newCode)) {
        final analysis = await _analyzeCode(newCode);
        setState(() {
          _errors.insert(0, {
            "code": newCode,
            "title": analysis["title"],
            "severity": analysis["severity"],
            "description": analysis["description"],
            "aiInsight": analysis["description"], // optional field
            "actions": analysis["fixes"], // optional
          });
        });
      }
    });
  }

  Future<String?> _getLatestDtc() async {
    try {
      final response = await http.get(Uri.parse("$backendBaseUrl/latest_dtc"));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data["code"];
      }
    } catch (e) {
      debugPrint("Error fetching DTC: $e");
    }
    return null;
  }

  Future<Map<String, dynamic>> _analyzeCode(String code) async {
    try {
      final response = await http.post(
        Uri.parse("$backendBaseUrl/analyze"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"code": code}),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      debugPrint("Error analyzing code: $e");
    }
    return {
      "title": "Unknown Fault",
      "severity": "-",
      "description": "Could not analyze this code.",
      "fixes": []
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Active Errors"),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      backgroundColor: Colors.grey[100],
      body: _errors.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _errors.length,
              padding: const EdgeInsets.all(16),
              itemBuilder: (context, index) {
                final error = _errors[index];
                final color = error["severity"] == "High"
                    ? Colors.redAccent
                    : Colors.orangeAccent;
                return Card(
                  margin: const EdgeInsets.only(bottom: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: ListTile(
                    leading: Icon(Icons.warning_amber_rounded,
                        color: color, size: 32),
                    title: Text(
                      "${error['code']} - ${error['title']}",
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(error["description"]),
                    trailing: Icon(Icons.arrow_forward_ios_rounded,
                        size: 18, color: Colors.grey[600]),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => ErrorDetailScreen(errorData: error),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
    );
  }
}
