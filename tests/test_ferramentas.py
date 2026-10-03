"""Ferramentas: a função `somar`, o despachante e o contrato declaração x código."""

import inspect
import json

import pytest

import agent


# --------------------------------------------------------------------------
# somar
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a, b, esperado",
    [
        (1, 2, 3),
        (1234, 5678, 6912),
        (-5, 3, -2),
        (0, 0, 0),
        (2.5, 0.25, 2.75),
    ],
)
def test_somar(a, b, esperado):
    assert agent.somar(a, b) == {"resultado": esperado}


def test_somar_decimais_com_tolerancia():
    assert agent.somar(0.1, 0.2)["resultado"] == pytest.approx(0.3)


# --------------------------------------------------------------------------
# executar_ferramenta
# --------------------------------------------------------------------------


def test_executar_ferramenta_existente():
    saida = agent.executar_ferramenta("somar", {"a": 2, "b": 3})
    assert isinstance(saida, str)
    assert json.loads(saida) == {"resultado": 5}


def test_executar_ferramenta_inexistente_vira_erro():
    saida = json.loads(agent.executar_ferramenta("dividir", {"a": 1, "b": 2}))
    assert saida == {"erro": "Ferramenta 'dividir' não existe."}


@pytest.mark.parametrize(
    "argumentos",
    [
        {"a": 1},  # faltando argumento
        {"a": 1, "b": 2, "c": 3},  # argumento extra
        {},  # nenhum argumento
        {"a": "1", "b": 2},  # tipo errado (str + int)
    ],
)
def test_executar_ferramenta_com_argumentos_invalidos_nao_quebra(argumentos):
    saida = agent.executar_ferramenta("somar", argumentos)
    dados = json.loads(saida)
    assert "erro" in dados
    assert dados["erro"].startswith("Falha em 'somar':")


def test_executar_ferramenta_preserva_acentos():
    saida = agent.executar_ferramenta("inexistente", {})
    assert "não" in saida  # ensure_ascii=False
    assert "\\u00e3" not in saida


# --------------------------------------------------------------------------
# Contrato: FERRAMENTAS (o que o modelo lê) x EXECUTORES (o que roda)
# --------------------------------------------------------------------------


def _declaracoes():
    return {f["function"]["name"]: f["function"] for f in agent.FERRAMENTAS}


def test_toda_ferramenta_declarada_tem_executor_e_vice_versa():
    assert set(_declaracoes()) == set(agent.EXECUTORES)


@pytest.mark.parametrize("nome", sorted(agent.EXECUTORES))
def test_parametros_declarados_batem_com_a_funcao(nome):
    declaracao = _declaracoes()[nome]
    assinatura = inspect.signature(agent.EXECUTORES[nome]).parameters

    propriedades = set(declaracao["parameters"]["properties"])
    obrigatorios = set(declaracao["parameters"].get("required", []))
    sem_default = {p for p, v in assinatura.items() if v.default is inspect.Parameter.empty}

    assert propriedades == set(assinatura), "properties diferente dos parâmetros da função"
    assert obrigatorios == sem_default, "required diferente dos parâmetros sem default"


@pytest.mark.parametrize("nome", sorted(agent.EXECUTORES))
def test_ferramenta_tem_descricao_util(nome):
    declaracao = _declaracoes()[nome]
    # descrição vaga = ferramenta ignorada pelo modelo (ver README)
    assert len(declaracao.get("description", "").split()) >= 4
    for prop, schema in declaracao["parameters"]["properties"].items():
        assert schema.get("description"), f"parâmetro '{prop}' sem description"
