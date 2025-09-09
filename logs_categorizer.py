#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
analisador_logs_basico.py
Analisa logs, detecta erros e gera relatórios (CSV + Markdown), sem severity/hints.
Detalhado CSV agora contém apenas: error_name, file, line, message.
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# =========================
# 1) Padrões de erro
# =========================
ERROR_PATTERNS = [
    {"name": "NetworkError", "regex": r"nsUtils.*err:\s*5|network\s+list.*err:\s*5"},
    {"name": "TunnelError", "regex": r"CTunnelMgr.*No tunnel found|tunnel.*not\s+found"},
    {"name": "Proxy403", "regex": r"HTTP\s+response\s+code:\s*403|forbidden"},
    {"name": "RecordingCorrupted", "regex": r"corrupted\s+recording|Failed to finalize record|Recovery process failed to recover"},
    {"name": "PSM_DuplicateSession", "regex": r"Duplicated session was (created|deleted)|Session UUID.*was unregistered"},
    {"name": "PSM_VaultIssues", "regex": r"Attempting to delete the Vault user session|Vault session .* does not exist|Open vault file operation (success|fail)"},
    {"name": "PSM_ListenerLogoff", "regex": r"PSM listener.*logoff|TSSession logoff event"},
    {"name": "PSM_InternalConn", "regex": r"InternalConnectionClient.*(has stopped|Terminating session process)"},
    {"name": "Auth_TicketMissing", "regex": r"Ticket ID was not found|Failed to find session identifiers|session LUID was not found"},
]

# =========================
# 2) Regex auxiliares
# =========================
TS_PATTERNS = [
    r"\[(\d{2}/\d{2}/\d{4}).*?\|",  # [10/04/2025 | ...]
    r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})",  # 2025-04-10 12:34:56
]
UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SESSION_ID_REGEX = r"session id[:\s]\s*(\d+)"

def extract_timestamp(line: str) -> Optional[str]:
    for pat in TS_PATTERNS:
        m = re.search(pat, line)
        if m:
            val = m.group(1)
            try:
                if re.match(r"\d{2}/\d{2}/\d{4}$", val):
                    dt = datetime.strptime(val, "%d/%m/%Y")
                    return dt.isoformat()
                else:
                    val = val.replace(" ", "T")
                    datetime.fromisoformat(val)
                    return val
            except Exception:
                return val
    return None

def extract_uuid(line: str) -> Optional[str]:
    m = re.search(UUID_REGEX, line, re.IGNORECASE)
    return m.group(0) if m else None

def extract_session_id(line: str) -> Optional[str]:
    m = re.search(SESSION_ID_REGEX, line, re.IGNORECASE)
    return m.group(1) if m else None

# =========================
# 3) Varredura de arquivos
# =========================
def iter_input_files(inputs: List[str]) -> List[Path]:
    files: List[Path] = []
    for inp in inputs:
        p = Path(inp)
        if p.is_dir():
            files += [f for f in p.rglob("*.txt")]
        elif p.is_file():
            files.append(p)
        else:
            print(f"[WARN] Caminho não encontrado: {inp}", file=sys.stderr)
    return sorted(set(files))

# =========================
# 4) Análise de linhas
# =========================
def analyze_files(files: List[Path]) -> Tuple[List[Dict], Dict]:
    occurrences: List[Dict] = []
    summary: Dict[str, Dict] = {}

    compiled = [(p["name"], re.compile(p["regex"], re.IGNORECASE)) for p in ERROR_PATTERNS]

    for fpath in files:
        try:
            with fpath.open("r", encoding="utf-8", errors="ignore") as fh:
                for lineno, line in enumerate(fh, start=1):
                    for name, cregex in compiled:
                        if cregex.search(line):
                            ts = extract_timestamp(line)
                            uuid = extract_uuid(line)
                            sid = extract_session_id(line)
                            msg = line.strip()

                            # Guarda dados completos internamente (útil para futuras expansões),
                            # mas não escreveremos ts/uuid/sid no CSV detalhado.
                            occ = {
                                "error_name": name,
                                "file": str(fpath),
                                "line": lineno,
                                "timestamp": ts or "",
                                "session_uuid": uuid or "",
                                "session_id": sid or "",
                                "message": msg,
                            }
                            occurrences.append(occ)

                            if name not in summary:
                                summary[name] = {
                                    "error_name": name,
                                    "count": 0,
                                    "first_seen": ts or "",
                                    "last_seen": ts or "",
                                    "files": set(),
                                    "sample_message": msg,
                                }
                            summary[name]["count"] += 1
                            summary[name]["files"].add(str(fpath))

                            if ts:
                                if not summary[name]["first_seen"]:
                                    summary[name]["first_seen"] = ts
                                if not summary[name]["last_seen"]:
                                    summary[name]["last_seen"] = ts
                                try:
                                    fdt = datetime.fromisoformat(summary[name]["first_seen"].replace(" ", "T"))
                                    ldt = datetime.fromisoformat(summary[name]["last_seen"].replace(" ", "T"))
                                    cdt = datetime.fromisoformat(ts.replace(" ", "T"))
                                    if cdt < fdt:
                                        summary[name]["first_seen"] = ts
                                    if cdt > ldt:
                                        summary[name]["last_seen"] = ts
                                except Exception:
                                    pass
                            break
        except Exception as e:
            print(f"[ERRO] Falha lendo {fpath}: {e}", file=sys.stderr)

    for k, v in summary.items():
        v["files"] = sorted(list(v["files"]))

    return occurrences, summary

