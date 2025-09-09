import argparse
from pathlib import Path
from datetime import datetime
from openai import OpenAI

BASE_URL = "https://api.z.ai/api/paas/v4/"
MODEL = "glm-4.5"

SYSTEM = (
    "Você é um engenheiro SRE focado em diagnóstico e plano de ação. "
    "Seja direto, assertivo e priorize recomendações práticas."
)

USER_PREFIX = (
    "Analise o conteúdo abaixo (um relatório/summary em Markdown). "
    "Para cada erro citado, produza em Markdown:\n"
    "1) Possíveis causas raiz; 2) Evidências/checagens a coletar; "
    "3) Mitigações imediatas (quick wins) e correções definitivas; "
    "4) Indicadores/KPIs para monitorar; 5) Prioridade (Alta/Média/Baixa). "
    "Seja conciso e objetivo. Conteúdo a analisar:\n\n"
)

def read_md(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    return path.read_text(encoding="utf-8")

def write_md(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    print(f"[ok] gravado: {path.resolve()}")

def analyze_text(client: OpenAI, text: str) -> str:
    CHUNK = 12000
    messages = [{"role": "system", "content": SYSTEM}]

    if len(text) <= CHUNK:
        messages.append({"role": "user", "content": USER_PREFIX + text})
    else:
        parts = [text[i:i+CHUNK] for i in range(0, len(text), CHUNK)]
        messages.append({"role": "user", "content": USER_PREFIX + "(Parte 1 de N)\n\n" + parts[0]})
        for i, p in enumerate(parts[1:], start=2):
            messages.append({"role": "user", "content": f"(Parte {i} de N)\n\n{p}"})

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()

def main():
    ap = argparse.ArgumentParser(description="Ler um .md, enviar para Zhipu e salvar análise em .md")
    ap.add_argument("api_key", help="Zhipu API key (obrigatória)")
    ap.add_argument("input_md", help="Caminho do arquivo .md de entrada")
    ap.add_argument("-o", "--output", help="Caminho do .md de saída (opcional)")
    ap.add_argument("--model", default=MODEL, help="Modelo (padrão: glm-4.5)")
    args = ap.parse_args()

    in_path = Path(args.input_md).expanduser().resolve()
    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else in_path.with_name(
            f"{in_path.stem}__analise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
    )

    client = OpenAI(api_key=args.api_key, base_url=BASE_URL)

    try:
        md = read_md(in_path)
        analysis = analyze_text(client, md)
    except Exception as e:
        emsg = str(e)
        if "401" in emsg or "Unauthorized" in emsg:
            analysis = "# Erro: API key inválida/expirada na Zhipu."
        elif "429" in emsg or "limit" in emsg or "quota" in emsg:
            analysis = "# Erro: quota/limite atingido na Zhipu. Verifique seu billing."
        elif isinstance(e, FileNotFoundError):
            analysis = f"# Erro: arquivo não encontrado\n\n{emsg}"
        else:
            analysis = f"# Erro inesperado ao chamar a API\n\n```\n{emsg}\n```"

    write_md(out_path, analysis)

if __name__ == "__main__":
    main()
