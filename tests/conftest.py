"""
Fixtures compartilhadas.

O ponto central é o `FakeCliente`: ele imita o cliente da OpenAI e devolve
respostas roteirizadas. Assim o loop do agente é testado sem rede, sem chave
e sem custo — e de forma determinística.
"""

import json
from types import SimpleNamespace

import pytest
from openai.types.chat import ChatCompletionMessage

import agent


@pytest.fixture(autouse=True)
def isolar_ambiente(request, monkeypatch):
    """Cada teste começa sem chave e sem cliente em cache.

    O `load_dotenv()` roda no import do agent.py, então um .env local poderia
    vazar para os testes. Testes de integração mantêm a chave real.
    """
    monkeypatch.setattr(agent, "_cliente", None)
    if request.node.get_closest_marker("integration") is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def msg_texto(conteudo):
    """Resposta do modelo em texto puro."""
    return ChatCompletionMessage.model_validate({"role": "assistant", "content": conteudo})


def msg_ferramentas(*chamadas):
    """Resposta do modelo pedindo ferramentas. Cada chamada: (id, nome, argumentos).

    `argumentos` pode ser dict (vira JSON) ou str (usado como está — útil para
    simular JSON inválido).
    """
    tool_calls = [
        {
            "id": id_,
            "type": "function",
            "function": {
                "name": nome,
                "arguments": args if isinstance(args, str) else json.dumps(args),
            },
        }
        for id_, nome, args in chamadas
    ]
    return ChatCompletionMessage.model_validate(
        {"role": "assistant", "content": None, "tool_calls": tool_calls}
    )


class FakeCliente:
    """Imita `OpenAI().chat.completions.create` com uma fila de respostas."""

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.chamadas = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        # cópia da lista: `responder` muta `messages` depois da chamada
        self.chamadas.append({**kwargs, "messages": list(kwargs["messages"])})
        if not self._respostas:
            raise AssertionError("FakeCliente: o agente pediu mais respostas que o roteiro")
        resposta = self._respostas.pop(0)
        if callable(resposta):
            resposta = resposta()
        return SimpleNamespace(choices=[SimpleNamespace(message=resposta)])


@pytest.fixture
def usar_fake(monkeypatch):
    """Instala um FakeCliente com o roteiro dado e o devolve."""

    def _instalar(*respostas):
        fake = FakeCliente(respostas)
        monkeypatch.setattr(agent, "get_cliente", lambda: fake)
        return fake

    return _instalar
