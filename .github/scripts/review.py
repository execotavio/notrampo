import os
import requests

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ABACUS_API_KEY = os.environ["ABACUS_API_KEY"]
PR_NUMBER = os.environ["PR_NUMBER"]
REPO = os.environ["REPO"]

GITHUB_API = "https://api.github.com"
ABACUS_API = "https://routellm.abacus.ai/v1/chat/completions"

headers_gh = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_pr_diff():
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{PR_NUMBER}"
    headers = {**headers_gh, "Accept": "application/vnd.github.v3.diff"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text


def review_with_llm(diff: str) -> str:
    prompt = f"""Você é um professor de programação revisando o código de um aluno iniciante/intermediário em Python.

Analise o diff abaixo e para cada problema encontrado:
1. Explique O QUE está errado
2. Explique POR QUE está errado
3. Mostre COMO corrigir com exemplo de código

Cubra aspectos como:
- Nomes de variáveis e funções (clareza, convenções Python)
- Responsabilidade única
- Type hints
- Docstrings
- Tratamento de erros
- Lógica e bugs

Se algo estiver bem feito, mencione também.
Seja didático, não apenas aponte o erro.

```diff
{diff[:6000]}
```"""

    response = requests.post(
        ABACUS_API,
        headers={
            "Authorization": f"Bearer {ABACUS_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "route-llm",
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def post_comment(body: str):
    url = f"{GITHUB_API}/repos/{REPO}/issues/{PR_NUMBER}/comments"
    response = requests.post(url, headers=headers_gh, json={"body": body})
    response.raise_for_status()
    print("Review postado com sucesso.")


if __name__ == "__main__":
    diff = get_pr_diff()
    if not diff.strip():
        print("Nenhum diff encontrado.")
        exit(0)

    review = review_with_llm(diff)
    post_comment(f"## 🤖 AI Code Review\n\n{review}")