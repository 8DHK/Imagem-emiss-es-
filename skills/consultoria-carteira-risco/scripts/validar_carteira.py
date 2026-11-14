#!/usr/bin/env python3
"""Valida uma carteira contra as regras da planilha de ativos diligenciados da Portfel.

Uso:
  python3 validar_carteira.py --perfil Moderado --investidor Geral carteira.csv
  python3 validar_carteira.py --modelo "Moderado" --perfil Moderado          # testa uma carteira-modelo da planilha
carteira.csv: colunas  produto  (nome, CNPJ ou ticker),  peso  (0,05 | 5% | 5),  [classe]  (obrigatória p/ itens genéricos)
Antes de usar, importe a planilha:  python3 importar_planilha_portfel.py Planilha.xlsx

ERRO = viola regra da planilha; AVISO = exige conferência do consultor; INFO = resumo.
Cobre: limites por classe e grupo do perfil; produto fora da lista, congelado ou só para qualificado; teto por produto
("Alocação Máx."); FIDC (vetado para conservador, 2,5%); gestão ativa (5% por fundo; 10% por gestora, só por aproximação);
rating C; soma de pesos. Não cobre: faixas S1-S5 por banco, Carteiras Finclass em conjunto e liquidez mínima do cliente.
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

TOL = 1e-6
FIDC_TETO = 0.025          # "Máximo em cada FIDC ou Private Equity: 2,5%"
ATIVA_TETO = 0.05          # "Máximo em cada fundo de GESTÃO ATIVA: 5%"
GESTORA_TETO = 0.10        # "Máximo em cada GESTORA via GESTÃO ATIVA: 10%"
REGRAS_ESPERADAS = ["FIDC", "GESTÃO ATIVA", "GESTORA"]


def chave(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def peso_fmt(x):
    return f"{x * 100:.2f}%".replace(".", ",")


def parse_peso(v):
    v = str(v).strip().replace("%", "").replace(",", ".")
    return float(v)


def norm_classe(c):
    c = re.sub(r"\s*\((EUA|Europa)\)", "", (c or "").strip()).strip()
    return {"Renda Fixa - Pré-fixado": "Renda Fixa - Pré-fixada"}.get(c, c)


def carregar_dados(pasta):
    pasta = Path(pasta)
    if not (pasta / "produtos.csv").exists():
        sys.exit(f"dados não encontrados em {pasta}: rode importar_planilha_portfel.py primeiro")
    with open(pasta / "produtos.csv", encoding="utf-8-sig", newline="") as f:
        produtos = list(csv.DictReader(f))
    limites = json.loads((pasta / "limites_por_perfil.json").read_text(encoding="utf-8"))
    modelos = json.loads((pasta / "carteiras_modelo.json").read_text(encoding="utf-8"))
    regras = json.loads((pasta / "regras_texto.json").read_text(encoding="utf-8"))
    meta = json.loads((pasta / "meta.json").read_text(encoding="utf-8"))
    return produtos, limites, modelos, regras, meta


def achar_produto(termo, produtos):
    k = chave(termo)
    por_id = [p for p in produtos if chave(p["cnpj_ticker"]) == k]
    if len(por_id) == 1:
        return por_id[0], None
    exatos = [p for p in produtos if chave(p["nome"]) == k]
    if len(exatos) == 1:
        return exatos[0], None
    cand = por_id or exatos or [p for p in produtos if k and k in chave(p["nome"])]
    if not cand:
        return None, "não consta na lista de produtos autorizados"
    if len(cand) == 1:
        return cand[0], None
    return None, "ambíguo: " + "; ".join(p["nome"] for p in cand[:6])


def generico(termo, tipo=""):
    t = chave(termo)
    return t.startswith("soberano") or "checartabela" in t or chave(tipo).startswith(("bancario", "tesouro"))


def validar(itens, perfil, investidor, dados):
    produtos, limites, _, regras, meta = dados
    res = []                                    # (nivel, mensagem)
    add = lambda n, m: res.append((n, m))
    if perfil not in limites:
        sys.exit(f"perfil '{perfil}' inexistente. Opções: {', '.join(limites)}")
    for r in REGRAS_ESPERADAS:
        if not any(r in x.upper() for lista in regras.values() for x in lista):
            add("AVISO", f"regra sobre '{r}' não encontrada nas regras da planilha importada: confira a versão")

    por_classe, por_gestora, risco = defaultdict(float), defaultdict(float), defaultdict(float)
    total = sum(i["peso"] for i in itens)
    if abs(total - 1) > 0.005:
        add("ERRO" if total > 1.005 else "AVISO", f"pesos somam {peso_fmt(total)} (esperado 100%)")

    for it in itens:
        p, erro = (None, None) if it.get("generico") else achar_produto(it["produto"], produtos)
        nome, w = it["produto"], it["peso"]
        if it.get("generico") or generico(nome, it.get("tipo", "")):
            classe = norm_classe(it.get("classe", ""))
            if not classe:
                add("ERRO", f"'{nome}': item genérico sem 'classe' informada")
            por_classe[classe] += w
            if chave(nome).startswith("soberano") or chave(it.get("tipo", "")).startswith("bancario"):
                add("AVISO", f"'{nome}' ({peso_fmt(w)}): conferir emissores na aba Ranking BC (S1 ilimitado; S2 até 20% do PL; S3 limite do FGC no vencimento)")
            continue
        if p is None:
            add("ERRO", f"'{nome}': {erro}")
            if it.get("classe"):                      # a classe informada ainda conta nos limites do perfil
                por_classe[norm_classe(it["classe"])] += w
            continue
        classe = norm_classe(it.get("classe") or p["classe_norm"])
        por_classe[classe] += w
        risco[p["risco"]] += w
        if p["congelado"] == "1":
            add("ERRO", f"{p['nome']}: produto CONGELADO (sem novas alocações)")
        if p["qualificado"] == "1" and investidor != "Qualificado":
            add("ERRO", f"{p['nome']}: exclusivo para investidor qualificado")
        if p["tipo"] == "FIDC":
            if perfil == "Conservador":
                add("ERRO", f"{p['nome']}: FIDC é vetado para clientes conservadores")
            if w > FIDC_TETO + TOL:
                add("ERRO", f"{p['nome']}: {peso_fmt(w)} acima do teto de {peso_fmt(FIDC_TETO)} por FIDC")
        teto = float(p["alocacao_max_pct"]) if p["alocacao_max_pct"] not in ("", None) else None
        if teto is not None and teto > 0 and w > teto + TOL:
            add("ERRO", f"{p['nome']}: {peso_fmt(w)} acima da alocação máxima do produto ({p['alocacao_max_texto']})")
        if p["alocacao_max_texto"].upper() == "FMP":
            add("AVISO", f"{p['nome']}: aberto só a quem já entrou em alguma FMP")
        if "Finclass" in p["alocacao_max_texto"] or "Finclass" in p["nome"]:
            add("AVISO", f"{p['nome']}: carteira Finclass só entra em conjunto (todos os ativos, alocação indicada, máx. 10% no total)")
        if p["estrategia"] == "Gestão Ativa" and p["tipo"] in ("Fundo",):
            if w > ATIVA_TETO + TOL:
                add("ERRO", f"{p['nome']}: {peso_fmt(w)} acima de {peso_fmt(ATIVA_TETO)} por fundo de gestão ativa")
            por_gestora[p["nome"].split()[0]] += w
        if p["rating"] == "C":
            add("AVISO", f"{p['nome']}: rating C (a planilha pede preferência por A ou B)")

    for g, w in por_gestora.items():
        if w > GESTORA_TETO + TOL:
            add("AVISO", f"gestora '{g}' (agrupada pelo 1º termo do nome): {peso_fmt(w)} em gestão ativa, acima de {peso_fmt(GESTORA_TETO)}. A planilha não traz a gestora: conferir")

    lim = limites[perfil]
    for classe, w in por_classe.items():
        c = lim["classes"].get(classe)
        if c is None:
            add("ERRO", f"classe '{classe}' não existe nos limites do perfil {perfil}")
            continue
        if c["max"] is not None and w > c["max"] + TOL:
            add("ERRO", f"{classe}: {peso_fmt(w)} acima do máximo do perfil {perfil} ({peso_fmt(c['max'])})")
    for classe, c in lim["classes"].items():
        if c["min"] and por_classe.get(classe, 0) < c["min"] - TOL:
            add("ERRO", f"{classe}: {peso_fmt(por_classe.get(classe, 0))} abaixo do mínimo do perfil {perfil} ({peso_fmt(c['min'])})")
    for g in lim["grupos"]:
        w = sum(por_classe.get(c, 0) for c in g["classes"])
        nome_g = " + ".join(g["classes"])
        if g["max"] is not None and w > g["max"] + TOL:
            add("ERRO", f"grupo [{nome_g}]: {peso_fmt(w)} acima do máximo do grupo ({peso_fmt(g['max'])})")
        if g["min"] and w < g["min"] - TOL:
            add("ERRO", f"grupo [{nome_g}]: {peso_fmt(w)} abaixo do mínimo do grupo ({peso_fmt(g['min'])})")

    add("INFO", "alocação por classe: " + "; ".join(f"{c} {peso_fmt(w)}" for c, w in sorted(por_classe.items(), key=lambda t: -t[1])))
    if risco:
        add("INFO", "risco dos produtos identificados (faixa de queda histórica): " + "; ".join(f"{k} {peso_fmt(v)}" for k, v in sorted(risco.items())))
    add("INFO", f"base: {meta['titulo_planilha']} (importada em {meta['importado_em'][:10]}, {meta['n_produtos']} produtos)")
    return res


def ler_csv(path):
    itens = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            w = parse_peso(row["peso"])
            itens.append({"produto": row["produto"], "peso": w, "classe": row.get("classe", ""), "tipo": row.get("tipo", "")})
    if sum(i["peso"] for i in itens) > 1.5:
        for i in itens:
            i["peso"] /= 100
    return itens


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carteira", nargs="?")
    ap.add_argument("--perfil", required=True)
    ap.add_argument("--investidor", default="Geral", choices=["Geral", "Qualificado"])
    ap.add_argument("--modelo", help="valida uma carteira-modelo da planilha (ex.: 'Moderado')")
    ap.add_argument("--dados", default=str(Path(__file__).resolve().parent.parent / "dados_portfel"))
    a = ap.parse_args()
    dados = carregar_dados(a.dados)
    if a.modelo:
        itens = [{"produto": i["produto"], "peso": i["pct_pl"], "classe": i["classe"], "tipo": i["tipo"],
                  "generico": generico(i["produto"], i["tipo"])} for i in dados[2][a.modelo]]
        # tenta resolver por CNPJ/ticker quando o nome do modelo não bate com a lista
        for it, orig in zip(itens, dados[2][a.modelo]):
            if not it["generico"] and achar_produto(it["produto"], dados[0])[0] is None:
                p, _ = achar_produto(orig["cnpj_ticker"], dados[0])
                if p:
                    it["produto"] = p["nome"]
    elif a.carteira:
        itens = ler_csv(a.carteira)
    else:
        sys.exit("informe carteira.csv ou --modelo")
    resultado = validar(itens, a.perfil, a.investidor, dados)
    for nivel in ("ERRO", "AVISO", "INFO"):
        for n, m in resultado:
            if n == nivel:
                print(f"[{n}] {m}")
    erros = sum(1 for n, _ in resultado if n == "ERRO")
    print(f"\n{'REPROVADA' if erros else 'APROVADA'}: {erros} erro(s), {sum(1 for n, _ in resultado if n == 'AVISO')} aviso(s)")
    sys.exit(1 if erros else 0)
