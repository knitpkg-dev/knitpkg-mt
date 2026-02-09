# KnitPkg CLI Telemetry Policy
*Effective Date: February 9th, 2026*

This Telemetry Policy ("Policy") describes how the KnitPkg Command Line Interface ("KnitPkg CLI" or "CLI") collects, uses, and handles usage data ("Telemetry Data") to help us improve the KnitPkg CLI and the overall KnitPkg ecosystem. Your privacy is important to us, and we are committed to transparency regarding our data practices.

## 1. What is Telemetry Data?

Telemetry Data refers to usage information collected by the KnitPkg CLI and the KnitPkg Registry server. This data helps us understand how the CLI is used, identify common issues, and prioritize future development efforts to enhance your experience. While we strive to minimize the collection of personally identifiable information (PII), certain network identifiers are collected to ensure service integrity and provide meaningful analytics.

## 2. Data Collected

When a project is installed using the KnitPkg CLI, the following Telemetry Data is collected and sent to KnitPkg servers:

- `project_id`: A unique identifier for the installed project.
- `version`: The specific version of the project being installed.
- `user_agent`: The User-Agent string from the client's HTTP header, identifying the CLI version (e.g., "KnitPkg-CLI/1.0.0").
- `ip_address`: The IP address of the client making the request. This is determined by checking the X-Forwarded-For header (taking the leftmost IP if present), as it represents the original client or, if X-Forwarded-For is not available, by using the remote address of the incoming request.

Important Notes on Data Collection:

- **No Direct Personal Data**: We do not collect personal data such as your name, email address, or any other information that could directly identify you from your local environment.
- **Network Identifiers**: While ip_address and user_agent are collected, they are primarily used for aggregated analytics, security, and to understand the distribution of our user base. We do not attempt to link these identifiers back to individual users for profiling purposes.
- **No Code Inspection**: We do not inspect your code, extract project-level data (like project name, repository, or author from your local files), or access any sensitive data from your local environment beyond the project_id and version explicitly sent.
- **No Tracking in Libraries**: We do not add any tracking information into the libraries or packages produced by the KnitPkg CLI.
- **Crash Reporting**: In the event of a CLI crash, we may collect anonymous crash reports including stack traces. These reports are anonymized and filtered to include only CLI/SDK code paths to prevent unintentional disclosure of sensitive information from your local environment.

## 3. How We Use Telemetry Data

The Telemetry Data collected is used exclusively for the following purposes:

- **Product Improvement**: To understand usage patterns, identify frequently used features, and pinpoint areas for improvement in the KnitPkg CLI.
- **Troubleshooting**: To diagnose and resolve bugs, errors, and performance issues within the CLI.
- **Prioritization**: To inform our development roadmap and prioritize features that will have the greatest positive impact on our users.
- **Security & Stability**: To monitor the overall health and stability of the KnitPkg ecosystem, detect potential abuse, and analyze traffic patterns  
- **Geographic Analysis**: The ip_address may be used for aggregated, anonymized geographic analysis to understand the global distribution of KnitPkg CLI usage, without identifying individual user locations.

## 4. Data Retention

All Telemetry Data collected, including project_id, version, user_agent, and ip_address, is retained permanently. This allows us to perform long-term trend analysis, track improvements over time, and maintain historical records for security and analytical purposes. While ip_address can be considered personal data under certain regulations (like GDPR and LGPD), its permanent retention is justified by the need for long-term security monitoring and aggregated, non-identifiable usage statistics crucial for the continuous improvement and stability of the KnitPkg ecosystem. We implement measures to protect this data as outlined in Section 6.

## 5. Opting Out of Telemetry

Telemetry collection is enabled by default to help us continuously improve the KnitPkg CLI. You have the right to opt out of telemetry collection at any time.

To disable telemetry, you can use the following command:

```bash 
knitpkg config telemetry off 
```

To re-enable telemetry, use:

```bash 
knitpkg config telemetry on 
```

## 6. Data Security

We are committed to protecting the security of the Telemetry Data we collect. Data is sent securely to KnitPkg servers using industry-standard encryption protocols (e.g., HTTPS) and is stored in secure environments with restricted access. Access to raw telemetry data, especially ip_address, is strictly limited to authorized personnel for specific, approved purposes (e.g., security incident investigation, aggregated reporting).

## 7. Changes to This Policy

We may update this Telemetry Policy from time to time. We will notify you of any significant changes by posting the new Policy on our website and updating the "Effective Date" at the top of this document. Your continued use of the KnitPkg CLI after any changes signifies your acceptance of the updated Policy.

## 8. Contact Us

If you have any questions or concerns about this Telemetry Policy or our data practices, please contact us at contact@knitpkg.dev.