import 'package:flutter/material.dart';

class ErrorDetailScreen extends StatelessWidget {
  final Map<String, dynamic> errorData;

  const ErrorDetailScreen({super.key, required this.errorData});

  @override
  Widget build(BuildContext context) {
    final color = errorData["severity"] == "High"
        ? Colors.redAccent
        : Colors.orangeAccent;

    return Scaffold(
      appBar: AppBar(
        title: Text(errorData["code"]),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        iconTheme: const IconThemeData(color: Colors.black),
      ),
      backgroundColor: Colors.grey[100],
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title + Severity
            Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: color, size: 40),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    errorData["title"],
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                "Severity: ${errorData["severity"]}",
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Description
            Text(
              "Description",
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey[800],
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              errorData["description"],
              style: const TextStyle(fontSize: 15, color: Colors.black87),
            ),
            const SizedBox(height: 20),

            // AI-generated insight (mock)
            Text(
              "AI Insight",
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey[800],
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              errorData["aiInsight"] ??
                  "The system detected inefficient catalytic performance. This typically means the oxygen sensors or catalytic converter may be worn out. It’s recommended to inspect the O2 sensor first before replacing the converter.",
              style: const TextStyle(fontSize: 15, color: Colors.black87),
            ),
            const SizedBox(height: 20),

            // Suggested actions
            Text(
              "Recommended Actions",
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey[800],
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: List.generate(
                (errorData["actions"] ?? [
                  "Check oxygen sensors for damage or fouling.",
                  "Inspect catalytic converter efficiency.",
                  "Avoid long drives until issue is fixed.",
                  "Visit a certified garage for full diagnostics."
                ]).length,
                (i) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("• ",
                          style: TextStyle(fontSize: 16, height: 1.5)),
                      Expanded(
                        child: Text(
                          (errorData["actions"] ?? [
                            "Check oxygen sensors for damage or fouling.",
                            "Inspect catalytic converter efficiency.",
                            "Avoid long drives until issue is fixed.",
                            "Visit a certified garage for full diagnostics."
                          ])[i],
                          style: const TextStyle(fontSize: 15),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 40),

            // Footer
            Center(
              child: Text(
                "Last updated: Just now",
                style: TextStyle(color: Colors.grey[600], fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}