# =========================
# 5) Escrita dos relatórios
# =========================
def write_csv_occurrences(occurrences: List[Dict], outdir: Path, basename: str = "erros_detalhados") -> Path:
    outpath = outdir / f"{basename}.csv"
    with outpath.open("w", newline="", encoding="utf-8") as csvfile:
        # REMOVIDO: timestamp, session_uuid, session_id
        fieldnames = ["error_name", "file", "line", "message"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for occ in occurrences:
            writer.writerow({
                "error_name": occ["error_name"],
                "file": occ["file"],
                "line": occ["line"],
                "message": occ["message"],
            })
    return outpath

def write_csv_summary(summary: Dict[str, Dict], outdir: Path, basename: str = "erros_resumo") -> Path:
    outpath = outdir / f"{basename}.csv"
    with outpath.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["error_name", "count", "first_seen", "last_seen", "files", "sample_message"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for name, data in sorted(summary.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
            row = data.copy()
            row["files"] = ";".join(row["files"])
            writer.writerow(row)
    return outpath

def write_markdown(summary: Dict[str, Dict], outdir: Path, basename: str = "RELATORIO_SUMARIO") -> Path:
    outpath = outdir / f"{basename}.md"
    total = sum(v["count"] for v in summary.values()) if summary else 0
    lines = []
    lines.append("# Sumário de Erros Detectados\n")
    lines.append(f"- Total de categorias de erro: **{len(summary)}**")
    lines.append(f"- Total de ocorrências: **{total}**\n")
    if not summary:
        lines.append("> Nenhum erro mapeado.\n")
    else:
        lines.append("| Erro | Ocorrências | Primeiro visto | Último visto | Arquivos afetados |")
        lines.append("|---|---:|---|---|---|")
        for name, data in sorted(summary.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
            files = ", ".join(Path(f).name for f in data["files"])
            lines.append(f"| {name} | {data['count']} | {data['first_seen'] or '-'} | {data['last_seen'] or '-'} | {files or '-'} |")
    with outpath.open("w", encoding="utf-8") as md:
        md.write("\n".join(lines))
    return outpath

# =========================
# 6) CLI
# =========================
def main():
    parser = argparse.ArgumentParser(description="Analisa logs, detecta erros e gera relatórios (CSV + Markdown).")
    parser.add_argument("--input", "-i", nargs="+", required=True,
                        help="Arquivos .txt e/ou pastas com logs (aceita múltiplos).")
    parser.add_argument("--output", "-o", required=True,
                        help="Pasta de saída para os relatórios.")
    parser.add_argument("--basename", "-b", default="logs",
                        help="Prefixo base para os arquivos de saída (opcional).")
    parser.add_argument("--export-json", action="store_true",
                        help="Exporta também um JSON com o resumo.")
    args = parser.parse_args()

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    files = iter_input_files(args.input)
    if not files:
        print("[ERRO] Nenhum arquivo de entrada encontrado.", file=sys.stderr)
        sys.exit(2)

    print(f"[INFO] Analisando {len(files)} arquivo(s)...")
    occurrences, summary = analyze_files(files)

    det_csv = write_csv_occurrences(occurrences, outdir, basename=f"{args.basename}_erros_detalhados")
    sum_csv = write_csv_summary(summary, outdir, basename=f"{args.basename}_erros_resumo")
    md_path = write_markdown(summary, outdir, basename=f"{args.basename}_RELATORIO_SUMARIO")

    if args.export_json:
        json_path = outdir / f"{args.basename}_resumo.json"
        with json_path.open("w", encoding="utf-8") as jf:
            json.dump(summary, jf, ensure_ascii=False, indent=2, default=str)
        print(f"[OK] JSON: {json_path}")

    print(f"[OK] Detalhado CSV: {det_csv}")
    print(f"[OK] Resumo CSV:    {sum_csv}")
    print(f"[OK] Markdown:      {md_path}")

if __name__ == "__main__":
    main()
