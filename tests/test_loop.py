"""O loop `responder()` — testado com um cliente falso, sem chamar a OpenAI."""

import json

import agent
from conftest import msg_ferramentas, msg_texto


def _conversa():
    return [
        {"role": "system", "content": "sistema"},
        {"role": "user", "content": "oi"},
    ]


def test_resposta_em_texto_direto(usar_fake):
    fake = usar_fake(msg_texto("Olá!"))
    mensagens = _conversa()

    assert agent.responder(mensagens) == "Olá!"
    assert len(fake.chamadas) == 1
    assert mensagens[-1] == {"role": "assistant", "content": "Olá!"}
    assert len(mensagens) == 3


def test_parametros_enviados_ao_modelo(usar_fake):
    fake = usar_fake(msg_texto("ok"))
    mensagens = _conversa()

    agent.responder(mensagens)

    chamada = fake.chamadas[0]
    assert chamada["model"] == agent.MODELO
    assert chamada["temperature"] == agent.TEMPERATURA
    assert chamada["tools"] is agent.FERRAMENTAS
    assert chamada["messages"] == _conversa()


def test_chama_ferramenta_e_depois_responde(usar_fake):
    fake = usar_fake(
        msg_ferramentas(("call_1", "somar", {"a": 1234, "b": 5678})),
        msg_texto("O resultado é 6912."),
    )
    mensagens = _conversa()

    resposta = agent.responder(mensagens)

    assert resposta == "O resultado é 6912."
    assert len(fake.chamadas) == 2

    pedido, resultado, final = mensagens[2:]
    assert pedido["role"] == "assistant"
    assert pedido["tool_calls"][0]["id"] == "call_1"
    assert resultado == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": json.dumps({"resultado": 6912}),
    }
    assert final == {"role": "assistant", "content": "O resultado é 6912."}

    # a segunda chamada ao modelo já leva o resultado da ferramenta
    assert fake.chamadas[1]["messages"][-1]["role"] == "tool"


def test_varias_ferramentas_na_mesma_resposta(usar_fake):
    usar_fake(
        msg_ferramentas(
            ("c1", "somar", {"a": 1, "b": 1}),
            ("c2", "somar", {"a": 2, "b": 2}),
            ("c3", "somar", {"a": 3, "b": 3}),
        ),
        msg_texto("feito"),
    )
    mensagens = _conversa()

    agent.responder(mensagens)

    respostas_tool = [m for m in mensagens if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in respostas_tool] == ["c1", "c2", "c3"]
    assert [json.loads(m["content"])["resultado"] for m in respostas_tool] == [2, 4, 6]


def test_argumentos_com_json_invalido_viram_erro_para_o_modelo(usar_fake):
    usar_fake(
        msg_ferramentas(("c1", "somar", "{isso não é json")),
        msg_texto("desculpe"),
    )
    mensagens = _conversa()

    assert agent.responder(mensagens) == "desculpe"

    resultado = next(m for m in mensagens if m["role"] == "tool")
    assert "erro" in json.loads(resultado["content"])


def test_ferramenta_inexistente_nao_derruba_o_loop(usar_fake):
    usar_fake(
        msg_ferramentas(("c1", "apagar_tudo", {})),
        msg_texto("não consegui"),
    )
    mensagens = _conversa()

    assert agent.responder(mensagens) == "não consegui"
    resultado = next(m for m in mensagens if m["role"] == "tool")
    assert "não existe" in json.loads(resultado["content"])["erro"]


def test_para_no_limite_de_iteracoes(usar_fake, monkeypatch):
    monkeypatch.setattr(agent, "MAX_ITERACOES", 3)
    fake = usar_fake(
        *[lambda: msg_ferramentas(("c", "somar", {"a": 1, "b": 1}))] * 3
    )

    resposta = agent.responder(_conversa())

    assert "limite de iterações" in resposta
    assert len(fake.chamadas) == 3


def test_conteudo_none_devolve_string_vazia(usar_fake):
    usar_fake(msg_texto(None))
    assert agent.responder(_conversa()) == ""


def test_verboso_imprime_a_chamada_de_ferramenta(usar_fake, capsys):
    usar_fake(
        msg_ferramentas(("c1", "somar", {"a": 2, "b": 3})),
        msg_texto("5"),
    )

    agent.responder(_conversa(), verboso=True)

    assert "[ferramenta] somar({'a': 2, 'b': 3})" in capsys.readouterr().out


def test_silencioso_por_padrao(usar_fake, capsys):
    usar_fake(
        msg_ferramentas(("c1", "somar", {"a": 2, "b": 3})),
        msg_texto("5"),
    )

    agent.responder(_conversa())

    assert capsys.readouterr().out == ""


def test_historico_preservado_entre_turnos(usar_fake):
    usar_fake(msg_texto("primeira"), msg_texto("segunda"))
    mensagens = _conversa()

    agent.responder(mensagens)
    mensagens.append({"role": "user", "content": "de novo"})
    agent.responder(mensagens)

    assert [m["role"] for m in mensagens] == ["system", "user", "assistant", "user", "assistant"]
