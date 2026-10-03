"""Contexto (agent.md + memory.md) e configuração do cliente."""

import pytest
from openai import OpenAI

import agent


@pytest.fixture
def arquivos(tmp_path, monkeypatch):
    """Aponta AGENT_MD e MEMORY_MD para arquivos temporários (ainda não criados)."""
    agent_md = tmp_path / "agent.md"
    memory_md = tmp_path / "memory.md"
    monkeypatch.setattr(agent, "AGENT_MD", agent_md)
    monkeypatch.setattr(agent, "MEMORY_MD", memory_md)
    return agent_md, memory_md


# --------------------------------------------------------------------------
# carregar_contexto
# --------------------------------------------------------------------------


def test_contexto_junta_identidade_e_memoria(arquivos):
    agent_md, memory_md = arquivos
    agent_md.write_text("Você é a Ada.", encoding="utf-8")
    memory_md.write_text("- Nome: Ana.", encoding="utf-8")

    contexto = agent.carregar_contexto()

    assert contexto.startswith("Você é a Ada.")
    assert "# Memória" in contexto
    assert contexto.endswith("- Nome: Ana.")
    assert contexto.index("Você é a Ada.") < contexto.index("# Memória") < contexto.index("- Nome: Ana.")


def test_contexto_sem_agent_md_usa_padrao(arquivos):
    _, memory_md = arquivos
    memory_md.write_text("algo", encoding="utf-8")

    assert agent.carregar_contexto().startswith("Você é um assistente.")


def test_contexto_sem_memory_md_nao_quebra(arquivos):
    agent_md, _ = arquivos
    agent_md.write_text("Identidade", encoding="utf-8")

    contexto = agent.carregar_contexto()

    assert contexto.startswith("Identidade")
    assert contexto.rstrip().endswith("# Memória")


def test_contexto_sem_nenhum_arquivo(arquivos):
    contexto = agent.carregar_contexto()
    assert "Você é um assistente." in contexto
    assert "# Memória" in contexto


def test_contexto_le_utf8(arquivos):
    agent_md, memory_md = arquivos
    agent_md.write_text("Atenção: ação, coração, pé 🤖", encoding="utf-8")
    memory_md.write_text("Preferência: respostas em português", encoding="utf-8")

    contexto = agent.carregar_contexto()

    assert "Atenção: ação, coração, pé 🤖" in contexto
    assert "Preferência: respostas em português" in contexto


def test_contexto_real_do_repositorio_carrega():
    """Os arquivos versionados no repositório precisam ser lidos sem erro."""
    contexto = agent.carregar_contexto()
    assert "## Identidade" in contexto
    assert "# Memória" in contexto


# --------------------------------------------------------------------------
# get_cliente
# --------------------------------------------------------------------------


def test_get_cliente_sem_chave_falha_com_mensagem_clara():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY não encontrada"):
        agent.get_cliente()


def test_get_cliente_com_chave_vazia_falha(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError):
        agent.get_cliente()


def test_get_cliente_com_chave_devolve_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    cliente = agent.get_cliente()
    assert isinstance(cliente, OpenAI)
    assert cliente.api_key == "sk-teste"


def test_get_cliente_e_instanciado_uma_vez_so(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    assert agent.get_cliente() is agent.get_cliente()
