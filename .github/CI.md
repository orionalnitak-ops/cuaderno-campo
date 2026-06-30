# CI/CD Pipeline

Este repositorio usa GitHub Actions para verificar cada Pull Request antes de mergear a `main`.

## Checks automáticos

- **Lint Python** — ruff verifica formato y convenciones
- **Security Scan (Bandit)** — análisis estático de seguridad en el código Python
- **Security Review (Claude)** — Claude AI revisa el diff buscando vulnerabilidades OWASP
