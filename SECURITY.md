# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in AGent, please report it responsibly.

### How to Report

1. **Do not** open a public issue
2. Email the maintainer with details
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- Acknowledgment within 48 hours
- Investigation within 7 days
- Fix or mitigation plan within 30 days
- Credit in the release notes (unless you prefer to remain anonymous)

## Security Considerations

- **APK Analysis**: This tool analyzes potentially malicious APKs. Always run in a sandboxed environment.
- **Token Security**: Never commit API tokens or credentials to the repository.
- **File System**: The agent writes files next to input APKs. Ensure you have proper backups.
- **Network**: The crawl script fetches URLs. Be cautious when crawling untrusted sources.
