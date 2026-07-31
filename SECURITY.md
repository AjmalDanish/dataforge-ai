# Security Policy for DataForge AI

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

```bash
EMAIL: security@dataforgeai.dev
```

Include:
- Description of the vulnerability
- Steps to reproduce
- Proof of exploit (if applicable)
- Affected versions

## Security Best Practices

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Keep dependencies updated
- Review third-party packages

## Dependency Security

We currently depend on:
- pandas: Data manipulation
- plotly: Visualization
- langgraph: Graph orchestration
- pydantic: Data validation
- openai/anthropic: LLM providers

All dependencies are from PyPI with verified maintainers.

## Vulnerability Disclosure Policy

We follow responsible disclosure:

1. Allow users time to update
- Coordinate security patches
- Maintain transparency about known issues
- Credit security reporters

## Supported Versions

Only latest version is supported.

We provide security updates for critical vulnerabilities.