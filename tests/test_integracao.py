"""Teste contra a API real da OpenAI.

Custa dinheiro e não é determinístico, por isso só roda quando há uma
OPENAI_API_KEY no ambiente e é pedido explicitamente. Sem a chave, é
pulado. Fora do `pytest` padrão; para rodar:  pytest -m integration
"""

import os

import pytest

import agent

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="sem OPENAI_API_KEY"),
]


def test_agente_usa_a_ferramenta_somar():
    mensagens = [
        {"role": "system", "content": agent.carregar_contexto()},
        {"role": "user", "content": "quanto é 1234 mais 5678?"},
    ]

    resposta = agent.responder(mensagens)

    chamadas = [m for m in mensagens if m.get("role") == "tool"]
    assert chamadas, "o modelo não chamou nenhuma ferramenta"
    assert "6912" in resposta.replace(".", "").replace(",", "")
