import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class AiAnalyzerScreen extends StatefulWidget {
  const AiAnalyzerScreen({Key? key}) : super(key: key);

  @override
  State<AiAnalyzerScreen> createState() => _AiAnalyzerScreenState();
}

class _AiAnalyzerScreenState extends State<AiAnalyzerScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = false;

  String? title;
  String? severity;
  String? description;
  List<String> causes = [];
  List<String> fixes = [];

  Future<void> analyzeCode() async {
    final errorCode = _controller.text.trim();
    if (errorCode.isEmpty) return;

    setState(() {
      _isLoading = true;
      title = null;
      severity = null;
      description = null;
      causes = [];
      fixes = [];
    });

    try {
      final baseUrl = Platform.isAndroid ? "http://10.0.2.2:8000" : "http://127.0.0.1:8000";
      final response = await http.post(
        Uri.parse("$baseUrl/analyze"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"code": errorCode}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        setState(() {
          title = data["title"] ?? "Unknown Code";
          severity = data["severity"] ?? "-";
          description = data["description"] ?? "No description available.";
          causes = List<String>.from(data["causes"] ?? []);
          fixes = List<String>.from(data["fixes"] ?? []);
        });
      } else {
        setState(() {
          title = "Error";
          description = "Failed to analyze code. Please try again.";
        });
      }
    } catch (e) {
      setState(() {
        title = "Error";
        description = "Connection failed: $e";
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("AI OBD Analyzer"),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            
            TextField(
              controller: _controller,
              decoration: InputDecoration(
                labelText: "Enter OBD Code (e.g. P0300)",
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 16),

            ElevatedButton(
              onPressed: _isLoading ? null : analyzeCode,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.black,
                foregroundColor: Colors.white,
                padding:
                    const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: _isLoading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                        color: Colors.white,
                        strokeWidth: 2,
                      ),
                    )
                  : const Text("Analyze Code",
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),

            const SizedBox(height: 20),

            Expanded(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: title == null
                    ? const Center(
                        child: Text(
                          "Enter a code and tap Analyze to get the AI report.",
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey, fontSize: 16),
                        ),
                      )
                    : SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title ?? "",
                              style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),

                            Text( 
                              "Severity: ${severity ?? ""}",
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),

                            Text(
                              description ?? "",
                              style: const TextStyle(
                                  fontSize: 16, height: 1.5, color: Colors.black87),
                            ),
                            const SizedBox(height: 16),

                            if (causes.isNotEmpty) ...[
                              const Text(
                                "Possible Causes:",
                                style: TextStyle(
                                    fontSize: 18, fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 6),
                              ...causes.map(
                                (c) => Padding(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 2),
                                  child: Text("• $c",
                                      style: const TextStyle(fontSize: 15)),
                                ),
                              ),
                              const SizedBox(height: 16),
                            ],

                            if (fixes.isNotEmpty) ...[
                              const Text(
                                "Suggested Fixes:",
                                style: TextStyle(
                                    fontSize: 18, fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 6),
                              ...fixes.map(
                                (f) => Padding(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 2),
                                  child: Text("• $f",
                                      style: const TextStyle(fontSize: 15)),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}