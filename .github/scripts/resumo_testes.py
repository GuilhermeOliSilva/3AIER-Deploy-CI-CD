"""
Gera um resumo em Markdown a partir dos relatórios do pytest.

No GitHub Actions, a saída vai para $GITHUB_STEP_SUMMARY e aparece na página
da execução. Localmente, é só impressa no terminal.

Uso:  python .github/scripts/resumo_testes.py reports/junit.xml [reports/coverage.xml]

Com vários junit.xml (um por suíte da pirâmide), gera uma tabela com uma
linha por suíte, usando o nome da pasta de cada arquivo:
      python .github/scripts/resumo_testes.py reports/*/junit.xml reports/coverage.xml
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def contar(raiz: ET.Element) -> dict:
    suites = [raiz] if raiz.tag == "testsuite" else list(raiz.iter("testsuite"))
    n = {campo: sum(int(s.get(campo, 0)) for s in suites) for campo in ("tests", "failures", "errors", "skipped")}
    n["time"] = sum(float(s.get("time", 0)) for s in suites)
    n["passed"] = n["tests"] - n["failures"] - n["errors"] - n["skipped"]
    return n


def linha_tabela(n: dict, rotulo: str = "") -> str:
    inicio = f"| {rotulo} " if rotulo else ""
    return (
        f"{inicio}| {n['tests']} | {n['passed']} | {n['failures']} | {n['errors']} "
        f"| {n['skipped']} | {n['time']:.2f}s |"
    )


def listar_problemas(raiz: ET.Element) -> list[str]:
    problemas = []
    for caso in raiz.iter("testcase"):
        for tipo in ("failure", "error"):
            no = caso.find(tipo)
            if no is not None:
                nome = f"{caso.get('classname', '')}::{caso.get('name', '')}"
                mensagem = (no.get("message") or "").strip().split("\n")[0][:200]
                mensagem = mensagem.replace("|", r"\|")  # não quebrar a tabela
                problemas.append(f"| `{nome}` | {tipo} | {mensagem} |")
    return problemas


def resumo_testes(junit: Path) -> list[str]:
    raiz = ET.parse(junit).getroot()
    n = contar(raiz)

    icone = "✅" if n["failures"] + n["errors"] == 0 else "❌"
    linhas = [
        f"## {icone} Testes",
        "",
        "| Total | ✅ Passaram | ❌ Falharam | 💥 Erros | ⏭️ Pulados | ⏱️ Tempo |",
        "|---:|---:|---:|---:|---:|---:|",
        linha_tabela(n),
        "",
    ]

    problemas = listar_problemas(raiz)
    if problemas:
        linhas += ["### Falhas", "", "| Teste | Tipo | Mensagem |", "|---|---|---|", *problemas, ""]
    return linhas


def resumo_piramide(junits: list[Path]) -> list[str]:
    """Uma linha por suíte (nome da pasta do junit.xml) e o total no fim."""
    linhas_suites, problemas = [], []
    total = {"tests": 0, "passed": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    for junit in sorted(junits):
        raiz = ET.parse(junit).getroot()
        n = contar(raiz)
        for campo in total:
            total[campo] += n[campo]
        icone = "✅" if n["failures"] + n["errors"] == 0 else "❌"
        linhas_suites.append(linha_tabela(n, f"{icone} `{junit.parent.name}`"))
        problemas += listar_problemas(raiz)

    icone = "✅" if total["failures"] + total["errors"] == 0 else "❌"
    linhas = [
        f"## {icone} Pirâmide de testes",
        "",
        "| Suíte | Total | ✅ Passaram | ❌ Falharam | 💥 Erros | ⏭️ Pulados | ⏱️ Tempo |",
        "|---|---:|---:|---:|---:|---:|---:|",
        *linhas_suites,
        linha_tabela(total, "**Total**"),
        "",
    ]
    if problemas:
        linhas += ["### Falhas", "", "| Teste | Tipo | Mensagem |", "|---|---|---|", *problemas, ""]
    return linhas


def resumo_cobertura(cobertura: Path) -> list[str]:
    raiz = ET.parse(cobertura).getroot()
    linhas = [
        f"## 📊 Cobertura: {float(raiz.get('line-rate', 0)) * 100:.1f}%",
        "",
        "| Arquivo | Linhas | Cobertura |",
        "|---|---:|---:|",
    ]
    for classe in raiz.iter("class"):
        n_linhas = len(classe.findall("lines/line"))
        taxa = float(classe.get("line-rate", 0)) * 100
        linhas.append(f"| `{classe.get('filename')}` | {n_linhas} | {taxa:.1f}% |")
    return linhas + [""]


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    arquivos = [Path(a) for a in sys.argv[1:]]
    cobertura = [a for a in arquivos if a.name.startswith("coverage")]
    junits = [a for a in arquivos if a not in cobertura]

    linhas = [f"⚠️ `{a}` não encontrado." for a in junits if not a.exists()]
    junits = [a for a in junits if a.exists()]
    if len(junits) == 1:
        linhas += resumo_testes(junits[0])
    elif junits:
        linhas += resumo_piramide(junits)
    for arquivo in cobertura:
        if arquivo.exists():
            linhas += resumo_cobertura(arquivo)
    linhas.append("📦 Relatórios completos (HTML) em **Artifacts**, no fim desta página.")

    texto = "\n".join(linhas) + "\n"
    destino = os.getenv("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as arquivo:
            arquivo.write(texto)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(texto)


if __name__ == "__main__":
    main()
