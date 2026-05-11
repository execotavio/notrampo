import json
import os
import sys

import requests

GITHUB_API_BASE_URL = "https://api.github.com"
ABACUS_API_URL = "https://routellm.abacus.ai/v1/chat/completions"


def get_required_env_var(var_name: str) -> str:
    """
    Obtém uma variável de ambiente obrigatória.

    Args:
        var_name (str): Nome da variável de ambiente.

    Returns:
        str: Valor da variável de ambiente.

    Raises:
        SystemExit: Se a variável não estiver definida.
    """
    value = os.getenv(var_name)
    if not value:
        print(f"Erro: variável de ambiente '{var_name}' não está definida.", file=sys.stderr)
        sys.exit(1)
    return value


def get_pr_diff(github_token: str, repo: str, pr_number: str) -> str:
    """
    Obtém o diff de um Pull Request do GitHub.

    Args:
        github_token (str): Token de autenticação do GitHub.
        repo (str): Repositório no formato 'owner/repo'.
        pr_number (str): Número do Pull Request.

    Returns:
        str: Conteúdo do diff.

    Raises:
        requests.exceptions.RequestException: Se a requisição HTTP falhar.
    """
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3.diff",
    }
    url = f"{GITHUB_API_BASE_URL}/repos/{repo}/pulls/{pr_number}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text


def review_with_llm(diff: str, abacus_api_key: str) -> str:
    """
    Envia o diff para a LLM e retorna o review gerado.

    Args:
        diff (str): Conteúdo do diff a ser revisado.
        abacus_api_key (str): Chave de API da Abacus AI.

    Returns:
        str: Review gerado pela LLM.

    Raises:
        requests.exceptions.RequestException: Se a requisição HTTP falhar.
    """
    truncate_warning = ""
    if len(diff) > 6000:
        diff = diff[:6000]
        truncate_warning = "\n\n(O diff foi truncado para os primeiros 6000 caracteres. O review pode não cobrir todas as mudanças.)"

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
{diff}
```{truncate_warning}"""

    headers = {
        "Authorization": f"Bearer {abacus_api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        ABACUS_API_URL,
        headers=headers,
        json={
            "model": "route-llm",
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    response.raise_for_status()

    try:
        choices = response.json().get("choices")
        if choices and len(choices) > 0:
            message = choices[0].get("message")
            if message:
                return message.get("content", "Nenhum conteúdo gerado pela LLM.")
        return "Nenhuma revisão válida encontrada na resposta da LLM."
    except json.JSONDecodeError:
        print(f"Erro ao decodificar JSON: {response.text}", file=sys.stderr)
        return "Erro ao processar a resposta da LLM: JSON inválido."
    except Exception as e:
        print(f"Erro inesperado: {e}\nResposta: {response.text}", file=sys.stderr)
        return f"Erro inesperado ao obter revisão: {e}"


def post_comment(github_token: str, repo: str, pr_number: str, body: str) -> None:
    """
    Posta um comentário em um Pull Request do GitHub.

    Args:
        github_token (str): Token de autenticação do GitHub.
        repo (str): Repositório no formato 'owner/repo'.
        pr_number (str): Número do Pull Request.
        body (str): Conteúdo do comentário.

    Raises:
        requests.exceptions.RequestException: Se a requisição HTTP falhar.
    """
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{GITHUB_API_BASE_URL}/repos/{repo}/issues/{pr_number}/comments"
    response = requests.post(url, headers=headers, json={"body": body})
    response.raise_for_status()
    print("Review postado com sucesso.")


if __name__ == "__main__":
    github_token = get_required_env_var("GITHUB_TOKEN")
    abacus_api_key = get_required_env_var("ABACUS_API_KEY")
    pr_number = get_required_env_var("PR_NUMBER")
    repo = get_required_env_var("REPO")

    diff = get_pr_diff(github_token, repo, pr_number)
    if not diff.strip():
        print("Nenhum diff encontrado.")
        sys.exit(0)

    review = review_with_llm(diff, abacus_api_key)
    post_comment(github_token, repo, pr_number, f"## 🤖 AI Code Review\n\n{review}")