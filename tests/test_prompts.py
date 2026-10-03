"""Os arquivos de prompt (agent*.md) e a memória."""

import re

import pytest

import agent

PERFIS = sorted(agent.RAIZ.glob("agent*.md"))
SECOES_OBRIGATORIAS = ["## Identidade", "## Regras", "## Ferramentas disponíveis"]


def _ferramentas_citadas(texto):
    """Nomes na primeira coluna da tabela da seção 'Ferramentas disponíveis'."""
    secao = texto.split("## Ferramentas disponíveis", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^\|\s*`([^`]+)`\s*\|", secao, flags=re.MULTILINE)


def test_existem_perfis():
    nomes = {p.name for p in PERFIS}
    assert {"agent.md", "agent-ada.md", "agent-lint.md", "agent-val.md"} <= nomes


@pytest.mark.parametrize("perfil", PERFIS, ids=lambda p: p.name)
def test_perfil_tem_secoes_obrigatorias(perfil):
    texto = perfil.read_text(encoding="utf-8")
    assert texto.strip()
    for secao in SECOES_OBRIGATORIAS:
        assert secao in texto, f"{perfil.name} sem a seção '{secao}'"


@pytest.mark.parametrize("perfil", PERFIS, ids=lambda p: p.name)
def test_perfil_so_cita_ferramentas_que_existem(perfil):
    citadas = _ferramentas_citadas(perfil.read_text(encoding="utf-8"))
    assert citadas, f"{perfil.name} não lista nenhuma ferramenta"
    inexistentes = set(citadas) - set(agent.EXECUTORES)
    assert not inexistentes, f"{perfil.name} cita ferramentas que não existem: {inexistentes}"


def test_memory_md_existe_e_tem_titulo():
    texto = agent.MEMORY_MD.read_text(encoding="utf-8")
    assert texto.startswith("# Memória")
