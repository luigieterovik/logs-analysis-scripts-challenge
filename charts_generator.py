#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional
import matplotlib.pyplot as plt

def read_counts(summary_csv: Path) -> List[Dict]:
    rows = []
    with summary_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = (r.get("error_name") or r.get("Erro") or r.get("error") or "").strip()
            if not name:
                continue
            try:
                count = int(r.get("count") or 0)
            except Exception:
                continue
            rows.append({"error_name": name, "count": count})
    rows.sort(key=lambda x: (-x["count"], x["error_name"]))
    return rows

def read_severity(enriched_csv: Optional[Path]) -> Dict[str, str]:
    sev = {}
    if not enriched_csv or not enriched_csv.exists():
        return sev
    with enriched_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = (r.get("error_name") or "").strip()
            s = (r.get("severity") or "").strip()
            if name and s:
                sev[name] = s
    return sev

def ensure_out(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)

def save_png(fig, out_png: Path):
    fig.tight_layout()
    fig.savefig(out_png, dpi=160, bbox_inches="tight")
    plt.close(fig)

def bar_top(errors: List[Dict], outdir: Path, top: int):
    data = errors[:top]
    labels = [r["error_name"] for r in data]
    counts = [r["count"] for r in data]

    fig = plt.figure()
    plt.bar(labels, counts)
    plt.xticks(rotation=45, ha="right")
    plt.title(f"Top {len(data)} erros por quantidade")
    plt.xlabel("Erro")
    plt.ylabel("Ocorrências")
    save_png(fig, outdir / "bar_top.png")

def barh_top(errors: List[Dict], outdir: Path, top: int):
    data = errors[:top][::-1]
    labels = [r["error_name"] for r in data]
    counts = [r["count"] for r in data]

    fig = plt.figure()
    plt.barh(labels, counts)
    plt.title(f"Top {len(data)} erros (horizontal)")
    plt.xlabel("Ocorrências")
    plt.ylabel("Erro")
    save_png(fig, outdir / "barh_top.png")

def pie_dist(errors: List[Dict], outdir: Path, top: int):
    data = errors[:top]
    labels = [r["error_name"] for r in data]
    sizes = [r["count"] for r in data]
    other = sum(r["count"] for r in errors[top:])
    if other > 0:
        labels.append("Outros")
        sizes.append(other)

    fig = plt.figure()
    plt.pie(sizes, labels=labels, autopct=lambda p: f"{p:.1f}%" if p >= 3 else "")
    plt.title(f"Distribuição (%) — Top {min(top, len(data))} + Outros")
    save_png(fig, outdir / "pie_distribution.png")

def pareto(errors: List[Dict], outdir: Path, top: int):
    data = errors[:top]
    labels = [r["error_name"] for r in data]
    counts = [r["count"] for r in data]
    total = sum(r["count"] for r in errors) or 1
    cumulative, csum = [], 0
    for c in counts:
        csum += c
        cumulative.append(100.0 * csum / total)

    fig, ax1 = plt.subplots()
    ax1.bar(labels, counts)
    ax1.set_ylabel("Ocorrências")
    ax1.set_title(f"Pareto — Top {len(data)} erros")
    plt.xticks(rotation=45, ha="right")

    ax2 = ax1.twinx()
    ax2.plot(range(len(data)), cumulative, marker="o", color="red")
    ax2.set_ylabel("Acumulado (%)")
    ax2.set_ylim(0, 110)

    save_png(fig, outdir / "pareto_top.png")

def bar_by_severity(errors: List[Dict], sevmap: Dict[str, str], outdir: Path, top: int):
    if not sevmap:
        return
    bysev: Dict[str, int] = {}
    for r in errors[:top]:
        sev = sevmap.get(r["error_name"], "Indefinida") or "Indefinida"
        bysev[sev] = bysev.get(sev, 0) + r["count"]

    labels = list(bysev.keys())
    counts = [bysev[k] for k in labels]
    fig = plt.figure()
    plt.bar(labels, counts)
    plt.title(f"Ocorrências por Severidade (Top {top} erros)")
    plt.xlabel("Severidade")
    plt.ylabel("Ocorrências")
    save_png(fig, outdir / "bar_by_severity.png")

def main():
    parser = argparse.ArgumentParser(description="Gera gráficos a partir do CSV de resumo.")
    parser.add_argument("--summary", required=True, help="CSV do resumo (error_name,count,...)")
    parser.add_argument("--out", required=True, help="Pasta de saída")
    parser.add_argument("--top", type=int, default=12, help="Quantos erros mostrar")
    parser.add_argument("--enriched", help="CSV enriquecido (opcional)")
    args = parser.parse_args()

    summary_csv = Path(args.summary)
    if not summary_csv.exists():
        raise SystemExit(f"[ERRO] CSV não encontrado: {summary_csv}")
    outdir = Path(args.out)
    ensure_out(outdir)

    errors = read_counts(summary_csv)
    if not errors:
        raise SystemExit("[ERRO] CSV sem dados.")

    sevmap = read_severity(Path(args.enriched)) if args.enriched else {}

    bar_top(errors, outdir, args.top)
    barh_top(errors, outdir, args.top)
    pie_dist(errors, outdir, args.top)
    pareto(errors, outdir, args.top)
    bar_by_severity(errors, sevmap, outdir, args.top)

    print("[OK] Gráficos gerados em:", outdir)

if __name__ == "__main__":
    main()
