import os
import sys
import anthropic
import requests


def main():
    api_key = os.environ["ANTHROPIC_API_KEY"]
    gh_token = os.environ["GH_TOKEN"]
    pr_number = os.environ["PR_NUMBER"]
    repo = os.environ["REPO"]

    with open("/tmp/pr_diff.txt") as f:
        diff = f.read()

    if not diff.strip():
        print("Diff vacío, nada que revisar.")
        return

    # Truncar si el diff es muy grande (limite de contexto)
    MAX_CHARS = 80_000
    truncated = len(diff) > MAX_CHARS
    if truncated:
        diff = diff[:MAX_CHARS] + "\n\n[... diff truncado por tamaño máximo ...]"

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Eres un experto en seguridad web especializado en Python/Flask. Revisa este diff de un Pull Request buscando vulnerabilidades de seguridad.

Busca específicamente:
- Inyección SQL (queries manuales con f-strings o concatenación de strings)
- XSS — outputs HTML sin escapar, uso de |safe en templates
- Secretos, API keys o contraseñas hardcodeadas en el código
- Fallos de autenticación o autorización (IDOR, bypass de login, falta de @login_required)
- Inputs de usuario no validados que lleguen a operaciones críticas (BD, filesystem, shell)
- CORS mal configurados (origins demasiado permisivos)
- Uso inseguro de eval(), exec() o subprocess con input externo
- Dependencias con vulnerabilidades conocidas añadidas en requirements.txt

Formato de respuesta:
- Si NO hay vulnerabilidades: empieza con "✅ **Sin vulnerabilidades detectadas**" y añade un comentario positivo breve sobre el código.
- Si HAY vulnerabilidades: lista cada una con:
  - **Severidad**: Alta / Media / Baja
  - **Ubicación**: archivo y línea aproximada
  - **Descripción**: qué está mal y por qué es un riesgo
  - **Corrección**: cómo arreglarlo con ejemplo de código si aplica

Diff del PR:
```diff
{diff}
```"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    review = message.content[0].text
    truncated_note = "\n> ⚠️ El diff fue truncado a 80.000 caracteres. Revisa manualmente los cambios adicionales.\n" if truncated else ""

    comment_body = f"""## 🔒 Security Review — Claude AI

{truncated_note}{review}

---
*Revisión automática generada por Claude ({message.model}). No sustituye una auditoría de seguridad manual en cambios críticos.*"""

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.post(url, json={"body": comment_body}, headers=headers)
    response.raise_for_status()
    print(f"Security review publicado: {response.json()['html_url']}")


if __name__ == "__main__":
    main()
