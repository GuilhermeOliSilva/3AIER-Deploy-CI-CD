"""A interface de terminal (`main`), simulando o teclado com monkeypatch."""

import pytest

import agent


@pytest.fixture
def teclado(monkeypatch):
    """Substitui `input()` por uma sequência de entradas (ou exceções)."""

    def _digitar(*entradas):
        fila = list(entradas)

        def fake_input(_prompt=""):
            item = fila.pop(0)
            if isinstance(item, BaseException) or (isinstance(item, type) and issubclass(item, BaseException)):
                raise item
            return item

        monkeypatch.setattr("builtins.input", fake_input)

    return _digitar


@pytest.fixture
def com_cliente(monkeypatch):
    monkeypatch.setattr(agent, "get_cliente", lambda: object())


def test_sem_chave_sai_com_codigo_1(capsys):
    with pytest.raises(SystemExit) as saida:
        agent.main()
    assert saida.value.code == 1
    assert "ERRO: OPENAI_API_KEY" in capsys.readouterr().out


@pytest.mark.parametrize("comando", ["/sair", "/quit", "/exit"])
def test_comandos_de_saida(comando, com_cliente, teclado, capsys):
    teclado(comando)
    agent.main()
    assert "Até mais." in capsys.readouterr().out


@pytest.mark.parametrize("excecao", [EOFError, KeyboardInterrupt])
def test_ctrl_d_e_ctrl_c_encerram_sem_traceback(excecao, com_cliente, teclado, capsys):
    teclado(excecao)
    agent.main()
    assert "Até mais." in capsys.readouterr().out


def test_entrada_vazia_e_ignorada(com_cliente, teclado, monkeypatch):
    chamadas = []
    monkeypatch.setattr(agent, "responder", lambda msgs, verboso=False: chamadas.append(1) or "x")
    teclado("", "   ", "/sair")

    agent.main()

    assert chamadas == []


def test_fluxo_normal_imprime_resposta(com_cliente, teclado, monkeypatch, capsys):
    historicos = []

    def fake_responder(mensagens, verboso=False):
        historicos.append(mensagens)
        assert verboso is True
        return "resposta do agente"

    monkeypatch.setattr(agent, "responder", fake_responder)
    teclado("  olá  ", "/sair")

    agent.main()

    assert "agente> resposta do agente" in capsys.readouterr().out
    mensagens = historicos[0]
    assert mensagens[0]["role"] == "system"
    assert mensagens[-1] == {"role": "user", "content": "olá"}  # entrada com strip


def test_erro_do_modelo_descarta_o_turno(com_cliente, teclado, monkeypatch, capsys):
    historicos = []

    def falha(mensagens, verboso=False):
        historicos.append(mensagens)
        raise RuntimeError("429 rate limit")

    monkeypatch.setattr(agent, "responder", falha)
    teclado("oi", "/sair")

    agent.main()

    assert "[erro ao chamar o modelo] 429 rate limit" in capsys.readouterr().out
    # a mensagem do usuário foi removida; sobra só o prompt de sistema
    assert [m["role"] for m in historicos[0]] == ["system"]
