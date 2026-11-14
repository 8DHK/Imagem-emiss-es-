#!/usr/bin/env python3
"""Importa a "Planilha de Fundos" da Portfel (ativos diligenciados) para arquivos estruturados.

Uso:  python3 importar_planilha_portfel.py caminho/Planilha.xlsx [pasta_saida]
Saída (padrão: ../dados_portfel/):
  meta.json                 título, arquivo, hash, data da importação (para detectar versão desatualizada)
  produtos.csv              todos os produtos autorizados, com colunas normalizadas
  limites_por_perfil.json   limites por classe e por grupo, para cada perfil
  carteiras_modelo.json     carteiras recomendadas por perfil
  regras_texto.json         linhas de regra ("➥ ...") de cada aba
  raw/<aba>.csv             cada aba, linha a linha, sem interpretação

Os dados gerados são internos da Portfel: ficam fora do git (.gitignore: dados_portfel/).
"""
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import warnings
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")
PERFIS = ["Conservador", "Moderado", "Equilibrado", "Arrojado", "Agressivo"]


def norm_classe(c):
    """Aproxima as classes dos produtos às classes dos limites por perfil."""
    c = re.sub(r"\s*\((EUA|Europa)\)", "", (c or "").strip()).strip()
    return {"Renda Fixa - Pré-fixado": "Renda Fixa - Pré-fixada"}.get(c, c)


def parse_max(txt):
    """'Máx. 5%' -> 0.05 | 0.04 -> 0.04 | 'Ilimitado' -> None | 'CONGELADO' -> 0.0 (veda aporte)."""
    if txt is None:
        return None, ""
    if isinstance(txt, (int, float)):
        return float(txt), str(txt)
    t = str(txt).strip()
    if t.upper() == "CONGELADO":
        return 0.0, t
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", t)
    if m:
        return float(m.group(1).replace(",", ".")) / 100, t
    return None, t


def cel(c):
    if c is None:
        return ""
    if isinstance(c, float):
        return f"{c:.6g}"
    return str(c).replace("\xa0", " ").strip()


def importar(xlsx, saida):
    xlsx, saida = Path(xlsx), Path(saida)
    (saida / "raw").mkdir(parents=True, exist_ok=True)
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    abas = {ws.title: [[cel(c) for c in row] for row in ws.iter_rows(values_only=True)] for ws in wb.worksheets}

    # --- cópia fiel de cada aba
    for nome, linhas in abas.items():
        with open(saida / "raw" / (re.sub(r"\W+", "_", nome) + ".csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            for i, l in enumerate(linhas, 1):
                if any(l):
                    w.writerow([i] + l)

    # --- regras em texto
    regras = {n: [c for l in ls for c in l if c.startswith("➥")] for n, ls in abas.items()}
    regras = {n: r for n, r in regras.items() if r}
    (saida / "regras_texto.json").write_text(json.dumps(regras, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- produtos autorizados
    ls = abas["Produtos Autorizados"]
    h = next(i for i, l in enumerate(ls) if l and l[0] == "CNPJ/Ticker")
    cab = ls[h]
    cols = ["cnpj_ticker", "isin_anbima", "nome", "classe", "arca", "risco", "alocacao_max_texto", "rating", "tipo",
            "estrategia", "taxas", "tributacao", "liquidacao", "investidor", "observacoes"]
    n_prod = 0
    with open(saida / "produtos.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols + ["classe_norm", "alocacao_max_pct", "congelado", "qualificado"])
        for l in ls[h + 1:]:
            if len(l) < 9 or not l[0] or l[0].startswith("➥"):
                continue
            l = (l + [""] * 15)[:15]
            mx, txt = parse_max(l[6])
            inv = l[13].replace("(a)", "").strip()
            w.writerow(l + [norm_classe(l[3]), "" if mx is None else mx, int(txt.upper() == "CONGELADO"), int(inv.startswith("Qualificado"))])
            n_prod += 1

    # --- limites por perfil (aba Composições)
    comp = abas["Composições"]
    limites = {}
    for r, linha in enumerate(comp):
        for c, v in enumerate(linha):
            if v in PERFIS and r + 1 < len(comp) and "Classe de Ativo" in comp[r + 1][c:c + 1]:
                classes, grupos, grupo_atual = {}, [], None
                for rr in range(r + 2, len(comp)):
                    ln = (comp[rr] + [""] * (c + 7))[c:c + 6]
                    if not ln[0]:
                        break
                    num = lambda x: float(x) if x not in ("", None) else None
                    classes[ln[0]] = {"min": num(ln[1]), "recomendado": num(ln[2]), "max": num(ln[3])}
                    if ln[4] != "" or ln[5] != "":
                        grupo_atual = {"classes": [], "min": num(ln[4]), "max": num(ln[5])}
                        grupos.append(grupo_atual)
                    if grupo_atual is not None:
                        grupo_atual["classes"].append(ln[0])
                limites[v] = {"classes": classes, "grupos": grupos}
    (saida / "limites_por_perfil.json").write_text(json.dumps(limites, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- carteiras-modelo (aba Composições, abaixo dos limites)
    modelos, i = {}, 0
    while i < len(comp):
        l = comp[i]
        if len(l) > 1 and l[1] == "CNPJ/Ticker" and i > 0:
            titulo = next((comp[j][1] for j in range(i - 1, -1, -1) if comp[j][1]), "?")
            itens = []
            for rr in range(i + 1, len(comp)):
                ln = (comp[rr] + [""] * 12)
                if not ln[2]:
                    break
                itens.append({"cnpj_ticker": ln[1], "produto": ln[2], "classe": ln[3], "pct_pl": float(ln[4] or 0),
                              "tipo": ln[6], "liquidez": ln[7], "taxa": ln[8], "rating": ln[9]})
            modelos[titulo] = itens
            i += len(itens)
        i += 1
    (saida / "carteiras_modelo.json").write_text(json.dumps(modelos, ensure_ascii=False, indent=1), encoding="utf-8")

    titulo = next((c for l in abas.get("Menu", []) for c in l if c), "")
    meta = {"titulo_planilha": titulo, "arquivo": xlsx.name, "sha256": hashlib.sha256(xlsx.read_bytes()).hexdigest(),
            "importado_em": dt.datetime.now().isoformat(timespec="seconds"), "n_produtos": n_prod,
            "perfis": list(limites), "n_carteiras_modelo": len(modelos), "abas": list(abas)}
    (saida / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    destino = sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "dados_portfel"
    m = importar(sys.argv[1], destino)
    print(f"{m['titulo_planilha']} | {m['n_produtos']} produtos | perfis: {', '.join(m['perfis'])} | {m['n_carteiras_modelo']} carteiras-modelo")
    print("gravado em:", destino)
