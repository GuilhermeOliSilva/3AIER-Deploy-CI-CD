"""
Gera um resumo em Markdown a partir dos relatórios do pytest.

No GitHub Actions, a saída vai para $GITHUB_STEP_SUMMARY e aparece na página
da execução. Localmente, é só impressa no terminal.

Uso:  python .github/scripts/resumo_testes.py reports/junit.xml [reports/coverage.xml]
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def resumo_testes(junit: Path) -> list[str]:
    raiz = ET.parse(junit).getroot()
    suites = [raiz] if raiz.tag == "testsuite" else list(raiz.iter("testsuite"))

    total = sum(int(s.get("tests", 0)) for s in suites)
    falhas = sum(int(s.get("failures", 0)) for s in suites)
    erros = sum(int(s.get("errors", 0)) for s in suites)
    pulados = sum(int(s.get("skipped", 0)) for s in suites)
    tempo = sum(float(s.get("time", 0)) for s in suites)
    passaram = total - falhas - erros - pulados

    icone = "✅" if falhas + erros == 0 else "❌"
    linhas = [
        f"## {icone} Testes",
        "",
        "| Total | ✅ Passaram | ❌ Falharam | 💥 Erros | ⏭️ Pulados | ⏱️ Tempo |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {total} | {passaram} | {falhas} | {erros} | {pulados} | {tempo:.2f}s |",
        "",
    ]

    problemas = []
    for caso in raiz.iter("testcase"):
        for tipo in ("failure", "error"):
            no = caso.find(tipo)
            if no is not None:
                nome = f"{caso.get('classname', '')}::{caso.get('name', '')}"
                mensagem = (no.get("message") or "").strip().split("\n")[0][:200]
                mensagem = mensagem.replace("|", r"\|")  # não quebrar a tabela
                problemas.append(f"| `{nome}` | {tipo} | {mensagem} |")

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

    junit = Path(sys.argv[1])
    linhas = resumo_testes(junit) if junit.exists() else [f"⚠️ `{junit}` não encontrado.", ""]
    if len(sys.argv) > 2 and Path(sys.argv[2]).exists():
        linhas += resumo_cobertura(Path(sys.argv[2]))
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
