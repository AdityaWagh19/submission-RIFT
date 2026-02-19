# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.x     | :white_check_mark: |
| 3.x     | :x:                |
| 2.x     | :x:                |
| 1.x     | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **projectmanagerpbl2025@gmail.com**

You should receive a response within 48 hours. If the issue is confirmed, we will:
1. Release a patch as soon as possible
2. Credit you in the release notes (unless you prefer to remain anonymous)

## Security Best Practices for Users

When using this boilerplate:

1. **Never commit `.env` files** — they're gitignored, but double-check
2. **Use environment variables** for all sensitive data
3. **Rotate API keys** if you switch from AlgoNode to a private node
4. **Audit smart contracts** before deploying to MainNet
5. **Test on TestNet first** — always
6. **Keep dependencies updated** — run `pip install -U` and `npm update` regularly

## Known Security Considerations

- **Private keys never touch the backend** — all signing happens in Pera Wallet
- **No authentication layer** — this is a boilerplate; add auth for production
- **CORS is wide open by default** — restrict `CORS_ORIGINS` in production
- **TestNet only by default** — MainNet requires additional security review
