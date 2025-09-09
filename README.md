# 📊 Log Analysis Toolkit

Conjunto de scripts em Python para análise de logs, geração de relatórios e diagnósticos assistidos por IA.  

## 🚀 Tecnologias

- Python 3.11+  
- openai>=1.0.0 (SDK oficial, usado em modo *OpenAI-compatible* para Zhipu)  
- matplotlib (gráficos)  
- csv / json / pathlib / argparse (builtin Python)  

Instalação das dependências:
`
pip install -r requirements.txt
`

Conteúdo do arquivo requirements.txt:

``
openai>=1.0.0
``
</br>
``
matplotlib
``

---

## 🔑 Como conseguir API Key da Zhipu (para ai_analyzer.py)

1. Acesse: <a href="https://open.bigmodel.cn/">Zhipu BigModel</a>.  
2. Crie uma conta.  
3. No console, vá em "API Key → 新建 API Key".  
4. Copie a sua chave (formato parecido com `xxxxxxxxxxxxx.MfPJtEy3cCtoPIn3`).  
5. Não compartilhe nem comite a chave em repositórios públicos.  

---

## 📂 Scripts

### 1) logs_categorizer.py

Analisa arquivos `.txt` de logs, detecta erros via regex e gera relatórios:

- CSV detalhado → cada ocorrência  
- CSV resumo → totais por tipo de erro  
- Markdown → relatório resumido em tabela  
- JSON → opcional  

Uso:

`
python logs_categorizer.py -i logs/ -o results/ -b logs --export-json
`

Saída esperada:

results/  
├── logs_erros_detalhados.csv  
├── logs_erros_resumo.csv  
├── logs_RELATORIO_SUMARIO.md  
└── logs_resumo.json   (se usar --export-json)  


---

### 2) chart_generator.py

Gera visualizações em PNG a partir do CSV resumo:

- Barras (vertical e horizontal)  
- Pizza (distribuição %)  
- Pareto (80/20)  
- Severidade (se fornecido CSV enriquecido)  

Uso:
`
python chart_generator.py --summary results/logs_erros_resumo.csv --out charts/
`

Saída esperada:

charts/  
├── bar_top.png  
├── barh_top.png  
├── pie_distribution.png  
└── pareto_top.png  


---

### 3) ai_analyzer.py

Envia o relatório em Markdown para a IA Zhipu GLM-4.5, que retorna análise com:

- Possíveis causas raiz  
- Evidências a coletar  
- Mitigações rápidas e soluções definitivas  
- Indicadores para monitorar  
- Priorização (Alta / Média / Baixa)  

Uso:
`
python ai_analyzer.py SUA_API_KEY results/logs_RELATORIO_SUMARIO.md -o results/analise.md
`

Saída: um novo arquivo `.md` com a análise detalhada.  

---

## 🔄 Fluxo sugerido

1. Extrair erros dos logs:  
   ``python logs_categorizer.py -i logs/ -o results/ -b logs --export-json``

2. Gerar gráficos:  
   ``python chart_generator.py --summary results/logs_erros_resumo.csv --out charts/ --top 10``  

3. Rodar análise com IA:  
   ``python ai_analyzer.py SUA_API_KEY results/logs_RELATORIO_SUMARIO.md -o results/analise.md``  

---

## ⚠️ Cuidados

- Use aspas em caminhos no Windows se houver espaços.  
- No OneDrive pode dar "PermissionError"; se der, use C:\Temp ou Desktop.  
- Nunca exponha a API key da Zhipu em público.  
