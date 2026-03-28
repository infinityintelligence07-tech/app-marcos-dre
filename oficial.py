import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import base64
import os
import json
import time
import calendar
import uuid
import math
from pathlib import Path
from datetime import date, datetime, timedelta

# ---------------------------------------------------------
# 1) LAYOUT & UI/UX (Configuração da Página SaaS)
# ---------------------------------------------------------
st.set_page_config(page_title="DRE Executivo", page_icon="📊", layout="wide")

# Toast Message System (Feedback Visual)
if "toast_msg" in st.session_state and st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg, icon="✅")
    st.session_state.toast_msg = None

def show_toast(msg):
    st.session_state.toast_msg = msg

components.html(
    "<script>\n"
    "const parentDoc = window.parent.document;\n"
    "parentDoc.documentElement.lang = 'pt-PT'; parentDoc.documentElement.setAttribute('translate', 'no');\n"
    "function formatCurrency(val) {\n"
    "    let numVal = val.replace(/\\D/g, ''); if (numVal === '') numVal = '0';\n"
    "    let num = parseInt(numVal, 10) / 100; let strNum = num.toFixed(2).replace('.', ',');\n"
    "    let parts = strNum.split(','); parts[0] = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');\n"
    "    return 'R$ ' + parts.join(',');\n"
    "}\n"
    "parentDoc.addEventListener('input', function(e) {\n"
    "    if (e.target && e.target.tagName === 'INPUT' && (e.target.placeholder === 'R$ 0,00' || e.target.value.includes('R$'))) {\n"
    "        if (e.target.dataset.isMasking === 'true') return;\n"
    "        let finalStr = formatCurrency(e.target.value);\n"
    "        if (e.target.value !== finalStr && finalStr !== 'R$ 0,00') {\n"
    "            e.target.dataset.isMasking = 'true';\n"
    "            let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;\n"
    "            if (nativeInputValueSetter) { nativeInputValueSetter.call(e.target, finalStr); e.target.dispatchEvent(new Event('input', { bubbles: true })); }\n"
    "            e.target.dataset.isMasking = 'false';\n"
    "        }\n"
    "    }\n"
    "}, true);\n"
    "</script>", width=0, height=0
)

# ---------------------------------------------------------
# 2) MOTOR DE BANCO DE DADOS MULTI-EMPRESAS
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = Path(os.getenv("DRE_DB_FILE", BASE_DIR / "dre_database.json"))

def load_db():
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "empresas" not in data:
                    migrated = {"empresas": {"emp_principal_1": {"nome": "Empresa Principal", "cnpj": "", "obs": "Migração Automática", "ativo": True, "dados": data}}}
                    return migrated
                for k, v in data["empresas"].items():
                    if "ativo" not in v: v["ativo"] = True
                    if "cenarios" not in v: v["cenarios"] = {"c2": 30.0, "c3": 70.0}
                return data
        except: pass
    return {"empresas": {"emp_padrao_1": {"nome": "Empresa Matriz", "cnpj": "", "obs": "Criada automaticamente", "ativo": True, "cenarios": {"c2": 30.0, "c3": 70.0}, "dados": {"plano_contas": [], "orcamentos": [], "lancamentos_reais": [], "bancos": [], "pendencias": [], "saldo_inicial": 0.0, "regras_pendencia": {"tipo": "Quantidade", "limite": 5}, "formas_pagamento": ["PIX", "Cartão de Crédito", "Boleto", "Dinheiro"], "acao_cfo": {"entradas": {}, "saidas": {}}}}}}

def save_db():
    if st.session_state.empresa_selecionada != "TODAS":
        eid = st.session_state.empresa_selecionada
        st.session_state.db["empresas"][eid]["dados"] = {
            "plano_contas": st.session_state.plano_contas,
            "orcamentos": st.session_state.orcamentos,
            "lancamentos_reais": st.session_state.lancamentos_reais,
            "bancos": st.session_state.bancos,
            "pendencias": st.session_state.pendencias,
            "saldo_inicial": st.session_state.saldo_inicial,
            "regras_pendencia": st.session_state.get("regras_pendencia", {"tipo": "Quantidade", "limite": 5}),
            "formas_pagamento": st.session_state.get("formas_pagamento", []),
            "acao_cfo": st.session_state.get("acao_cfo", {"entradas": {}, "saidas": {}})
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.db, f, indent=4)

if "db_loaded" not in st.session_state:
    st.session_state.db = load_db()
    st.session_state.empresa_selecionada = list(st.session_state.db["empresas"].keys())[0]
    st.session_state.db_loaded = True

# SINCRONIZADOR DE CONTEXTO (Troca de Empresas)
if st.session_state.empresa_selecionada == "TODAS":
    agg_pc = {}
    agg_orc, agg_lanc, agg_pend, agg_bancos = [], [], [], []
    agg_saldo = 0.0
    for emp in st.session_state.db["empresas"].values():
        if not emp.get("ativo", True): continue
        d = emp["dados"]
        for pc in d.get("plano_contas", []): agg_pc[pc["nome_conta"]] = pc
        agg_orc.extend(d.get("orcamentos", []))
        agg_lanc.extend(d.get("lancamentos_reais", []))
        agg_pend.extend(d.get("pendencias", []))
        agg_bancos.extend([{"empresa": emp["nome"], **b} for b in d.get("bancos", [])])
        agg_saldo += d.get("saldo_inicial", 0.0)
    
    st.session_state.plano_contas = list(agg_pc.values())
    st.session_state.orcamentos = agg_orc
    st.session_state.lancamentos_reais = agg_lanc
    st.session_state.pendencias = agg_pend
    st.session_state.bancos = agg_bancos
    st.session_state.saldo_inicial = agg_saldo
    st.session_state.regras_pendencia = {"tipo": "Quantidade", "limite": 5}
    st.session_state.formas_pagamento = []
    st.session_state.acao_cfo = {"entradas": {}, "saidas": {}}
    st.session_state.cenarios_cfg = {"c2": 30.0, "c3": 70.0}
else:
    emp_cfg = st.session_state.db["empresas"][st.session_state.empresa_selecionada]
    d = emp_cfg["dados"]
    st.session_state.plano_contas = d.get("plano_contas", [])
    st.session_state.orcamentos = d.get("orcamentos", [])
    st.session_state.lancamentos_reais = d.get("lancamentos_reais", [])
    st.session_state.bancos = d.get("bancos", [])
    st.session_state.pendencias = d.get("pendencias", [])
    st.session_state.saldo_inicial = d.get("saldo_inicial", 0.0)
    st.session_state.regras_pendencia = d.get("regras_pendencia", {"tipo": "Quantidade", "limite": 5})
    st.session_state.formas_pagamento = d.get("formas_pagamento", ["PIX", "Cartão de Crédito", "Boleto", "Dinheiro"])
    st.session_state.acao_cfo = d.get("acao_cfo", {"entradas": {}, "saidas": {}})
    st.session_state.cenarios_cfg = emp_cfg.get("cenarios", {"c2": 30.0, "c3": 70.0})

    for o in st.session_state.orcamentos:
        if "id" not in o: o["id"] = str(uuid.uuid4())
        if "efetivado" not in o: o["efetivado"] = False
    for l in st.session_state.lancamentos_reais:
        if "ativo" not in l: l["ativo"] = True
        if "transacao_id" not in l: l["transacao_id"] = str(uuid.uuid4())
        if "nao_previsto" not in l: l["nao_previsto"] = False

DEFAULT_PRIMARY = "#0A1D56"
DEFAULT_BG = "#F4F5F8"
DEFAULT_TEXT = "#1A202C"

for key, val in [("color_primary", DEFAULT_PRIMARY), ("color_bg", DEFAULT_BG), ("color_text", DEFAULT_TEXT)]:
    if key not in st.session_state: st.session_state[key] = val

if "logo_b64" not in st.session_state: st.session_state.logo_b64 = None
if "data_inicio" not in st.session_state: st.session_state.data_inicio = date.today().replace(day=1)
if "data_fim" not in st.session_state: st.session_state.data_fim = date.today()

custom_css = f"""<style>
    :root {{ --primary-color: {st.session_state.color_primary}; }}
    html, body, [data-testid="stAppViewContainer"], .stApp {{ background-color: {st.session_state.color_bg}; overflow-x: hidden !important; max-width: 100vw; }}
    #MainMenu, footer, header, [data-testid="collapsedControl"], section[data-testid="stSidebar"] {{ display: none !important; visibility: hidden !important; }}
    .block-container {{ padding-top: 0.5rem; padding-bottom: 2rem; max-width: 98% !important; padding-left: 1rem !important; padding-right: 1rem !important; overflow-x: hidden !important; }}
    h1, h2, h3, p, div, span {{ font-family: 'Inter', sans-serif; }}
    [data-testid="stDataFrame"] {{ background-color: white; border-radius: 16px; padding: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #D1E0FF; }}
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{ background-color: #FFFFFF !important; }}
    .saas-page-title {{ font-size: 22px !important; font-weight: 700 !important; color: #0F172A !important; letter-spacing: -0.02em !important; margin-bottom: 4px !important; display: flex !important; align-items: center !important; gap: 8px !important; }}
    .saas-page-subtitle {{ font-size: 13.5px !important; color: #64748B !important; margin-top: 0 !important; margin-bottom: 24px !important; font-weight: 400 !important; }}
    .saas-section-title {{ font-size: 16px !important; font-weight: 600 !important; color: #1E293B !important; margin-top: 0 !important; margin-bottom: 6px !important; display: flex !important; align-items: center !important; gap: 8px !important; letter-spacing: -0.01em !important; }}
    .saas-section-subtitle {{ font-size: 12.5px !important; color: #94A3B8 !important; margin-top: 0 !important; margin-bottom: 16px !important; }}
    .saas-form-group-title {{ font-size: 12.5px !important; font-weight: 700 !important; color: #4A5568 !important; margin-bottom: 12px !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; }}
    .stButton button {{ border-radius: 8px !important; font-size: 12.5px !important; font-weight: 600 !important; height: 38px !important; min-height: 38px !important; padding: 0px 16px !important; transition: all 0.2s ease-in-out !important; border: 1px solid transparent !important; text-transform: none !important; letter-spacing: 0.2px; line-height: 1 !important; }}
    #nav-anchor + div[data-testid="stHorizontalBlock"] {{ background-color: #FFFFFF !important; padding: 6px 10px !important; border-radius: 50px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.04) !important; border: 1px solid #D1E0FF !important; margin-bottom: 24px !important; width: fit-content !important; gap: 4px !important; align-items: center !important; }}
    #nav-anchor + div[data-testid="stHorizontalBlock"] > div {{ width: auto !important; min-width: auto !important; flex: 0 1 auto !important; }}
    #nav-anchor + div[data-testid="stHorizontalBlock"] button {{ border-radius: 50px !important; border: none !important; height: 36px !important; min-height: 36px !important; box-shadow: none !important; font-size: 13px !important; font-weight: 600 !important; padding: 0 18px !important; margin: 0 !important; }}
    #nav-anchor + div[data-testid="stHorizontalBlock"] button[kind="secondary"] {{ background-color: transparent !important; color: #64748B !important; }}
    #nav-anchor + div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{ background-color: #F1F5F9 !important; color: var(--primary-color) !important; }}
    #nav-anchor + div[data-testid="stHorizontalBlock"] button[kind="primary"] {{ background-color: var(--primary-color) !important; color: white !important; }}
    button[kind="primary"]:not(#nav-anchor button) {{ background-color: var(--primary-color) !important; color: white !important; box-shadow: 0 2px 4px rgba(0,0,0, 0.08) !important; }}
    button[kind="primary"]:not(#nav-anchor button):hover {{ box-shadow: 0 4px 8px rgba(0,0,0, 0.12) !important; transform: translateY(-1px); filter: brightness(1.15); }}
    button[kind="secondary"]:not(#nav-anchor button) {{ background-color: white !important; color: #4A5568 !important; border: 1px solid #D1E0FF !important; box-shadow: 0 1px 2px rgba(0,0,0, 0.02) !important; }}
    button[kind="secondary"]:not(#nav-anchor button):hover {{ border-color: var(--primary-color) !important; color: var(--primary-color) !important; background-color: #F8FAFC !important; }}
    div[data-baseweb="tab-list"] {{ gap: 8px; background-color: #F1F5F9; padding: 6px; border-radius: 12px; border: 1px solid #D1E0FF; margin-bottom: 15px; }}
    button[data-baseweb="tab"] {{ background-color: transparent !important; border-radius: 8px !important; border: none !important; color: #64748B !important; font-size: 13px !important; font-weight: 600 !important; padding: 8px 20px !important; margin: 0 !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ background-color: var(--primary-color) !important; color: white !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; }}
    div[data-baseweb="tab-highlight"] {{ display: none !important; }}
    div[data-testid="stDateInput"] label p, div[data-testid="stSelectbox"] label p, div[data-testid="stTextInput"] label p, div[data-testid="stNumberInput"] label p, div[data-testid="stColorPicker"] label p {{ text-transform: none !important; font-weight: 500 !important; color: #4A5568 !important; font-size: 13px !important; letter-spacing: 0px !important; margin-bottom: 2px !important; }}
    div[data-testid="stDateInput"] > div, div[data-testid="stSelectbox"] > div, div[data-testid="stTextInput"] > div, div[data-testid="stNumberInput"] > div, div[data-testid="stTextArea"] > div {{ border-radius: 8px !important; border: 1px solid #D1E0FF !important; box-shadow: inset 0 1px 2px rgba(0,0,0,0.02) !important; padding: 0px 8px !important; background-color: #FFFFFF !important; transition: border-color 0.2s ease, box-shadow 0.2s ease; min-height: 38px !important; }}
    div[data-testid="stDateInput"] > div:focus-within, div[data-testid="stSelectbox"] > div:focus-within, div[data-testid="stTextInput"] > div:focus-within, div[data-testid="stNumberInput"] > div:focus-within, div[data-testid="stTextArea"] > div:focus-within {{ border-color: var(--primary-color) !important; box-shadow: 0 0 0 1px var(--primary-color) !important; background-color: #FFFFFF !important; }}
    div[data-testid="stDateInput"] svg {{ fill: var(--primary-color) !important; color: var(--primary-color) !important; }}
    input::placeholder, textarea::placeholder {{ color: #CBD5E1 !important; opacity: 1 !important; }}
    div[data-testid="stExpander"] {{ border: 1px solid #D1E0FF !important; border-radius: 16px !important; background-color: white !important; box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important; margin-bottom: 8px !important; }}
    div[data-testid="stExpander"] details summary {{ padding: 12px 15px !important; font-weight: 600 !important; color: #1E293B !important; }}
    div[data-testid="stCheckbox"] label p {{ font-weight: 500 !important; color: #4A5568 !important; font-size: 13px !important; }}
</style>"""
st.markdown(custom_css, unsafe_allow_html=True)

if "pagina_atual" not in st.session_state: st.session_state.pagina_atual = "DASH"

def parse_currency(val_str):
    if pd.isna(val_str) or not val_str: return 0.0
    val_str = str(val_str).strip()
    if val_str in ['-', '+']: return 0.0
    is_negative = False
    if val_str.startswith('-'): is_negative = True; val_str = val_str[1:].strip()
    val_str = val_str.replace('R$', '').strip()
    if val_str.isdigit(): res = float(val_str) / 100.0; return -res if is_negative else res
    val_str = val_str.replace(' ', '')
    if ',' in val_str and '.' in val_str: val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str: val_str = val_str.replace(',', '.')
    elif val_str.count('.') > 1: val_str = val_str.replace('.', '')
    try: res = float(val_str); return -res if is_negative else res
    except ValueError: return 0.0

def formatar_moeda(valor): return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def aplicar_mascara_moeda(key):
    if key in st.session_state: st.session_state[key] = formatar_moeda(parse_currency(st.session_state[key]))

def aplicar_mascara_telefone(key):
    if key in st.session_state:
        val = str(st.session_state[key])
        num = ''.join(filter(str.isdigit, val))
        if len(num) == 11: st.session_state[key] = f"({num[:2]}) {num[2:7]}-{num[7:]}"
        elif len(num) == 10: st.session_state[key] = f"({num[:2]}) {num[2:6]}-{num[6:]}"

def aplicar_mascara_e_salvar_saldo(idx, key):
    if key in st.session_state:
        num = parse_currency(st.session_state[key])
        st.session_state[key] = formatar_moeda(num)
        if st.session_state.bancos[idx]["saldo"] != num:
            st.session_state.bancos[idx]["saldo"] = num
            st.session_state.bancos[idx]["ultima_atualizacao"] = date.today().strftime("%d/%m/%Y")
            save_db()

# MOTOR DE SIMULAÇÃO CFO
def get_multiplicador(categoria_interna, conta_nome, data_ref_str):
    if st.session_state.empresa_selecionada == "TODAS": return 1.0
    acao = st.session_state.get("acao_cfo", {"entradas": {}, "saidas": {}})
    tipo_macro = "entradas" if categoria_interna in ["receita", "outras_receitas"] else "saidas"
    
    regras_cat = acao[tipo_macro].get(categoria_interna, {})
    regra = regras_cat.get(conta_nome) or regras_cat.get("todas")
    
    if regra:
        try:
            d_criacao = datetime.strptime(regra["data"], "%Y-%m-%d").date()
            d_ref = datetime.strptime(data_ref_str, "%Y-%m-%d").date()
            if d_ref >= d_criacao: return 1.0 + (regra["pct"] / 100.0)
        except: pass
        
    return 1.0

def consolidar_dados_periodo(d_in, d_out, aplicar_cfo=True):
    consolidados = {c["nome_conta"]: {"tipo": c["categoria_dre"], "exige_fat": c.get("exige_faturamento", False), "p1": 0.0, "p2": 0.0, "p3": 0.0, "real": 0.0, "faturado_p": 0.0, "faturado_real": 0.0} for c in st.session_state.plano_contas}
    consolidados["📥 Entradas Pendentes"] = {"tipo": "receita", "exige_fat": False, "p1": 0.0, "p2": 0.0, "p3": 0.0, "real": 0.0, "faturado_p": 0.0, "faturado_real": 0.0}
    consolidados["📤 Saídas Pendentes"] = {"tipo": "outras_despesas", "exige_fat": False, "p1": 0.0, "p2": 0.0, "p3": 0.0, "real": 0.0, "faturado_p": 0.0, "faturado_real": 0.0}
    for o in st.session_state.orcamentos:
        try:
            if d_in <= datetime.strptime(o["data_ref"], "%Y-%m-%d").date() <= d_out and o["conta"] in consolidados:
                c_name = o["conta"]
                c_cat = consolidados[c_name]["tipo"]
                mult = get_multiplicador(c_cat, c_name, o["data_ref"]) if aplicar_cfo else 1.0
                
                consolidados[c_name]["p1"] += float(o.get("p1", 0.0)) * mult
                consolidados[c_name]["p2"] += float(o.get("p2", 0.0)) * mult
                consolidados[c_name]["p3"] += float(o.get("p3", 0.0)) * mult
        except: pass
    for l in st.session_state.lancamentos_reais:
        if l.get("ativo", True):
            try:
                if d_in <= datetime.strptime(l["data_real"], "%Y-%m-%d").date() <= d_out and l["conta"] in consolidados: consolidados[l["conta"]]["real"] += float(l.get("valor", 0.0))
            except: pass
    for p in st.session_state.pendencias:
        try:
            if d_in <= datetime.strptime(p["data"], "%Y-%m-%d").date() <= d_out:
                v_pend = float(p.get("valor", 0.0))
                if p.get("conta") and p["conta"] in consolidados:
                    consolidados[p["conta"]]["real"] += v_pend
                else:
                    if p["tipo"] == "entrada": consolidados["📥 Entradas Pendentes"]["real"] += v_pend
                    elif p["tipo"] == "saida": consolidados["📤 Saídas Pendentes"]["real"] += v_pend
        except: pass
    return consolidados

def consolidar_dados():
    return consolidar_dados_periodo(st.session_state.data_inicio, st.session_state.data_fim, aplicar_cfo=True)

def calcular_dre(c):
    d = {k: {"p1": 0.0, "p2": 0.0, "p3": 0.0, "real": 0.0} for k in ["receita_bruta", "deducoes", "receita_liquida", "custos_variaveis", "margem_contribuicao", "despesas_operacionais", "ebitda", "outras_receitas", "outras_despesas", "investimentos", "emprestimos", "resultado_bruto", "distribuicao_lucro", "resultado_liquido"]}
    for _, v in c.items():
        t = v["tipo"]
        if t == "receita": d["receita_bruta"]["p1"]+=v["p1"]; d["receita_bruta"]["p2"]+=v["p2"]; d["receita_bruta"]["p3"]+=v["p3"]; d["receita_bruta"]["real"]+=v["real"]
        elif t == "deducao": d["deducoes"]["p1"]+=v["p1"]; d["deducoes"]["p2"]+=v["p2"]; d["deducoes"]["p3"]+=v["p3"]; d["deducoes"]["real"]+=v["real"]
        elif t == "custo_variavel": d["custos_variaveis"]["p1"]+=v["p1"]; d["custos_variaveis"]["p2"]+=v["p2"]; d["custos_variaveis"]["p3"]+=v["p3"]; d["custos_variaveis"]["real"]+=v["real"]
        elif t == "despesa_operacional": d["despesas_operacionais"]["p1"]+=v["p1"]; d["despesas_operacionais"]["p2"]+=v["p2"]; d["despesas_operacionais"]["p3"]+=v["p3"]; d["despesas_operacionais"]["real"]+=v["real"]
        elif t == "outras_receitas": d["outras_receitas"]["p1"]+=v["p1"]; d["outras_receitas"]["p2"]+=v["p2"]; d["outras_receitas"]["p3"]+=v["p3"]; d["outras_receitas"]["real"]+=v["real"]
        elif t == "outras_despesas": d["outras_despesas"]["p1"]+=v["p1"]; d["outras_despesas"]["p2"]+=v["p2"]; d["outras_despesas"]["p3"]+=v["p3"]; d["outras_despesas"]["real"]+=v["real"]
        elif t == "investimento": d["investimentos"]["p1"]+=v["p1"]; d["investimentos"]["p2"]+=v["p2"]; d["investimentos"]["p3"]+=v["p3"]; d["investimentos"]["real"]+=v["real"]
        elif t == "emprestimo": d["emprestimos"]["p1"]+=v["p1"]; d["emprestimos"]["p2"]+=v["p2"]; d["emprestimos"]["p3"]+=v["p3"]; d["emprestimos"]["real"]+=v["real"]
        elif t == "distribuicao_lucro": d["distribuicao_lucro"]["p1"]+=v["p1"]; d["distribuicao_lucro"]["p2"]+=v["p2"]; d["distribuicao_lucro"]["p3"]+=v["p3"]; d["distribuicao_lucro"]["real"]+=v["real"]
    for x in ["p1", "p2", "p3", "real"]:
        d["receita_liquida"][x] = d["receita_bruta"][x] - d["deducoes"][x]
        d["margem_contribuicao"][x] = d["receita_liquida"][x] - d["custos_variaveis"][x]
        d["ebitda"][x] = d["margem_contribuicao"][x] - d["despesas_operacionais"][x]
        d["resultado_bruto"][x] = d["ebitda"][x] + d["outras_receitas"][x] - d["outras_despesas"][x] - d["investimentos"][x] - d["emprestimos"][x]
        d["resultado_liquido"][x] = d["resultado_bruto"][x] - d["distribuicao_lucro"][x]
    return d

def consolidar_dados_anual(ano, aplicar_cfo=True):
    meses = {m: {c["nome_conta"]: {"tipo": c["categoria_dre"], "real": 0.0, "p1": 0.0, "p2": 0.0, "p3": 0.0} for c in st.session_state.plano_contas} for m in range(1, 13)}
    for m in range(1, 13):
        meses[m]["📥 Entradas Pendentes"] = {"tipo": "receita", "real": 0.0, "p1": 0.0, "p2": 0.0, "p3": 0.0}; meses[m]["📤 Saídas Pendentes"] = {"tipo": "outras_despesas", "real": 0.0, "p1": 0.0, "p2": 0.0, "p3": 0.0}
    for o in st.session_state.orcamentos:
        try:
            d_orc = datetime.strptime(o["data_ref"], "%Y-%m-%d").date()
            if d_orc.year == ano and o["conta"] in meses[d_orc.month]:
                c_name = o["conta"]
                c_cat = meses[d_orc.month][c_name]["tipo"]
                mult = get_multiplicador(c_cat, c_name, o["data_ref"]) if aplicar_cfo else 1.0
                meses[d_orc.month][c_name]["p1"] += float(o.get("p1", 0.0)) * mult
                meses[d_orc.month][c_name]["p2"] += float(o.get("p2", 0.0)) * mult
                meses[d_orc.month][c_name]["p3"] += float(o.get("p3", 0.0)) * mult
        except: pass
    for l in st.session_state.lancamentos_reais:
        if l.get("ativo", True):
            try:
                d_lanc = datetime.strptime(l["data_real"], "%Y-%m-%d").date()
                if d_lanc.year == ano and l["conta"] in meses[d_lanc.month]: meses[d_lanc.month][l["conta"]]["real"] += float(l.get("valor", 0.0))
            except: pass
    for p in st.session_state.pendencias:
        try:
            d_p = datetime.strptime(p["data"], "%Y-%m-%d").date()
            if d_p.year == ano:
                v_pend = float(p.get("valor", 0.0))
                if p.get("conta") and p["conta"] in meses[d_p.month]: meses[d_p.month][p["conta"]]["real"] += v_pend
                else:
                    if p["tipo"] == "entrada": meses[d_p.month]["📥 Entradas Pendentes"]["real"] += v_pend
                    elif p["tipo"] == "saida": meses[d_p.month]["📤 Saídas Pendentes"]["real"] += v_pend
        except: pass
    return meses

def calcular_dre_anual(meses):
    dre_anual = {m: {k: {"p1": 0.0, "p2": 0.0, "p3": 0.0, "real": 0.0} for k in ["receita_bruta", "deducoes", "receita_liquida", "custos_variaveis", "margem_contribuicao", "despesas_operacionais", "ebitda", "outras_receitas", "outras_despesas", "investimentos", "emprestimos", "resultado_bruto", "distribuicao_lucro", "resultado_liquido"]} for m in range(1, 13)}
    acumulado = {k: {"p1": 0.0, "p2": 0.0, "p3": 0.0, "real": 0.0} for k in dre_anual[1].keys()}
    for m in range(1, 13):
        for conta, v in meses[m].items():
            t = v["tipo"]
            if t == "receita": dre_anual[m]["receita_bruta"]["p1"]+=v["p1"]; dre_anual[m]["receita_bruta"]["p2"]+=v["p2"]; dre_anual[m]["receita_bruta"]["p3"]+=v["p3"]; dre_anual[m]["receita_bruta"]["real"]+=v["real"]
            elif t == "deducao": dre_anual[m]["deducoes"]["p1"]+=v["p1"]; dre_anual[m]["deducoes"]["p2"]+=v["p2"]; dre_anual[m]["deducoes"]["p3"]+=v["p3"]; dre_anual[m]["deducoes"]["real"]+=v["real"]
            elif t == "custo_variavel": dre_anual[m]["custos_variaveis"]["p1"]+=v["p1"]; dre_anual[m]["custos_variaveis"]["p2"]+=v["p2"]; dre_anual[m]["custos_variaveis"]["p3"]+=v["p3"]; dre_anual[m]["custos_variaveis"]["real"]+=v["real"]
            elif t == "despesa_operacional": dre_anual[m]["despesas_operacionais"]["p1"]+=v["p1"]; dre_anual[m]["despesas_operacionais"]["p2"]+=v["p2"]; dre_anual[m]["despesas_operacionais"]["p3"]+=v["p3"]; dre_anual[m]["despesas_operacionais"]["real"]+=v["real"]
            elif t == "outras_receitas": dre_anual[m]["outras_receitas"]["p1"]+=v["p1"]; dre_anual[m]["outras_receitas"]["p2"]+=v["p2"]; dre_anual[m]["outras_receitas"]["p3"]+=v["p3"]; dre_anual[m]["outras_receitas"]["real"]+=v["real"]
            elif t == "outras_despesas": dre_anual[m]["outras_despesas"]["p1"]+=v["p1"]; dre_anual[m]["outras_despesas"]["p2"]+=v["p2"]; dre_anual[m]["outras_despesas"]["p3"]+=v["p3"]; dre_anual[m]["outras_despesas"]["real"]+=v["real"]
            elif t == "investimento": dre_anual[m]["investimentos"]["p1"]+=v["p1"]; dre_anual[m]["investimentos"]["p2"]+=v["p2"]; dre_anual[m]["investimentos"]["p3"]+=v["p3"]; dre_anual[m]["investimentos"]["real"]+=v["real"]
            elif t == "emprestimo": dre_anual[m]["emprestimos"]["p1"]+=v["p1"]; dre_anual[m]["emprestimos"]["p2"]+=v["p2"]; dre_anual[m]["emprestimos"]["p3"]+=v["p3"]; dre_anual[m]["emprestimos"]["real"]+=v["real"]
            elif t == "distribuicao_lucro": dre_anual[m]["distribuicao_lucro"]["p1"]+=v["p1"]; dre_anual[m]["distribuicao_lucro"]["p2"]+=v["p2"]; dre_anual[m]["distribuicao_lucro"]["p3"]+=v["p3"]; dre_anual[m]["distribuicao_lucro"]["real"]+=v["real"]
        for x in ["p1", "p2", "p3", "real"]:
            dre_anual[m]["receita_liquida"][x] = dre_anual[m]["receita_bruta"][x] - dre_anual[m]["deducoes"][x]
            dre_anual[m]["margem_contribuicao"][x] = dre_anual[m]["receita_liquida"][x] - dre_anual[m]["custos_variaveis"][x]
            dre_anual[m]["ebitda"][x] = dre_anual[m]["margem_contribuicao"][x] - dre_anual[m]["despesas_operacionais"][x]
            dre_anual[m]["resultado_bruto"][x] = dre_anual[m]["ebitda"][x] + dre_anual[m]["outras_receitas"][x] - dre_anual[m]["outras_despesas"][x] - dre_anual[m]["investimentos"][x] - dre_anual[m]["emprestimos"][x]
            dre_anual[m]["resultado_liquido"][x] = dre_anual[m]["resultado_bruto"][x] - dre_anual[m]["distribuicao_lucro"][x]
        for k in acumulado.keys():
            acumulado[k]["p1"]+=dre_anual[m][k]["p1"]; acumulado[k]["p2"]+=dre_anual[m][k]["p2"]; acumulado[k]["p3"]+=dre_anual[m][k]["p3"]; acumulado[k]["real"]+=dre_anual[m][k]["real"]
    return dre_anual, acumulado

def calcular_resultado_all_time():
    receitas, saidas = 0.0, 0.0
    mapa_tipos = {c["nome_conta"]: c["categoria_dre"] for c in st.session_state.plano_contas}
    for l in st.session_state.lancamentos_reais:
        if not l.get("ativo", True): continue
        tipo = mapa_tipos.get(l.get("conta"))
        val = float(l.get("valor", 0.0))
        if tipo in ["receita", "outras_receitas"]: receitas += val
        elif tipo in ["deducao", "custo_variavel", "despesa_operacional", "outras_despesas", "investimento", "emprestimo", "distribuicao_lucro"]: saidas += val
    for p in st.session_state.pendencias:
        val = float(p.get("valor", 0.0))
        if p.get("tipo") == "entrada": receitas += val
        elif p.get("tipo") == "saida": saidas += val
    return (receitas - saidas) + st.session_state.get("saldo_inicial", 0.0)

def calcular_saldo_historico_ate(data_limite):
    receitas, saidas = 0.0, 0.0
    mapa_tipos = {c["nome_conta"]: c["categoria_dre"] for c in st.session_state.plano_contas}
    for l in st.session_state.lancamentos_reais:
        if not l.get("ativo", True): continue
        try:
            if datetime.strptime(l["data_real"], "%Y-%m-%d").date() < data_limite:
                tipo = mapa_tipos.get(l.get("conta"))
                val = float(l.get("valor", 0.0))
                if tipo in ["receita", "outras_receitas"]: receitas += val
                elif tipo in ["deducao", "custo_variavel", "despesa_operacional", "outras_despesas", "investimento", "emprestimo", "distribuicao_lucro"]: saidas += val
        except: pass
    for p in st.session_state.pendencias:
        try:
            if datetime.strptime(p["data"], "%Y-%m-%d").date() < data_limite:
                val = float(p.get("valor", 0.0))
                if p.get("tipo") == "entrada": receitas += val
                elif p.get("tipo") == "saida": saidas += val
        except: pass
    return (receitas - saidas) + st.session_state.get("saldo_inicial", 0.0)

TIPO_MAPEAMENTO = {"Receita Bruta": "receita", "Deduções": "deducao", "Custos Variáveis": "custo_variavel", "Despesas Operacionais": "despesa_operacional", "Outras Receitas": "outras_receitas", "Outras Despesas": "outras_despesas", "Investimentos": "investimento", "Empréstimos": "emprestimo", "Distribuição de Lucro": "distribuicao_lucro"}

st.markdown('<div class="notranslate" translate="no">', unsafe_allow_html=True)

if st.session_state.logo_b64: logo_element = f"<img src='data:image/png;base64,{st.session_state.logo_b64}' style='max-height: 35px; width: auto; object-fit: contain; border-radius: 5px;'>"
else: logo_element = f"<div style='color: {st.session_state.color_primary}; font-weight: 800; font-size: 20px; letter-spacing: -0.5px;'>LOGO</div>"

# CABEÇALHO MULTI-EMPRESA
st.markdown(f"<div class='notranslate' style='background-color: {st.session_state.color_primary}; border-radius: 16px; padding: 12px 25px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);'><div style='display: flex; align-items: center; gap: 15px;'><div style='background-color: white; padding: 5px 15px; border-radius: 12px; display: flex; align-items: center; justify-content: center; min-height: 45px;'>{logo_element}</div><div><h2 style='margin: 0; font-size: 19px; color: #FFFFFF; font-weight: 600; letter-spacing: -0.3px;'>DRE por Fluxo de Caixa</h2><p style='margin: 0; font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 2px;'>Painel Executivo Multi-Empresas</p></div></div></div>", unsafe_allow_html=True)

c_filtro1, c_filtro2 = st.columns([7, 3])
with c_filtro2:
    opcoes_empresa = {"TODAS": "🌐 Consolidado (Todas as Empresas)"}
    for k, v in st.session_state.db["empresas"].items():
        if v.get("ativo", True): opcoes_empresa[k] = f"🏢 {v['nome']}"
    sel_empresa = st.selectbox("Ambiente Ativo", list(opcoes_empresa.keys()), format_func=lambda x: opcoes_empresa[x], label_visibility="collapsed")
    if sel_empresa != st.session_state.empresa_selecionada:
        st.session_state.empresa_selecionada = sel_empresa
        if sel_empresa == "TODAS" and st.session_state.pagina_atual not in ["DASH", "DRE RESUMIDO", "DRE ANUAL"]: st.session_state.pagina_atual = "DASH"
        st.rerun()

st.markdown("<div id='nav-anchor' style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# MENU RESTRITO SE 'TODAS'
if st.session_state.empresa_selecionada == "TODAS":
    cols_nav = st.columns(3)
    nav_items = [("📊 Dash", "DASH"), ("📋 DRE 4 Semanas", "DRE RESUMIDO"), ("📆 DRE Anual", "DRE ANUAL")]
else:
    cols_nav = st.columns(8)
    nav_items = [("📊 Dash", "DASH"), ("📋 DRE 4 Semanas", "DRE RESUMIDO"), ("📆 DRE Anual", "DRE ANUAL"), ("🎯 Planejamento", "PLANEJAMENTO"), ("💸 Realizado", "REALIZADO"), ("🏦 Conciliação", "CONCILIACAO"), ("💼 Ação CFO", "ACAO_CFO"), ("⚙️ Cadastro", "CADASTRO")]

for i, (label, val) in enumerate(nav_items):
    with cols_nav[i]:
        if st.button(label, type="primary" if st.session_state.pagina_atual == val else "secondary", use_container_width=True, key=f"nav_btn_top_{val}"): st.session_state.pagina_atual = val; st.rerun()

dados_consolidados = consolidar_dados()
dre_data = calcular_dre(dados_consolidados)

# ALERTA DE 80% GLOBAL
alerta_80_html = ""
for conta, dados in dados_consolidados.items():
    if dados["tipo"] in ["deducao", "custo_variavel", "despesa_operacional", "outras_despesas", "investimento", "emprestimo", "distribuicao_lucro"]:
        if dados["p1"] > 0 and (dados["real"] >= dados["p1"] * 0.8) and (dados["real"] <= dados["p1"]):
            alerta_80_html += f"<span style='background-color:#FEF3C7; color:#D97706; padding:4px 8px; border-radius:6px; font-size:11px; font-weight:700; border:1px solid #FCD34D; margin-right:8px;'>⚠️ {conta} atingiu {((dados['real']/dados['p1'])*100):.1f}% do orçado</span>"

if alerta_80_html:
    st.markdown(f"<div style='margin-bottom:15px;'>{alerta_80_html}</div>", unsafe_allow_html=True)

if st.session_state.pagina_atual == "DASH":
    resultado_liquido_real_periodo = dre_data['resultado_liquido']['real']
    resultado_liquido_historico = calcular_resultado_all_time()
    saldo_total_bancos = sum([float(b.get("saldo", 0.0)) for b in st.session_state.bancos])
    check_valor = saldo_total_bancos - resultado_liquido_historico
    is_conciliado = abs(check_valor) < 0.01 
    
    if is_conciliado: check_color_border, check_color_text, check_valor_display = "#046C4E", "#046C4E", formatar_moeda(0)
    elif check_valor > 0: check_color_border, check_color_text, check_valor_display = "#2B6CB0", "#2B6CB0", f"+ {formatar_moeda(check_valor)}"
    else: check_color_border, check_color_text, check_valor_display = "#C53030", "#C53030", f"- {formatar_moeda(abs(check_valor))}"
    
    col_kpis, col_dates = st.columns([7.5, 2.5])
    with col_kpis:
        st.markdown(f"<div class='notranslate' style='display: flex; gap: 15px;'><div style='flex: 1; background-color: white; padding: 20px; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>Res. Líquido (Período)</div><div style='font-size: 22px; font-weight: 800; color: {st.session_state.color_text};'>{formatar_moeda(resultado_liquido_real_periodo)}</div></div><div style='flex: 1; background-color: white; padding: 20px; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>Saldo Bancos (Real)</div><div style='font-size: 22px; font-weight: 800; color: {st.session_state.color_text};'>{formatar_moeda(saldo_total_bancos)}</div></div><div style='flex: 1; background-color: white; padding: 20px; border-radius: 16px; border: 1px solid {check_color_border}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>Check Auditoria</div><div style='font-size: 22px; font-weight: 800; color: {check_color_text}; margin-bottom: 4px;'>{check_valor_display}</div></div></div>", unsafe_allow_html=True)
    with col_dates:
        st.markdown("<div style='background-color: white; padding: 15px 20px; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%; display: flex; flex-direction: column; justify-content: center;'>", unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        with d1: st.date_input("📅 Inicial", key="data_inicio", format="DD/MM/YYYY")
        with d2: st.date_input("📅 Final", key="data_fim", format="DD/MM/YYYY")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Detalhe Bancos "TODAS"
    if st.session_state.empresa_selecionada == "TODAS" and st.session_state.bancos:
        bancos_html = "<div style='display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 15px;'>"
        for b in st.session_state.bancos:
            bancos_html += f"<div style='min-width: 200px; background-color: white; padding: 12px; border-radius: 12px; border: 1px solid #E2E8F0;'><div style='font-size: 10px; color: #64748B; font-weight: 700;'>{b['empresa']}</div><div style='font-size: 13px; font-weight: 600; color: #1E293B;'>{b['nome']}</div><div style='font-size: 16px; font-weight: 800; color: #0F172A; margin-top: 4px;'>{formatar_moeda(b['saldo'])}</div></div>"
        bancos_html += "</div>"
        st.markdown("<div class='saas-section-title' style='margin-bottom: 10px;'>Saldos por Empresa</div>", unsafe_allow_html=True)
        st.markdown(bancos_html, unsafe_allow_html=True)

    despesas_totais = sum(v["real"] for v in dados_consolidados.values() if v["tipo"] in ["deducao", "custo_variavel", "despesa_operacional", "outras_despesas", "investimento", "emprestimo", "distribuicao_lucro"] and v["real"] > 0)
    top_5_ofensores = sorted([{"conta": c, "valor": v["real"]} for c, v in dados_consolidados.items() if v["tipo"] in ["deducao", "custo_variavel", "despesa_operacional", "outras_despesas", "investimento", "emprestimo", "distribuicao_lucro"] and v["real"] > 0], key=lambda x: x["valor"], reverse=True)[:5]
    ofensores_html = "<div style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>"
    if not top_5_ofensores: ofensores_html += "<div style='color: #64748B; font-size: 13px; text-align: center; padding: 10px;'>Sem dados no período.</div>"
    else:
        for i, of in enumerate(top_5_ofensores):
            pct = (of['valor'] / despesas_totais) * 100 if despesas_totais > 0 else 0
            cb = "#E53E3E" if i == 0 else "#DD6B20" if i == 1 else "#D69E2E" if i == 2 else "#4A5568"
            ofensores_html += f"<div style='margin-bottom: 15px;'><div style='display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #1E293B; margin-bottom: 6px;'><span>{i+1}. {of['conta']}</span><span style='color: {cb};'>{formatar_moeda(of['valor'])} ({pct:.1f}%)</span></div><div style='width: 100%; background-color: #F1F5F9; border-radius: 4px; height: 8px;'><div style='width: {min(pct, 100)}%; background-color: {cb}; border-radius: 4px; height: 8px;'></div></div></div>"
    ofensores_html += "</div>"

    ano_proj = date.today().year
    mapa_t = {c["nome_conta"]: c["categoria_dre"] for c in st.session_state.plano_contas}
    evs = []
    for l in st.session_state.lancamentos_reais:
        if l.get("ativo", True):
            try:
                t = mapa_t.get(l["conta"]); v = float(l.get("valor", 0.0))
                if t in ["receita", "outras_receitas"]: evs.append({"d": datetime.strptime(l["data_real"], "%Y-%m-%d").date(), "v": v})
                elif t: evs.append({"d": datetime.strptime(l["data_real"], "%Y-%m-%d").date(), "v": -v})
            except: pass
    for p in st.session_state.pendencias:
        try:
            v = float(p.get("valor", 0.0))
            if p["tipo"] == "entrada": evs.append({"d": datetime.strptime(p["data"], "%Y-%m-%d").date(), "v": v})
            elif p["tipo"] == "saida": evs.append({"d": datetime.strptime(p["data"], "%Y-%m-%d").date(), "v": -v})
        except: pass
    h_fc = date.today()
    for o in st.session_state.orcamentos:
        if not o.get("efetivado"):
            try:
                d = datetime.strptime(o["data_ref"], "%Y-%m-%d").date()
                if d > h_fc:
                    t = mapa_t.get(o["conta"]); v = float(o.get("p1", 0.0))
                    if t in ["receita", "outras_receitas"]: evs.append({"d": d, "v": v})
                    elif t: evs.append({"d": d, "v": -v})
            except: pass
    delta_fc = {}
    for ev in evs: delta_fc[ev["d"]] = delta_fc.get(ev["d"], 0.0) + ev["v"]
    
    d_i = date(ano_proj, 1, 1)
    s_fc = st.session_state.get("saldo_inicial", 0.0)
    for d, v in delta_fc.items():
        if d < d_i: s_fc += v
    semanas_fc = {}
    while d_i <= date(ano_proj, 12, 31):
        s_fc += delta_fc.get(d_i, 0.0)
        y, w, _ = d_i.isocalendar()
        if (y, w) not in semanas_fc: semanas_fc[(y, w)] = {"i": d_i - timedelta(days=d_i.weekday()), "f": d_i - timedelta(days=d_i.weekday()) + timedelta(days=6), "min": s_fc}
        else:
            if s_fc < semanas_fc[(y, w)]["min"]: semanas_fc[(y, w)]["min"] = s_fc
        d_i += timedelta(days=1)

    top_5_f = sorted([v for k, v in semanas_fc.items() if v["i"].year == ano_proj or v["f"].year == ano_proj], key=lambda x: x["min"])[:5]
    m_pt = ["", "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    fc_html = ""
    if not top_5_f: fc_html += "<div style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; text-align: center; color: #64748B;'>Sem projeção.</div>"
    else:
        for i, fc in enumerate(top_5_f):
            di, df, val = fc["i"], fc["f"], fc["min"]
            sd = f"{di.day:02d} a {df.day:02d} {m_pt[di.month]}" if di.month == df.month else f"{di.day:02d} {m_pt[di.month]} a {df.day:02d} {m_pt[df.month]}"
            if val < 0: bg_card = "#FFF5F5"; border_card = "#FED7D7"; cor_icon = "#C53030"; cor_txt = "#742A2A"; cor_val = "#C53030"; risco = "Risco Crítico (Falta de Capital)"
            elif val < 5000: bg_card = "#FFFFF0"; border_card = "#FEFCBF"; cor_icon = "#D69E2E"; cor_txt = "#744210"; cor_val = "#D69E2E"; risco = "Atenção (Caixa Baixo)"
            else: bg_card = "#F0FDF4"; border_card = "#BBF7D0"; cor_icon = "#166534"; cor_txt = "#14532D"; cor_val = "#166534"; risco = "Confortável (Ponto mais baixo)"
            fc_html += f"<div style='display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background-color: {bg_card}; border: 1px solid {border_card}; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);'><div style='display: flex; align-items: center; gap: 14px;'><div style='background-color: {cor_icon}; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{i+1}</div><div><div style='font-size: 13.5px; font-weight: 800; color: {cor_txt};'>Semana {sd}</div><div style='font-size: 11px; font-weight: 600; color: {cor_icon}; margin-top: 1px;'>{risco}</div></div></div><div style='font-size: 17px; font-weight: 900; color: {cor_val}; letter-spacing: -0.5px;'>{formatar_moeda(val)}</div></div>"

    rl_r, eb_r, rl_liq, mc_r, dop_r = dre_data['receita_liquida']['real'], dre_data['ebitda']['real'], dre_data['resultado_liquido']['real'], dre_data['margem_contribuicao']['real'], dre_data['despesas_operacionais']['real']
    m_eb = (eb_r / rl_r * 100) if rl_r > 0 else 0.0
    m_lq = (rl_liq / rl_r * 100) if rl_r > 0 else 0.0
    imc = (mc_r / rl_r) if rl_r > 0 else 0.0
    bep = (dop_r / imc) if imc > 0 else 0.0
    c_eb = "#38A169" if m_eb >= 15 else "#DD6B20" if m_eb > 0 else "#E53E3E"
    c_lq = "#38A169" if m_lq >= 10 else "#DD6B20" if m_lq > 0 else "#E53E3E"
    
    ind_html = f"<div style='display: flex; gap: 10px; margin-bottom: 15px;'><div style='flex: 1; background-color: white; border: 1px solid #D1E0FF; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 2px;'>Margem EBITDA</div><div style='font-size: 16px; font-weight: 800; color: {c_eb};'>{m_eb:.1f}%</div></div><div style='flex: 1; background-color: white; border: 1px solid #D1E0FF; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 2px;'>Margem Líquida</div><div style='font-size: 16px; font-weight: 800; color: {c_lq};'>{m_lq:.1f}%</div></div><div style='flex: 1; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 2px;'>Ponto Equilíbrio</div><div style='font-size: 16px; font-weight: 800; color: #1E293B;'>{formatar_moeda(bep)}</div><div style='font-size: 9px; color: #94A3B8; margin-top: 4px; line-height: 1.2;'>Faturamento mínimo p/ cobrir as Despesas Fixas.</div></div></div>"

    if st.session_state.empresa_selecionada == "TODAS":
        p_cards = "<div style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); text-align: center; color: #64748B; margin-bottom: 25px;'>Monitor de Pendências indisponível na visão Multi-Empresa.</div>"
    else:
        pi = [p for p in st.session_state.pendencias if p["tipo"] == "entrada" and not p.get("conta")]
        po = [p for p in st.session_state.pendencias if p["tipo"] == "saida" and not p.get("conta")]
        rg = st.session_state.get("regras_pendencia", {"tipo": "Quantidade", "limite": 5})
        tr, lr = rg.get("tipo", "Quantidade"), int(rg.get("limite", 5))
        def cps(pl, tr, lr):
            if not pl: return "Tudo em dia", "#046C4E", "#DEF7EC", "#046C4E"
            if tr == "Quantidade":
                if len(pl) > lr: return f"Atenção: {len(pl)} itens", "#9B1C1C", "#FDE8E8", "#E53E3E"
                else: return f"No limite: {len(pl)} itens", "#046C4E", "#DEF7EC", "#38A169"
            else:
                hoje, max_dias = date.today(), 0
                for p in pl:
                    try:
                        dias = (hoje - datetime.strptime(p["data"], "%Y-%m-%d").date()).days
                        if dias > max_dias: max_dias = dias
                    except: pass
                if max_dias > lr: return f"Atrasado: {max_dias} dias", "#9B1C1C", "#FDE8E8", "#E53E3E"
                else: return f"No prazo: {max_dias} dias", "#046C4E", "#DEF7EC", "#38A169"

        sit, sic, sib, vic = cps(pi, tr, lr)
        sot, soc, sob, voc = cps(po, tr, lr)
        vit, vot = sum(float(p.get("valor", 0.0)) for p in pi), sum(float(p.get("valor", 0.0)) for p in po)
        p_cards = f"<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;'><div style='background-color: white; border: 2px solid {sic}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); position: relative;'><div style='position: absolute; top: -10px; right: 10px; background-color: {sib}; color: {sic}; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 12px; border: 1px solid {sic};'>{sit}</div><div style='font-size: 11px; font-weight: 700; color: {sic}; text-transform: uppercase; margin-bottom: 4px;'>Pendências: Entradas</div><div style='font-size: 22px; font-weight: 800; color: {vic};'>{formatar_moeda(vit)}</div></div><div style='background-color: white; border: 2px solid {soc}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); position: relative;'><div style='position: absolute; top: -10px; right: 10px; background-color: {sob}; color: {soc}; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 12px; border: 1px solid {soc};'>{sot}</div><div style='font-size: 11px; font-weight: 700; color: {soc}; text-transform: uppercase; margin-bottom: 4px;'>Pendências: Saídas</div><div style='font-size: 22px; font-weight: 800; color: {voc};'>{formatar_moeda(vot)}</div></div></div>"
    
    col_esq, col_dir = st.columns([5, 5], gap="large")
    with col_esq:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>⚠️</span> Monitor de Pendências Não Identificadas</div>", unsafe_allow_html=True)
        st.markdown(p_cards, unsafe_allow_html=True)

        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>🎯</span> Cenários de Caixa (Projetado vs Realizado)</div>", unsafe_allow_html=True)
        c1_v, c2_v, c3_v, r_v = dre_data['resultado_liquido']['p1'], dre_data['resultado_liquido']['p2'], dre_data['resultado_liquido']['p3'], dre_data['resultado_liquido']['real']
        in_p1, in_r = dre_data['receita_bruta']['p1'] + dre_data['outras_receitas']['p1'], dre_data['receita_bruta']['real'] + dre_data['outras_receitas']['real']
        out_p1 = sum([dre_data[k]['p1'] for k in ['deducoes', 'custos_variaveis', 'despesas_operacionais', 'outras_despesas', 'investimentos', 'emprestimos', 'distribuicao_lucro']])
        out_r = sum([dre_data[k]['real'] for k in ['deducoes', 'custos_variaveis', 'despesas_operacionais', 'outras_despesas', 'investimentos', 'emprestimos', 'distribuicao_lucro']])
        
        if r_v >= c3_v and c3_v > 0: stx, sc, sbg = "Superou Cenário 3! 🚀", "#046C4E", "#DEF7EC"
        elif r_v >= c2_v and c2_v > 0: stx, sc, sbg = "Superou Cenário 2! ⭐", "#046C4E", "#DEF7EC"
        elif r_v >= c1_v and c1_v > 0: stx, sc, sbg = "Atingiu Cenário 1! ✅", "#046C4E", "#DEF7EC"
        elif r_v < c1_v: stx, sc, sbg = "Abaixo do C1 ⚠️", "#9B1C1C", "#FDE8E8"
        else: stx, sc, sbg = "Aguardando dados", "#718096", "#F1F5F9"
        
        cfg_c2, cfg_c3 = st.session_state.cenarios_cfg.get("c2", 30.0), st.session_state.cenarios_cfg.get("c3", 70.0)

        def bd(ip, ir, op, orr, ir_t=False): return f"<div class='kpi-details' style='margin-top: 12px; padding-top: 12px; border-top: 1px dashed #E2E8F0;'><div style='display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;'><span style='color: #64748B;'>{'Entrada Prevista:' if ir_t else 'Entrada Projetada:'}</span> <span style='font-weight: 700; color: #3182CE;'>{formatar_moeda(ip)}</span></div><div style='display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;'><span style='color: #64748B;'>Entrada Realizada:</span> <span style='font-weight: 700; color: #38A169;'>{formatar_moeda(ir)}</span></div><div style='height: 4px;'></div><div style='display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;'><span style='color: #64748B;'>{'Saída Prevista:' if ir_t else 'Saída Projetada:'}</span> <span style='font-weight: 700; color: #DD6B20;'>{formatar_moeda(op)}</span></div><div style='display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;'><span style='color: #64748B;'>Saída Realizada:</span> <span style='font-weight: 700; color: #E53E3E;'>{formatar_moeda(orr)}</span></div></div>"

        sc_html = "<style>details.dash-card summary::-webkit-details-marker {display: none;} details.dash-card summary {list-style: none; outline: none;} details.dash-card:hover {background-color: #F8FAFC !important;} details.dash-card[open] summary span.arrow {transform: rotate(180deg);} span.arrow {display: inline-block; transition: transform 0.2s;}</style><div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;'>"
        sc_html += f"<details class='dash-card' style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); cursor: pointer; transition: background-color 0.2s;'><summary><div style='font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 4px;'>Cenário 1 (Base) <span class='arrow' style='float:right; color: #CBD5E1; font-size: 10px; margin-top: 2px;'>▼</span></div><div style='font-size: 22px; font-weight: 800; color: #1E293B;'>{formatar_moeda(c1_v)}</div></summary>{bd(in_p1, in_r, out_p1, out_r, False)}</details>"
        sc_html += f"<details class='dash-card' style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); cursor: pointer; transition: background-color 0.2s;'><summary><div style='font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 4px;'>Cenário 2 (+{cfg_c2:g}%) <span class='arrow' style='float:right; color: #CBD5E1; font-size: 10px; margin-top: 2px;'>▼</span></div><div style='font-size: 22px; font-weight: 800; color: #1E293B;'>{formatar_moeda(c2_v)}</div></summary>{bd(dre_data['receita_bruta']['p2'] + dre_data['outras_receitas']['p2'], in_r, out_p1, out_r, False)}</details>"
        sc_html += f"<details class='dash-card' style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); cursor: pointer; transition: background-color 0.2s;'><summary><div style='font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 4px;'>Cenário 3 (+{cfg_c3:g}%) <span class='arrow' style='float:right; color: #CBD5E1; font-size: 10px; margin-top: 2px;'>▼</span></div><div style='font-size: 22px; font-weight: 800; color: #1E293B;'>{formatar_moeda(c3_v)}</div></summary>{bd(dre_data['receita_bruta']['p3'] + dre_data['outras_receitas']['p3'], in_r, out_p1, out_r, False)}</details>"
        sc_html += f"<details class='dash-card' style='background-color: white; border: 2px solid {sc}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); position: relative; cursor: pointer; transition: background-color 0.2s;'><summary><div style='position: absolute; top: -10px; right: 10px; background-color: {sbg}; color: {sc}; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 12px; border: 1px solid {sc};'>{stx}</div><div style='font-size: 11px; font-weight: 800; color: {sc}; text-transform: uppercase; margin-bottom: 4px;'>Realizado <span class='arrow' style='float:right; color: {sc}; font-size: 10px; margin-top: 2px; opacity: 0.7;'>▼</span></div><div style='font-size: 22px; font-weight: 900; color: {sc};'>{formatar_moeda(r_v)}</div></summary>{bd(in_p1, in_r, out_p1, out_r, True)}</details></div>"
        st.markdown(sc_html, unsafe_allow_html=True)

    with col_dir:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>⚡</span> Eficiência e Break-Even</div>", unsafe_allow_html=True)
        st.markdown(ind_html, unsafe_allow_html=True)
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>📉</span> Top 5 Ofensores do Caixa</div>", unsafe_allow_html=True)
        st.markdown(ofensores_html, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)
    c_rad1, c_rad2 = st.columns([5, 5], gap="large")

    with c_rad1:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>📡</span> Radar Fundo de Caixa (Risco Anual)</div>", unsafe_allow_html=True)
        st.markdown(fc_html, unsafe_allow_html=True)

    with c_rad2:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>📊</span> Mapa Comparativo (100% da Receita)</div>", unsafe_allow_html=True)
        dg = []
        for v, n, c in [(dre_data['deducoes']['real'], "Deduções", "#E53E3E"), (dre_data['custos_variaveis']['real'], "Custos Variáveis", "#DD6B20"), (dre_data['despesas_operacionais']['real'], "Desp. Operacionais", "#3182CE"), (dre_data['outras_despesas']['real'], "Outras Despesas", "#805AD5"), (dre_data['investimentos']['real'], "Investimentos", "#319795"), (dre_data['emprestimos']['real'], "Empréstimos", "#718096"), (dre_data['distribuicao_lucro']['real'], "Dist. Lucros", "#D69E2E"), (dre_data['resultado_liquido']['real'] if dre_data['resultado_liquido']['real'] > 0 else 0, "Lucro Retido", "#38A169")]:
            if v > 0: dg.append({"value": v, "name": n, "itemStyle": {"color": c}})
        rt = dre_data['receita_bruta']['real'] + dre_data['outras_receitas']['real']
        if rt == 0 or len(dg) == 0: st.markdown("""<div style="background-color: white; border-radius: 16px; border: 1px solid #D1E0FF; height: 120px; display: flex; align-items: center; justify-content: center; flex-direction: column; color: #A0AEC0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);"><span style="font-weight: 500; font-size: 13px;">Sem dados suficientes.</span></div>""", unsafe_allow_html=True)
        else:
            pie_html = "<!DOCTYPE html><html><head><meta charset='utf-8'><script src='https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'></script><style>body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background: transparent; } .chart-container { background-color: white; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); padding: 15px; height: 350px; } #main { width: 100%; height: 100%; }</style></head><body><div class='chart-container'><div id='main'></div></div><script>var chartDom = document.getElementById('main'); var myChart = echarts.init(chartDom); var option = {tooltip: { trigger: 'item', backgroundColor: 'rgba(255, 255, 255, 0.95)', borderColor: '#D1E0FF', textStyle: { color: '#1E293B' }, formatter: function(params) { let totalRec = __RT__; let pct = totalRec > 0 ? ((params.value / totalRec) * 100).toFixed(1) : 0; let val = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(params.value); return `<div style='font-weight:700;margin-bottom:6px;border-bottom:1px solid #E2E8F0;padding-bottom:4px;'>${params.marker} ${params.name}</div><div style='font-weight:800;color:#0F172A;font-size:15px;'>${val}</div><div style='color:#64748B;font-size:12px;margin-top:2px;'>Representa <b>${pct}%</b> da Receita</div>`;}},legend: { orient: 'vertical', right: '2%', top: 'center', textStyle: { color: '#4A5568', fontSize: 12, fontFamily: 'Inter' }, itemGap: 15 },series: [{ name: 'Alocação', type: 'pie', radius: ['40%', '70%'], center: ['35%', '50%'], avoidLabelOverlap: true, itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 3 },label: { show: true, formatter: function(params) { let totalRec = __RT__; let pct = totalRec > 0 ? ((params.value / totalRec) * 100).toFixed(1) : 0; return params.name + '\\n' + pct + '%'; }, fontSize: 11, fontWeight: 'bold', color: '#4A5568' },labelLine: { show: true, length: 10, length2: 15 }, emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.1)' } }, data: __DG__}]}; option && myChart.setOption(option); window.addEventListener('resize', myChart.resize);</script></body></html>"
            pie_html = pie_html.replace("__RT__", str(rt)).replace("__DG__", json.dumps(dg))
            components.html(pie_html, height=380)

    st.markdown("<hr style='border-color: #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)
    c_past, c_next = st.columns([5, 5], gap="large")

    with c_past:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>⬅️</span> Radar Semanas Passadas (Realizado)</div>", unsafe_allow_html=True)
        p_html = "<div style='display: flex; flex-direction: column; gap: 10px;'>"
        for i in range(4, -1, -1):
            dw_i = date.today() - timedelta(days=date.today().weekday()) - timedelta(weeks=i)
            dw_f = dw_i + timedelta(days=6)
            ds = calcular_dre(consolidar_dados_periodo(dw_i, dw_f, aplicar_cfo=False))
            inp, inr = ds['receita_bruta']['p1'] + ds['outras_receitas']['p1'], ds['receita_bruta']['real'] + ds['outras_receitas']['real']
            oup = sum(ds[k]['p1'] for k in ['deducoes', 'custos_variaveis', 'despesas_operacionais', 'outras_despesas', 'investimentos', 'emprestimos', 'distribuicao_lucro'])
            our = sum(ds[k]['real'] for k in ['deducoes', 'custos_variaveis', 'despesas_operacionais', 'outras_despesas', 'investimentos', 'emprestimos', 'distribuicao_lucro'])
            res_r = inr - our
            bg_r = "#DEF7EC" if res_r >= 0 else "#FDE8E8"
            c_r = "#046C4E" if res_r >= 0 else "#9B1C1C"
            p_html += f"<div style='display: flex; justify-content: space-between; align-items: center; background-color: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);'><div><div style='font-size: 13px; font-weight: 700; color: #1E293B;'>{dw_i.strftime('%d/%m')} a {dw_f.strftime('%d/%m')}</div><div style='font-size: 10px; color: #94A3B8; margin-top: 2px; font-weight: 500;'>Real vs Proj</div></div><div style='text-align: right; margin-right: 15px;'><div style='font-size: 11px; color: #64748B; font-weight: 600;'>IN: <span style='color:#38A169;'>{formatar_moeda(inr)}</span> <span style='font-size:9.5px; color:#CBD5E1; font-weight: 500;'>({formatar_moeda(inp)})</span></div><div style='font-size: 11px; color: #64748B; font-weight: 600; margin-top: 2px;'>OUT: <span style='color:#E53E3E;'>{formatar_moeda(our)}</span> <span style='font-size:9.5px; color:#CBD5E1; font-weight: 500;'>({formatar_moeda(oup)})</span></div></div><div><div style='background-color: {bg_r}; color: {c_r}; padding: 6px 12px; border-radius: 20px; font-weight: 800; font-size: 13px; min-width: 90px; text-align: center;'>{formatar_moeda(res_r)}</div></div></div>"
        p_html += "</div>"
        st.markdown(p_html, unsafe_allow_html=True)

    with c_next:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>➡️</span> Radar Próximas Semanas (Projetado)</div>", unsafe_allow_html=True)
        n_html = "<div style='display: flex; flex-direction: column; gap: 10px;'>"
        for i in range(1, 6):
            dw_i = date.today() - timedelta(days=date.today().weekday()) + timedelta(weeks=i)
            dw_f = dw_i + timedelta(days=6)
            ds = calcular_dre(consolidar_dados_periodo(dw_i, dw_f, aplicar_cfo=True))
            inp = ds['receita_bruta']['p1'] + ds['outras_receitas']['p1']
            oup = sum(ds[k]['p1'] for k in ['deducoes', 'custos_variaveis', 'despesas_operacionais', 'outras_despesas', 'investimentos', 'emprestimos', 'distribuicao_lucro'])
            res_p = inp - oup
            bg_p = "#DEF7EC" if res_p >= 0 else "#FDE8E8"
            c_p = "#046C4E" if res_p >= 0 else "#9B1C1C"
            n_html += f"<div style='display: flex; justify-content: space-between; align-items: center; background-color: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);'><div><div style='font-size: 13px; font-weight: 700; color: #1E293B;'>{dw_i.strftime('%d/%m')} a {dw_f.strftime('%d/%m')}</div><div style='font-size: 10px; color: #94A3B8; margin-top: 2px; font-weight: 500;'>Projetado</div></div><div style='text-align: right; margin-right: 15px;'><div style='font-size: 11px; color: #64748B; font-weight: 600;'>IN: <span style='color:#3182CE;'>{formatar_moeda(inp)}</span></div><div style='font-size: 11px; color: #64748B; font-weight: 600; margin-top: 2px;'>OUT: <span style='color:#DD6B20;'>{formatar_moeda(oup)}</span></div></div><div><div style='background-color: {bg_p}; color: {c_p}; padding: 6px 12px; border-radius: 20px; font-weight: 800; font-size: 13px; min-width: 90px; text-align: center;'>{formatar_moeda(res_p)}</div></div></div>"
        n_html += "</div>"
        st.markdown(n_html, unsafe_allow_html=True)
        
    st.markdown("<hr style='border-color: #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)
    c_ch1, c_ch2 = st.columns([5, 5], gap="large")

    with c_ch1:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>📊</span> Cascata do DRE (Realizado)</div>", unsafe_allow_html=True)
        v_rec = dre_data['receita_bruta']['real']
        v_ded = dre_data['deducoes']['real']
        v_cv = dre_data['custos_variaveis']['real']
        v_dop = dre_data['despesas_operacionais']['real']
        v_or = dre_data['outras_receitas']['real']
        v_od = dre_data['outras_despesas']['real']
        v_inv = dre_data['investimentos']['real']
        v_emp = dre_data['emprestimos']['real']
        v_dl = dre_data['distribuicao_lucro']['real']
        v_res = dre_data['resultado_liquido']['real']

        bs, ps, ng = [], [], []
        cvl = [0.0]
        def as_t(val, isp):
            if isp: bs.append(cvl[0]); ps.append(val); ng.append("-"); cvl[0] += val
            else: cvl[0] -= val; bs.append(cvl[0]); ps.append("-"); ng.append(val)

        as_t(v_rec, True); as_t(v_ded, False); as_t(v_cv, False); as_t(v_dop, False)
        as_t(v_or, True); as_t(v_od, False); as_t(v_inv, False); as_t(v_emp, False); as_t(v_dl, False)

        bs.append(0)
        if v_res >= 0: ps.append(v_res); ng.append("-")
        else: ps.append("-"); ng.append(abs(v_res))

        wh = "<!DOCTYPE html><html><head><meta charset='utf-8'><script src='https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'></script><style>body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background: transparent; } .chart-container { background-color: white; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); padding: 15px; height: 380px; } #main { width: 100%; height: 100%; }</style></head><body><div class='chart-container'><div id='main'></div></div><script>var chartDom = document.getElementById('main'); var myChart = echarts.init(chartDom); var option = {tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: function(params) { let tar = params[1].value !== '-' ? params[1] : params[2]; let val = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(tar.value); let sinal = params[2].value !== '-' ? '-' : ''; return `<div style='font-weight:700;margin-bottom:6px;border-bottom:1px solid #E2E8F0;padding-bottom:4px;'>${tar.name}</div><div style='font-weight:800;color:#0F172A;font-size:15px;'>${sinal}${val}</div>`; } }, grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }, xAxis: { type: 'category', splitLine: {show: false}, data: ['Rec Bruta', 'Deduções', 'Custos Var', 'Desp Op', 'Out Rec', 'Out Desp', 'Invest', 'Emp', 'Dist Luc', 'Líquido'], axisLabel: {fontSize: 10, interval: 0, rotate: 30, color: '#64748B', fontWeight: 600} }, yAxis: { type: 'value', axisLabel: {fontSize: 10, color: '#64748B'} }, series: [{ name: 'Base', type: 'bar', stack: 'Total', itemStyle: { borderColor: 'transparent', color: 'transparent' }, emphasis: { itemStyle: { borderColor: 'transparent', color: 'transparent' } }, data: __BASES__ }, { name: 'Entrada', type: 'bar', stack: 'Total', itemStyle: {color: '#38A169', borderRadius: [4, 4, 0, 0]}, label: { show: true, position: 'top', fontSize: 9, color: '#38A169', formatter: function(p){ return p.value > 0 ? '+' + Intl.NumberFormat('pt-BR', { notation: 'compact' }).format(p.value) : '';} }, data: __POS__ }, { name: 'Saída', type: 'bar', stack: 'Total', itemStyle: {color: '#E53E3E', borderRadius: [0, 0, 4, 4]}, label: { show: true, position: 'bottom', fontSize: 9, color: '#E53E3E', formatter: function(p){ return p.value > 0 ? '-' + Intl.NumberFormat('pt-BR', { notation: 'compact' }).format(p.value) : '';} }, data: __NEG__ }]}; option && myChart.setOption(option); window.addEventListener('resize', myChart.resize);</script></body></html>"
        wh = wh.replace("__BASES__", json.dumps(bs)).replace("__POS__", json.dumps(ps)).replace("__NEG__", json.dumps(ng))
        components.html(wh, height=410)

    with c_ch2:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>📉</span> Projetado x Realizado (Saldo)</div>", unsafe_allow_html=True)
        ld, lb = [], []
        cb = calcular_saldo_historico_ate(st.session_state.data_inicio)
        for i in range((st.session_state.data_fim - st.session_state.data_inicio).days + 1):
            cd = st.session_state.data_inicio + timedelta(days=i)
            cb += delta_fc.get(cd, 0.0)
            ld.append(cd.strftime("%d/%m")); lb.append(round(cb, 2))
        
        ah = "<!DOCTYPE html><html><head><meta charset='utf-8'><script src='https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'></script><style>body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background: transparent; } .chart-container { background-color: white; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); padding: 15px; height: 380px; } #main { width: 100%; height: 100%; }</style></head><body><div class='chart-container'><div id='main'></div></div><script>var chartDom = document.getElementById('main'); var myChart = echarts.init(chartDom); var option = {tooltip: { trigger: 'axis', formatter: function(params) { let val = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(params[0].value); return `<div style='font-weight:700;margin-bottom:6px;border-bottom:1px solid #E2E8F0;padding-bottom:4px;'>Caixa em ${params[0].name}</div><div style='font-weight:800;color:#0F172A;font-size:15px;'>${val}</div>`; } }, grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }, xAxis: { type: 'category', boundaryGap: false, data: __DATES__, axisLabel: {fontSize: 10, color: '#64748B', fontWeight: 600} }, yAxis: { type: 'value', axisLabel: {fontSize: 10, color: '#64748B'} }, series: [{ data: __BALS__, type: 'line', smooth: true, symbol: 'none', itemStyle: {color: '#3182CE'}, lineStyle: {width: 3}, areaStyle: {color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: 'rgba(49,130,206,0.4)'}, {offset: 1, color: 'rgba(49,130,206,0.02)'}])} }]}; option && myChart.setOption(option); window.addEventListener('resize', myChart.resize);</script></body></html>"
        ah = ah.replace("__DATES__", json.dumps(ld)).replace("__BALS__", json.dumps(lb))
        components.html(ah, height=410)

    st.markdown("<hr style='border-color: #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)
    c_rk1, c_rk2 = st.columns([5, 5], gap="large")
    
    despesas_periodo = []
    ofensores_detalhes = {}
    for l in st.session_state.lancamentos_reais:
        if l.get("ativo", True):
            try:
                if st.session_state.data_inicio <= datetime.strptime(l["data_real"], "%Y-%m-%d").date() <= st.session_state.data_fim:
                    if l["conta"] not in ofensores_detalhes: ofensores_detalhes[l["conta"]] = []
                    ofensores_detalhes[l["conta"]].append(l)
            except: pass

    for conta, dados in dados_consolidados.items():
        if dados["tipo"] in ["deducao", "custo_variavel", "despesa_operacional", "outras_despesas", "investimento", "emprestimo", "distribuicao_lucro"]:
            diff = dados["real"] - dados["p1"]
            if dados["real"] > 0 or dados["p1"] > 0:
                despesas_periodo.append({"conta": conta, "real": dados["real"], "proj": dados["p1"], "diff": diff})
    
    estouraram = sorted([d for d in despesas_periodo if d["diff"] > 0.01], key=lambda x: x["diff"], reverse=True)[:10]
    economizaram = sorted([d for d in despesas_periodo if d["diff"] < -0.01], key=lambda x: x["diff"])[:10]

    with c_rk1:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>🚨</span> Top 10 Acima do Projetado (Estouraram)</div>", unsafe_allow_html=True)
        if not estouraram:
            st.markdown("<div style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='color: #64748B; font-size: 13px; text-align: center; padding: 10px;'>Nenhuma conta acima do projetado. Excelente! 🎉</div></div>", unsafe_allow_html=True)
        else:
            for i, d in enumerate(estouraram):
                with st.expander(f"{i+1}. {d['conta']} | Real: {formatar_moeda(d['real'])} (+{formatar_moeda(d['diff'])})"):
                    detalhes = ofensores_detalhes.get(d['conta'], [])
                    if detalhes:
                        for l in detalhes:
                            st.markdown(f"<div style='font-size:12px; border-bottom:1px solid #E2E8F0; padding:4px 0;'><span style='color:#64748B;'>{datetime.strptime(l['data_real'], '%Y-%m-%d').strftime('%d/%m')}</span> - {l.get('descricao', 'Sem observação')} : <b>{formatar_moeda(l['valor'])}</b></div>", unsafe_allow_html=True)
                    else: st.caption("Detalhes não encontrados.")

    with c_rk2:
        st.markdown("<div class='saas-section-title' style='margin-bottom: 15px;'><span style='font-size: 18px;'>🏆</span> Top 10 Abaixo do Projetado (Economia)</div>", unsafe_allow_html=True)
        r_html2 = "<div style='background-color: white; border: 1px solid #D1E0FF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>"
        if not economizaram:
            r_html2 += "<div style='color: #64748B; font-size: 13px; text-align: center; padding: 10px;'>Nenhuma economia registrada no período.</div>"
        else:
            for i, d in enumerate(economizaram):
                r_html2 += f"<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #F1F5F9; padding: 10px 0; {'border-bottom: none;' if i == len(economizaram)-1 else ''}'><div style='flex: 1;'><div style='font-size: 12.5px; font-weight: 700; color: #1E293B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{i+1}. {d['conta']}</div><div style='font-size: 10.5px; color: #94A3B8; font-weight: 500;'>Real: {formatar_moeda(d['real'])} | Proj: {formatar_moeda(d['proj'])}</div></div><div style='text-align: right; background-color: #F0FDF4; padding: 4px 8px; border-radius: 6px; border: 1px solid #BBF7D0;'><span style='font-weight: 800; color: #166534; font-size: 13px;'>{formatar_moeda(d['diff'])}</span></div></div>"
        r_html2 += "</div>"
        st.markdown(r_html2, unsafe_allow_html=True)

# =========================================================
# PÁGINA: DRE SEMANAL
# =========================================================
elif st.session_state.pagina_atual == "DRE RESUMIDO":
    st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div class='saas-page-title notranslate'>DRE Semanal (Previsor de Fluxo de Caixa / 4 Semanas)</div><div class='saas-page-subtitle notranslate'>Preveja gargalos financeiros mapeando o resultado e o saldo acumulado para as próximas 4 semanas.</div>", unsafe_allow_html=True)
    c_date, _ = st.columns([3, 7])
    with c_date: 
        d_sel = st.date_input("📅 Data Base (Calcula as 4 semanas seguintes)", key="data_inicio", format="DD/MM/YYYY")
        d_ini = d_sel - timedelta(days=d_sel.weekday())
    st.markdown("</div>", unsafe_allow_html=True)

    w1i, w1f = d_ini, d_ini + timedelta(days=6); w2i, w2f = w1i + timedelta(days=7), w1f + timedelta(days=7)
    w3i, w3f = w2i + timedelta(days=7), w2f + timedelta(days=7); w4i, w4f = w3i + timedelta(days=7), w3f + timedelta(days=7)
    
    w1_raw = consolidar_dados_periodo(w1i, w1f, aplicar_cfo=True); dw1 = calcular_dre(w1_raw)
    w2_raw = consolidar_dados_periodo(w2i, w2f, aplicar_cfo=True); dw2 = calcular_dre(w2_raw)
    w3_raw = consolidar_dados_periodo(w3i, w3f, aplicar_cfo=True); dw3 = calcular_dre(w3_raw)
    w4_raw = consolidar_dados_periodo(w4i, w4f, aplicar_cfo=True); dw4 = calcular_dre(w4_raw)
    
    dtot = {k: {"p1": dw1[k]["p1"]+dw2[k]["p1"]+dw3[k]["p1"]+dw4[k]["p1"], "real": dw1[k]["real"]+dw2[k]["real"]+dw3[k]["real"]+dw4[k]["real"]} for k in dw1.keys()}
    sh = calcular_saldo_historico_ate(w1i)
    siw1p, sfw1p = sh, sh + dw1["resultado_liquido"]["p1"]
    siw2p, sfw2p = sfw1p, sfw1p + dw2["resultado_liquido"]["p1"]
    siw3p, sfw3p = sfw2p, sfw2p + dw3["resultado_liquido"]["p1"]
    siw4p, sfw4p = sfw3p, sfw3p + dw4["resultado_liquido"]["p1"]
    siw1r, sfw1r = sh, sh + dw1["resultado_liquido"]["real"]
    siw2r, sfw2r = sfw1r, sfw1r + dw2["resultado_liquido"]["real"]
    siw3r, sfw3r = sfw2r, sfw2r + dw3["resultado_liquido"]["real"]
    siw4r, sfw4r = sfw3r, sfw3r + dw4["resultado_liquido"]["real"]

    gc = [{"id": "receita_bruta", "nome": "RECEITA BRUTA", "is_sub": False}, {"id": "deducoes", "nome": "(-) DEDUÇÕES", "is_sub": False}, {"id": "receita_liquida", "nome": "(=) RECEITA LÍQUIDA", "is_sub": True}, {"id": "custos_variaveis", "nome": "(-) CUSTOS VARIÁVEIS", "is_sub": False}, {"id": "margem_contribuicao", "nome": "(=) MARGEM DE CONTRIBUIÇÃO", "is_sub": True}, {"id": "despesas_operacionais", "nome": "(-) DESPESAS OPERACIONAIS", "is_sub": False}, {"id": "ebitda", "nome": "(=) EBITDA", "is_sub": True}, {"id": "outras_receitas", "nome": "(+) OUTRAS RECEITAS", "is_sub": False}, {"id": "outras_despesas", "nome": "(-) OUTRAS DESPESAS", "is_sub": False}, {"id": "investimentos", "nome": "(-) INVESTIMENTOS", "is_sub": False}, {"id": "emprestimos", "nome": "(-) EMPRÉSTIMOS", "is_sub": False}, {"id": "resultado_bruto", "nome": "(=) RESULTADO BRUTO", "is_sub": True}, {"id": "distribuicao_lucro", "nome": "(-) DISTRIBUIÇÃO DE LUCRO", "is_sub": False}, {"id": "resultado_liquido", "nome": "(=) RESULTADO LÍQUIDO", "is_sub": True}]
    def f(v): return f"<span style='color: #A0AEC0; font-weight: 500;'>0,00</span>" if v == 0 else formatar_moeda(v).replace('R$ ', '')
    def fb(v): return f"<span style='color: {'#15803D' if v >= 0 else '#B91C1C'}; font-weight: 800;'>{formatar_moeda(v).replace('R$ ', '')}</span>"

    ht = f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"><style>body {{ font-family: "Inter", sans-serif; margin: 0; padding: 0; background-color: transparent; }} .table-container {{ background-color: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #D1E0FF; overflow-x: auto; }} table {{ width: 100%; border-collapse: collapse; font-size: 11px; text-align: right; min-width: 1000px; }} th {{ padding: 10px 8px; color: #718096; font-weight: 600; text-transform: uppercase; font-size: 10px; border-bottom: 2px solid #F1F5F9; background-color: #F8FAFC; }} th:first-child, td:first-child {{ text-align: left; position: sticky; left: 0; z-index: 10; background-color: inherit; box-shadow: 2px 0 5px rgba(0,0,0,0.03); padding-left: 15px; }} th:first-child {{ background-color: #F8FAFC; z-index: 11; }} td {{ padding: 8px 8px; border-bottom: 1px solid #F1F5F9; color: #4A5568; white-space: nowrap; }} .row-hover:hover {{ background-color: #F1F5F9 !important; }} .comp-child:hover {{ background-color: #F0F4F8 !important; }}</style><script>function toggleSemanalRow(id) {{ var rows = document.getElementsByClassName("child-of-semanal-" + id); var icon = document.getElementById("icon-semanal-" + id); var isExpanded = false; if (rows.length > 0) isExpanded = rows[0].style.display === "table-row"; for (var i = 0; i < rows.length; i++) rows[i].style.display = isExpanded ? "none" : "table-row"; if(icon) icon.innerHTML = isExpanded ? "+" : "−"; }}</script></head><body><div class="table-container"><table><thead><tr><th rowspan="2" style="min-width: 250px;">Categoria / Subcategoria</th><th colspan="2" style="text-align: center; border-left: 1px solid #E2E8F0;">SEMANA 1<br><span style="font-size:8px; color:#94A3B8;">{w1i.strftime("%d/%m")} - {w1f.strftime("%d/%m")}</span></th><th colspan="2" style="text-align: center; border-left: 1px solid #E2E8F0;">SEMANA 2<br><span style="font-size:8px; color:#94A3B8;">{w2i.strftime("%d/%m")} - {w2f.strftime("%d/%m")}</span></th><th colspan="2" style="text-align: center; border-left: 1px solid #E2E8F0;">SEMANA 3<br><span style="font-size:8px; color:#94A3B8;">{w3i.strftime("%d/%m")} - {w3f.strftime("%d/%m")}</span></th><th colspan="2" style="text-align: center; border-left: 1px solid #E2E8F0;">SEMANA 4<br><span style="font-size:8px; color:#94A3B8;">{w4i.strftime("%d/%m")} - {w4f.strftime("%d/%m")}</span></th><th colspan="2" style="text-align: center; border-left: 1px solid #E2E8F0; background-color: #EEF2FF;">TOTAL 4 SEMANAS</th></tr><tr><th style="border-left: 1px solid #E2E8F0;">Previsto</th><th>Realizado</th><th style="border-left: 1px solid #E2E8F0;">Previsto</th><th>Realizado</th><th style="border-left: 1px solid #E2E8F0;">Previsto</th><th>Realizado</th><th style="border-left: 1px solid #E2E8F0;">Previsto</th><th>Realizado</th><th style="border-left: 1px solid #E2E8F0; background-color: #EEF2FF;">Previsto</th><th style="background-color: #EEF2FF;">Realizado</th></tr></thead><tbody>'
    
    for g in gc:
        gid, gnm, isb = g["id"], g["nome"], g["is_sub"]
        tipo_cat = {"receita_bruta": "receita", "deducoes": "deducao", "custos_variaveis": "custo_variavel", "despesas_operacionais": "despesa_operacional", "outras_receitas": "outras_receitas", "outras_despesas": "outras_despesas", "investimentos": "investimento", "emprestimos": "emprestimo", "distribuicao_lucro": "distribuicao_lucro"}.get(gid)
        scs = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == tipo_cat] if tipo_cat else []
        
        c = "#38A169" if "(+)" in gnm else "#3182CE" if "(=)" in gnm else "#E53E3E" if "RESULTADO" in gnm and dtot[gid]["real"] < 0 else "#4A5568"
        fw, bg = "700" if isb else "600", "#F8FAFC" if isb else "white"
        
        cs = "cursor: pointer;" if scs else "cursor: default;"
        oc = f'onclick="toggleSemanalRow(\'{gid}\')"' if scs else ""
        ic = f"<span id='icon-semanal-{gid}' style='display:inline-block; width:12px; font-weight:900; color:{st.session_state.color_primary};'>+</span> " if scs else "<span style='display:inline-block; width:12px;'>&nbsp;</span> "

        ht += f'<tr class="row-hover" style="{cs} background-color: {bg};" {oc}><td style="color: {c}; font-weight: {fw}; position: sticky; left: 0; z-index: 10; background-color: {bg};">{ic}{gnm}</td><td style="border-left: 1px solid #F1F5F9;">{f(dw1[gid]["p1"])}</td><td>{f(dw1[gid]["real"])}</td><td style="border-left: 1px solid #F1F5F9;">{f(dw2[gid]["p1"])}</td><td>{f(dw2[gid]["real"])}</td><td style="border-left: 1px solid #F1F5F9;">{f(dw3[gid]["p1"])}</td><td>{f(dw3[gid]["real"])}</td><td style="border-left: 1px solid #F1F5F9;">{f(dw4[gid]["p1"])}</td><td>{f(dw4[gid]["real"])}</td><td style="border-left: 1px solid #E2E8F0; font-weight: 700; background-color: #F8FAFC;">{f(dtot[gid]["p1"])}</td><td style="font-weight: 700; background-color: #F8FAFC;">{f(dtot[gid]["real"])}</td></tr>'
        
        for sc in scs:
            sc_w1_p = w1_raw.get(sc, {}).get("p1", 0.0); sc_w1_r = w1_raw.get(sc, {}).get("real", 0.0)
            sc_w2_p = w2_raw.get(sc, {}).get("p1", 0.0); sc_w2_r = w2_raw.get(sc, {}).get("real", 0.0)
            sc_w3_p = w3_raw.get(sc, {}).get("p1", 0.0); sc_w3_r = w3_raw.get(sc, {}).get("real", 0.0)
            sc_w4_p = w4_raw.get(sc, {}).get("p1", 0.0); sc_w4_r = w4_raw.get(sc, {}).get("real", 0.0)
            sc_tot_p = sc_w1_p + sc_w2_p + sc_w3_p + sc_w4_p; sc_tot_r = sc_w1_r + sc_w2_r + sc_w3_r + sc_w4_r

            ht += f'<tr class="comp-child child-of-semanal-{gid}" style="display: none; background-color: #FAFAFA;"><td style="padding-left: 35px; color: #718096; font-size: 11px; position: sticky; left: 0; z-index: 10; background-color: #FAFAFA;">↳ {sc}</td><td style="border-left: 1px solid #F1F5F9;">{f(sc_w1_p)}</td><td>{f(sc_w1_r)}</td><td style="border-left: 1px solid #F1F5F9;">{f(sc_w2_p)}</td><td>{f(sc_w2_r)}</td><td style="border-left: 1px solid #F1F5F9;">{f(sc_w3_p)}</td><td>{f(sc_w3_r)}</td><td style="border-left: 1px solid #F1F5F9;">{f(sc_w4_p)}</td><td>{f(sc_w4_r)}</td><td style="border-left: 1px solid #E2E8F0; font-weight: 700; background-color: #F8FAFC;">{f(sc_tot_p)}</td><td style="font-weight: 700; background-color: #F8FAFC;">{f(sc_tot_r)}</td></tr>'

    sis = st.session_state.get("saldo_inicial", 0.0); cga = sh - sis
    ht += f'<tr style="background-color: #F8FAFC; border-top: 2px solid #CBD5E1;"><td style="font-weight: 700; color: #64748B;"><span style="display:inline-block; width:12px;">&nbsp;</span>(+) SALDO INICIAL CADASTRADO</td><td style="border-left: 1px solid #E2E8F0;">{f(sis)}</td><td>{f(sis)}</td><td style="border-left: 1px solid #E2E8F0;">{f(sis)}</td><td>{f(sis)}</td><td style="border-left: 1px solid #E2E8F0;">{f(sis)}</td><td>{f(sis)}</td><td style="border-left: 1px solid #E2E8F0;">{f(sis)}</td><td>{f(sis)}</td><td style="border-left: 1px solid #E2E8F0; background-color: #EEF2FF; font-weight: 700;">{f(sis)}</td><td style="background-color: #EEF2FF; font-weight: 700;">{f(sis)}</td></tr><tr style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0;"><td style="font-weight: 700; color: #64748B;"><span style="display:inline-block; width:12px;">&nbsp;</span>(+) CAIXA GERADO ANTES DESTE PERÍODO</td><td style="border-left: 1px solid #E2E8F0;">{f(cga)}</td><td>{f(cga)}</td><td style="border-left: 1px solid #E2E8F0;">{f(cga)}</td><td>{f(cga)}</td><td style="border-left: 1px solid #E2E8F0;">{f(cga)}</td><td>{f(cga)}</td><td style="border-left: 1px solid #E2E8F0;">{f(cga)}</td><td>{f(cga)}</td><td style="border-left: 1px solid #E2E8F0; background-color: #EEF2FF; font-weight: 700;">{f(cga)}</td><td style="background-color: #EEF2FF; font-weight: 700;">{f(cga)}</td></tr><tr style="background-color: #F1F5F9; border-top: 1px solid #CBD5E1;"><td style="font-weight: 800; color: #0F172A;"><span style="display:inline-block; width:12px;">&nbsp;</span>(=) SALDO DE CAIXA NO INÍCIO DA SEMANA</td><td style="border-left: 1px solid #E2E8F0; font-weight: 700; color:#4A5568;">{f(siw1p)}</td><td style="font-weight: 700; color:#4A5568;">{f(siw1r)}</td><td style="border-left: 1px solid #E2E8F0; font-weight: 700; color:#4A5568;">{f(siw2p)}</td><td style="font-weight: 700; color:#4A5568;">{f(siw2r)}</td><td style="border-left: 1px solid #E2E8F0; font-weight: 700; color:#4A5568;">{f(siw3p)}</td><td style="font-weight: 700; color:#4A5568;">{f(siw3r)}</td><td style="border-left: 1px solid #E2E8F0; font-weight: 700; color:#4A5568;">{f(siw4p)}</td><td style="font-weight: 700; color:#4A5568;">{f(siw4r)}</td><td style="border-left: 1px solid #E2E8F0; background-color: #EEF2FF; font-weight: 700; color:#4A5568;">{f(siw1p)}</td><td style="background-color: #EEF2FF; font-weight: 700; color:#4A5568;">{f(siw1r)}</td></tr><tr style="background-color: #F8FAFC;"><td style="font-weight: 700; color: #64748B;"><span style="display:inline-block; width:12px;">&nbsp;</span>(=) RESULTADO LÍQUIDO DA SEMANA</td><td style="border-left: 1px solid #E2E8F0;">{f(dw1["resultado_liquido"]["p1"])}</td><td>{f(dw1["resultado_liquido"]["real"])}</td><td style="border-left: 1px solid #E2E8F0;">{f(dw2["resultado_liquido"]["p1"])}</td><td>{f(dw2["resultado_liquido"]["real"])}</td><td style="border-left: 1px solid #E2E8F0;">{f(dw3["resultado_liquido"]["p1"])}</td><td>{f(dw3["resultado_liquido"]["real"])}</td><td style="border-left: 1px solid #E2E8F0;">{f(dw4["resultado_liquido"]["p1"])}</td><td>{f(dw4["resultado_liquido"]["real"])}</td><td style="border-left: 1px solid #E2E8F0; background-color: #EEF2FF; font-weight: 700;">{f(dtot["resultado_liquido"]["p1"])}</td><td style="background-color: #EEF2FF; font-weight: 700;">{f(dtot["resultado_liquido"]["real"])}</td></tr><tr style="background-color: #E2E8F0; border-top: 1px solid #CBD5E1; border-bottom: 2px solid #CBD5E1;"><td style="font-weight: 900; color: #0F172A;"><span style="display:inline-block; width:12px;">&nbsp;</span>(=) SALDO FINAL DE CAIXA</td><td style="border-left: 1px solid #CBD5E1;">{fb(sfw1p)}</td><td>{fb(sfw1r)}</td><td style="border-left: 1px solid #CBD5E1;">{fb(sfw2p)}</td><td>{fb(sfw2r)}</td><td style="border-left: 1px solid #CBD5E1;">{fb(sfw3p)}</td><td>{fb(sfw3r)}</td><td style="border-left: 1px solid #CBD5E1;">{fb(sfw4p)}</td><td>{fb(sfw4r)}</td><td style="border-left: 1px solid #CBD5E1; background-color: #E0E7FF;">{fb(sfw4p)}</td><td style="background-color: #E0E7FF;">{fb(sfw4r)}</td></tr></tbody></table></div></body></html>'
    components.html(ht, height=750, scrolling=True)

# =========================================================
# PÁGINA: DRE ANUAL E PLANEJAMENTO
# =========================================================
elif st.session_state.pagina_atual == "DRE ANUAL":
    st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div class='saas-page-title notranslate'>DRE Anual (Visão Horizontal)</div><div class='saas-page-subtitle notranslate'>Acompanhe a sazonalidade e a tendência do negócio mês a mês num único painel.</div>", unsafe_allow_html=True)
    col_ano, _ = st.columns([2, 8])
    with col_ano: a_sel = st.selectbox("Selecione o Ano Base", list(range(2020, 2031)), index=date.today().year - 2020)
    st.markdown("</div>", unsafe_allow_html=True)
    md = consolidar_dados_anual(a_sel, aplicar_cfo=True)
    da, ac = calcular_dre_anual(md)
    def fm(v): return "<span style='color: #CBD5E1; font-weight: 500;'>0,00</span>" if v == 0 else f"<span style='font-weight: 600;'>{formatar_moeda(v).replace('R$ ', '')}</span>"
    def fd(v): return "<span style='color: #94A3B8; font-weight: 600;'>-</span>" if abs(v) < 0.01 else f"<span style='color: {'#15803D' if v >= 0 else '#B91C1C'}; font-weight: 600;'>{'+' if v > 0 else '-'}{formatar_moeda(abs(v)).replace('R$ ', '')}</span>"
    def fp(v, b): return "<span style='color: #CBD5E1; font-weight: 500;'>0,0%</span>" if b == 1 and v == 0 else f"<span style='color: #A0AEC0; font-weight: 500;'>{(v / b) * 100:.1f}%".replace('.', ',') + "</span>"
    bar = ac['receita_liquida']['real'] if ac['receita_liquida']['real'] != 0 else (ac['receita_bruta']['real'] if ac['receita_bruta']['real'] != 0 else 1)
    bap = ac['receita_liquida']['p1'] if ac['receita_liquida']['p1'] != 0 else (ac['receita_bruta']['p1'] if ac['receita_bruta']['p1'] != 0 else 1)
    gc = [{"id": "receita_bruta", "nome": "(+) Receita de Vendas", "is_sub": False}, {"id": "deducoes", "nome": "(-) Deduções de Vendas", "is_sub": False}, {"id": "receita_liquida", "nome": "(=) Receita líquida", "is_sub": True}, {"id": "custos_variaveis", "nome": "(-) Custos Variáveis", "is_sub": False}, {"id": "margem_contribuicao", "nome": "(=) Margem de contribuição", "is_sub": True}, {"id": "despesas_operacionais", "nome": "(-) Despesas Operacionais", "is_sub": False}, {"id": "ebitda", "nome": "(=) Ebitda", "is_sub": True}, {"id": "outras_receitas", "nome": "(+) Outras Receitas", "is_sub": False}, {"id": "outras_despesas", "nome": "(-) Outras Despesas", "is_sub": False}, {"id": "investimentos", "nome": "(-) Investimentos", "is_sub": False}, {"id": "emprestimos", "nome": "(-) Empréstimos", "is_sub": False}, {"id": "resultado_bruto", "nome": "(=) Resultado op. bruto", "is_sub": True}, {"id": "distribuicao_lucro", "nome": "(-) Distribuição de Lucro", "is_sub": False}, {"id": "resultado_liquido", "nome": "(=) Resultado op. líquido", "is_sub": True}]
    
    cfg_c2, cfg_c3 = st.session_state.cenarios_cfg.get("c2", 30.0), st.session_state.cenarios_cfg.get("c3", 70.0)

    ha = '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"><style>body { font-family: "Inter", sans-serif; margin: 0; padding: 0; background-color: transparent; } .table-container-anual { background-color: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #D1E0FF; overflow-x: auto; max-height: 700px; overflow-y: auto; } .table-anual { width: max-content; border-collapse: collapse; font-size: 11px; text-align: right; } .table-anual th { padding: 10px 8px; color: #718096; font-weight: 600; text-transform: uppercase; font-size: 10px; border-bottom: 2px solid #F1F5F9; background-color: #F8FAFC; white-space: nowrap; position: sticky; top: 0; z-index: 10; } .table-anual td { padding: 8px 8px; border-bottom: 1px solid #F1F5F9; color: #4A5568; white-space: nowrap; } .sticky-l { position: sticky; left: 0; z-index: 12; background-color: inherit; min-width: 220px; text-align: left; box-shadow: 2px 0 5px rgba(0,0,0,0.03); } th.sticky-l { z-index: 20; background-color: #F8FAFC; } .sticky-r1, .sticky-r2, .sticky-r3, .sticky-r4, .sticky-r5, .sticky-r6 { position: sticky; box-sizing: border-box; background-color: inherit; z-index: 12; } .sticky-r1 { right: 0px; width: 60px; min-width: 60px; } .sticky-r2 { right: 60px; width: 60px; min-width: 60px; } .sticky-r3 { right: 120px; width: 85px; min-width: 85px; } .sticky-r4 { right: 205px; width: 85px; min-width: 85px; } .sticky-r5 { right: 290px; width: 85px; min-width: 85px; } .sticky-r6 { right: 375px; width: 85px; min-width: 85px; box-shadow: -2px 0 5px rgba(0,0,0,0.03); } th.sticky-r1, th.sticky-r2, th.sticky-r3, th.sticky-r4, th.sticky-r5, th.sticky-r6 { z-index: 20; background-color: #F8FAFC; } .comp-row:hover { background-color: #F1F5F9 !important; } .comp-child:hover { background-color: #F0F4F8 !important; }</style><script>function toggleAnualRow(id) { var rows = document.getElementsByClassName("child-of-anual-" + id); var icon = document.getElementById("icon-anual-" + id); var isExpanded = false; if (rows.length > 0) isExpanded = rows[0].style.display === "table-row"; for (var i = 0; i < rows.length; i++) rows[i].style.display = isExpanded ? "none" : "table-row"; if(icon) icon.innerHTML = isExpanded ? "+" : "−"; }</script></head><body><div class="table-container-anual"><table class="table-anual"><thead><tr><th rowspan="2" class="sticky-l">Categoria / Subcategoria</th>'
    for m in ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]: ha += f'<th colspan="3" style="text-align: center;">{m}</th>'
    ha += '<th colspan="4" class="sticky-r6" style="text-align: center; right: 120px; width: 340px; min-width: 340px; box-shadow: -2px 0 5px rgba(0,0,0,0.03);">ACUMULADO</th><th colspan="2" class="sticky-r2" style="text-align: center; right: 0px; width: 120px; min-width: 120px;">% (AV)</th></tr><tr>'
    for _ in range(12): ha += '<th style="text-align: right;">Previsto</th><th style="text-align: right;">Realizado</th><th style="text-align: right;">Diferença</th>'
    ha += f'<th class="sticky-r6" style="text-align: right;">Cenário 1</th><th class="sticky-r5" style="text-align: right;">Cenário 2 (+{cfg_c2:g}%)</th><th class="sticky-r4" style="text-align: right;">Cenário 3 (+{cfg_c3:g}%)</th><th class="sticky-r3" style="text-align: right;">Realizado</th><th class="sticky-r2" style="text-align: right;">Real.</th><th class="sticky-r1" style="text-align: right;">Prev.</th></tr></thead><tbody>'
    for item in gc:
        gid, nm, isb = item["id"], item["nome"], item["is_sub"]
        tipo_cat = {"receita_bruta": "receita", "deducoes": "deducao", "custos_variaveis": "custo_variavel", "despesas_operacionais": "despesa_operacional", "outras_receitas": "outras_receitas", "outras_despesas": "outras_despesas", "investimentos": "investimento", "emprestimos": "emprestimo", "distribuicao_lucro": "distribuicao_lucro"}.get(gid)
        scs = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == tipo_cat] if tipo_cat else []
        
        c = "#38A169" if "(+)" in nm else "#3182CE" if "(=)" in nm else "#E53E3E" if "Resultado" in nm and ac[gid]["real"] < 0 else "#4A5568"
        f, bg, cs, oc = ("700", "#F8FAFC", "cursor: pointer;" if scs else "cursor: default;", f'onclick="toggleAnualRow(\'{gid}\')"' if scs else "") if isb else ("600", "white", "cursor: pointer;" if scs else "cursor: default;", f'onclick="toggleAnualRow(\'{gid}\')"' if scs else "")
        ic = f"<span id='icon-anual-{gid}' style='display:inline-block; width:12px; font-weight:900; color:{st.session_state.color_primary};'>+</span> " if scs else "<span style='display:inline-block; width:12px;'>&nbsp;</span> "
        
        ha += f'<tr class="comp-row" style="{cs} background-color: {bg};" {oc}><td class="sticky-l" style="color: {c}; font-weight: {f};">{ic}{nm}</td>'
        for m in range(1, 13): 
            df = da[m][gid]["real"] - da[m][gid]["p1"]
            ha += f'<td>{fm(da[m][gid]["p1"])}</td><td>{fm(da[m][gid]["real"])}</td><td>{fd(df)}</td>'
        ha += f'<td class="sticky-r6">{fm(ac[gid]["p1"])}</td><td class="sticky-r5">{fm(ac[gid]["p2"])}</td><td class="sticky-r4">{fm(ac[gid]["p3"])}</td><td class="sticky-r3">{fm(ac[gid]["real"])}</td><td class="sticky-r2">{fp(ac[gid]["real"], bar)}</td><td class="sticky-r1">{fp(ac[gid]["p1"], bap)}</td></tr>'
        for sc in scs:
            ha += f'<tr class="comp-child child-of-anual-{gid}" style="display: none; background-color: #FAFAFA;"><td class="sticky-l" style="padding-left: 35px; color: #718096; font-size: 11px;">↳ {sc}</td>'
            scr, scp1, scp2, scp3 = 0.0, 0.0, 0.0, 0.0
            for m in range(1, 13):
                r, p1, p2, p3 = md[m].get(sc, {}).get("real", 0.0), md[m].get(sc, {}).get("p1", 0.0), md[m].get(sc, {}).get("p2", 0.0), md[m].get(sc, {}).get("p3", 0.0)
                scr+=r; scp1+=p1; scp2+=p2; scp3+=p3
                ha += f'<td>{fm(p1)}</td><td>{fm(r)}</td><td>{fd(r-p1)}</td>'
            ha += f'<td class="sticky-r6">{fm(scp1)}</td><td class="sticky-r5">{fm(scp2)}</td><td class="sticky-r4">{fm(scp3)}</td><td class="sticky-r3">{fm(scr)}</td><td class="sticky-r2">{fp(scr, bar)}</td><td class="sticky-r1">{fp(scp1, bap)}</td></tr>'

    shr = calcular_saldo_historico_ate(date(a_sel, 1, 1))
    sis = st.session_state.get("saldo_inicial", 0.0)
    cga = shr - sis
    pd_anual = {m: {"r": 0.0, "p1": 0.0, "p2": 0.0, "p3": 0.0} for m in range(1, 13)}
    rr, rp1, rp2, rp3 = shr, shr, shr, shr
    for m in range(1, 13):
        rr+=da[m]["resultado_liquido"]["real"]; rp1+=da[m]["resultado_liquido"]["p1"]; rp2+=da[m]["resultado_liquido"]["p2"]; rp3+=da[m]["resultado_liquido"]["p3"]
        pd_anual[m]["r"], pd_anual[m]["p1"], pd_anual[m]["p2"], pd_anual[m]["p3"] = rr, rp1, rp2, rp3

    ha += f'<tr style="background-color: #F8FAFC; border-top: 2px solid #CBD5E1;"><td class="sticky-l" style="color: #64748B; font-weight: 700;"><span style="display:inline-block; width:12px;">&nbsp;</span>(+) SALDO INICIAL CADASTRADO</td>'
    for m in range(1, 13): ha += f'<td style="color: #64748B; font-weight: 600;">{fm(sis)}</td><td style="color: #64748B; font-weight: 600;">{fm(sis)}</td><td style="color: #64748B; font-weight: 600;">-</td>'
    ha += f'<td class="sticky-r6" style="color: #64748B; font-weight: 600;">{fm(sis)}</td><td class="sticky-r5" style="color: #64748B; font-weight: 600;">{fm(sis)}</td><td class="sticky-r4" style="color: #64748B; font-weight: 600;">{fm(sis)}</td><td class="sticky-r3" style="color: #64748B; font-weight: 600;">{fm(sis)}</td><td class="sticky-r2" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r1" style="text-align: center; color: #94A3B8;">-</td></tr><tr style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0;"><td class="sticky-l" style="color: #64748B; font-weight: 700;"><span style="display:inline-block; width:12px;">&nbsp;</span>(+) CAIXA GERADO ANTES DE 01/JAN</td>'
    for m in range(1, 13): ha += f'<td style="color: #64748B; font-weight: 600;">{fm(cga)}</td><td style="color: #64748B; font-weight: 600;">{fm(cga)}</td><td style="color: #64748B; font-weight: 600;">-</td>'
    ha += f'<td class="sticky-r6" style="color: #64748B; font-weight: 600;">{fm(cga)}</td><td class="sticky-r5" style="color: #64748B; font-weight: 600;">{fm(cga)}</td><td class="sticky-r4" style="color: #64748B; font-weight: 600;">{fm(cga)}</td><td class="sticky-r3" style="color: #64748B; font-weight: 600;">{fm(cga)}</td><td class="sticky-r2" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r1" style="text-align: center; color: #94A3B8;">-</td></tr><tr style="background-color: #F1F5F9; border-top: 1px solid #CBD5E1; border-bottom: 1px solid #E2E8F0;"><td class="sticky-l" style="color: #0F172A; font-weight: 800;"><span style="display:inline-block; width:12px;">&nbsp;</span>(=) SALDO DE CAIXA ACUMULADO (C1)</td>'
    for m in range(1, 13): ha += f'<td style="color: #1E293B; font-weight: 700;">{fm(pd_anual[m]["p1"])}</td><td style="text-align: center; color: #94A3B8;">-</td><td style="text-align: center; color: #94A3B8;">-</td>'
    ha += f'<td class="sticky-r6" style="color: #1E293B; font-weight: 700;">{fm(pd_anual[12]["p1"])}</td><td class="sticky-r5" style="color: #1E293B; font-weight: 700;">{fm(pd_anual[12]["p2"])}</td><td class="sticky-r4" style="color: #1E293B; font-weight: 700;">{fm(pd_anual[12]["p3"])}</td><td class="sticky-r3" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r2" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r1" style="text-align: center; color: #94A3B8;">-</td></tr><tr style="background-color: #F1F5F9; border-bottom: 1px solid #E2E8F0;"><td class="sticky-l" style="color: #0F172A; font-weight: 800;"><span style="display:inline-block; width:12px;">&nbsp;</span>(=) CAIXA REAL ACUMULADO</td>'
    for m in range(1, 13): ha += f'<td style="text-align: center; color: #94A3B8;">-</td><td style="color: {"#15803D" if pd_anual[m]["r"] >= 0 else "#B91C1C"}; font-weight: 700;">{fm(pd_anual[m]["r"])}</td><td style="text-align: center; color: #94A3B8;">-</td>'
    ha += f'<td class="sticky-r6" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r5" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r4" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r3" style="color: {"#15803D" if pd_anual[12]["r"] >= 0 else "#B91C1C"}; font-weight: 700;">{fm(pd_anual[12]["r"])}</td><td class="sticky-r2" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r1" style="text-align: center; color: #94A3B8;">-</td></tr>'
    ha += f'<tr style="background-color: #F8FAFC; border-bottom: 2px solid #CBD5E1;"><td class="sticky-l" style="color: #0F172A; font-weight: 800;"><span style="display:inline-block; width:12px;">&nbsp;</span>(±) DIFERENÇA (REAL vs PROJ.)</td>'
    for m in range(1, 13): ha += f'<td style="text-align: center; color: #94A3B8;">-</td><td style="text-align: center; color: #94A3B8;">-</td><td style="text-align: right;">{fd(pd_anual[m]["r"] - pd_anual[m]["p1"])}</td>'
    ha += f'<td class="sticky-r6" style="text-align: right;">{fd(pd_anual[12]["r"] - pd_anual[12]["p1"])}</td><td class="sticky-r5" style="text-align: right;">{fd(pd_anual[12]["r"] - pd_anual[12]["p2"])}</td><td class="sticky-r4" style="text-align: right;">{fd(pd_anual[12]["r"] - pd_anual[12]["p3"])}</td><td class="sticky-r3" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r2" style="text-align: center; color: #94A3B8;">-</td><td class="sticky-r1" style="text-align: center; color: #94A3B8;">-</td></tr></tbody></table></div></body></html>'
    components.html(ha, height=750, scrolling=True)

elif st.session_state.pagina_atual == "PLANEJAMENTO":
    if not st.session_state.plano_contas: st.warning("⚠️ O seu Plano de Contas está vazio. Vá até à aba **CADASTRO**.")
    else:
        st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-top: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
        ro = st.session_state.get("reset_orc", 0)
        kf, kl, kp, ko = f"ofat_{ro}", f"oliq_{ro}", f"op1_unico_{ro}", f"obs_orc_{ro}"
        ta = TIPO_MAPEAMENTO[st.session_state.get("orc_cat", list(TIPO_MAPEAMENTO.keys())[0])]
        cas = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == ta]
        sa = st.session_state.get("orc_conta")
        sa = sa if sa in cas else (cas[0] if cas else None)
        
        is_blocked = sa and ("master class" in sa.lower() or "masterclass" in sa.lower() or "boleto" in sa.lower())
        ef = next((c.get("exige_faturamento", False) for c in st.session_state.plano_contas if c["nome_conta"] == sa), False) if not is_blocked else False

        st.markdown("<div class='saas-form-group-title' style='margin-top: 5px;'>1. Detalhes da Conta</div>", unsafe_allow_html=True)
        if ef:
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1.5])
            with c1: cf = st.selectbox("Categoria", list(TIPO_MAPEAMENTO.keys()), key="orc_cat")
            with c2: cs = st.selectbox("Subcategoria", cas, key="orc_conta") if cas else st.selectbox("Subcategoria", ["Sem contas"], disabled=True, key="orc_conta_vazia")
            with c3: st.text_input("Faturamento", key=kf, placeholder="R$ 0,00", on_change=aplicar_mascara_moeda, args=(kf,), disabled=not cs); fat = parse_currency(st.session_state.get(kf, "0"))
            with c4: st.text_input("Liquidez (Caixa)", key=kl, placeholder="R$ 0,00", on_change=aplicar_mascara_moeda, args=(kl,), disabled=not cs); p1 = parse_currency(st.session_state.get(kl, "0"))
            with c5: dl = st.date_input("Data Lanç.", date.today(), format="DD/MM/YYYY", disabled=True)
            with c6: dv = st.date_input("1º Venc.", date.today(), format="DD/MM/YYYY", disabled=not cs)
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 2.5, 2.5, 1.5, 1.5])
            with c1: cf = st.selectbox("Categoria", list(TIPO_MAPEAMENTO.keys()), key="orc_cat")
            with c2: cs = st.selectbox("Subcategoria", cas, key="orc_conta") if cas else st.selectbox("Subcategoria", ["Sem contas"], disabled=True, key="orc_conta_vazia")
            with c3: st.text_input("Projeção", key=kp, placeholder="R$ 0,00", on_change=aplicar_mascara_moeda, args=(kp,), disabled=(not cs or is_blocked)); p1 = parse_currency(st.session_state.get(kp, "0"))
            with c4: dl = st.date_input("Data Lanç.", date.today(), format="DD/MM/YYYY", disabled=True)
            with c5: dv = st.date_input("1º Venc.", date.today(), format="DD/MM/YYYY", disabled=not cs)
            fat = 0.0

        cfg_c2, cfg_c3 = st.session_state.cenarios_cfg.get("c2", 30.0), st.session_state.cenarios_cfg.get("c3", 70.0)
        p2, p3 = p1 * (1 + (cfg_c2/100)), p1 * (1 + (cfg_c3/100))

        # Regra de Final de Semana
        acao_fds = "Manter Data"
        if dv.weekday() >= 5:
            st.warning("⚠️ O Vencimento selecionado cai em um Fim de Semana.")
            acao_fds = st.radio("Ajuste automático para Fim de Semana:", ["Manter Data", "Antecipar (Sexta)", "Próximo dia útil (Segunda)"], horizontal=True)

        ir = st.checkbox("🔁 Criar Recorrência", disabled=not cs)
        frq, tt, qp, dlim = "Mensal", "Por Quantidade de Parcelas", 2, date.today()
        if ir and cs:
            st.markdown("<div style='background-color: #F8FAFC; padding: 15px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 15px;'>", unsafe_allow_html=True)
            cr1, cr2, cr3 = st.columns(3)
            with cr1: frq = st.selectbox("Frequência", ["Mensal", "Semanal"])
            with cr2: tt = st.selectbox("Término", ["Por Quantidade de Parcelas", "Por Data Limite"])
            with cr3:
                if tt == "Por Quantidade de Parcelas": qp = st.number_input("Qtd", min_value=2, value=2, step=1)
                else: dlim = st.date_input("Até", dv, format="DD/MM/YYYY")
            st.markdown("</div>", unsafe_allow_html=True)

        co, cb = st.columns([8, 2])
        with co: obs = st.text_input("Observação", key=ko, disabled=not cs)
        with cb:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            if st.button("💾 SALVAR", type="primary", use_container_width=True, disabled=(not cs or (is_blocked and p1 == 0)), key="btn_salvar_orcamento"):
                nls, dbq = [], 0
                
                def ajustar_fds(d, acao):
                    if d.weekday() == 5: 
                        if acao == "Antecipar (Sexta)": return d - timedelta(days=1)
                        elif acao == "Próximo dia útil (Segunda)": return d + timedelta(days=2)
                    elif d.weekday() == 6: 
                        if acao == "Antecipar (Sexta)": return d - timedelta(days=2)
                        elif acao == "Próximo dia útil (Segunda)": return d + timedelta(days=1)
                    return d

                dv_aj = ajustar_fds(dv, acao_fds)

                if not ir:
                    nv = {"id": str(uuid.uuid4()), "data_lancamento": dl.strftime("%Y-%m-%d"), "data_ref": dv_aj.strftime("%Y-%m-%d"), "conta": cs, "faturado": fat, "p1": p1, "p2": p2, "p3": p3, "descricao": obs, "efetivado": False}
                    if nv not in st.session_state.orcamentos: nls.append(nv)
                    else: dbq += 1
                else:
                    cd = dv; i = 0
                    while (tt == "Por Quantidade de Parcelas" and i < int(qp)) or (tt != "Por Quantidade de Parcelas" and cd <= dlim):
                        desc = f"{obs} (Parc {i+1}/{int(qp)})" if tt == "Por Quantidade de Parcelas" else (obs or "Recorrente")
                        cd_aj = ajustar_fds(cd, acao_fds)
                        nv = {"id": str(uuid.uuid4()), "data_lancamento": dl.strftime("%Y-%m-%d"), "data_ref": cd_aj.strftime("%Y-%m-%d"), "conta": cs, "faturado": fat, "p1": p1, "p2": p2, "p3": p3, "descricao": desc, "efetivado": False}
                        if nv not in st.session_state.orcamentos and nv not in nls: nls.append(nv)
                        else: dbq += 1
                        i += 1
                        if frq == "Mensal":
                            m = dv.month - 1 + i; y = dv.year + m // 12; m = m % 12 + 1; cd = date(y, m, min(dv.day, calendar.monthrange(y, m)[1]))
                        else: cd = dv + timedelta(days=7*i)
                if nls: st.session_state.orcamentos.extend(nls); save_db(); st.session_state.reset_orc = ro + 1; show_toast(f"{len(nls)} itens gerados!"); time.sleep(1); st.rerun()
                elif dbq: st.warning(f"⚠️ {dbq} ignorados (duplicados).")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.session_state.orcamentos:
            dfo = pd.DataFrame(st.session_state.orcamentos)
            dfo["Categoria"] = dfo["conta"].map({c["nome_conta"]: {v: k for k, v in TIPO_MAPEAMENTO.items()}[c["categoria_dre"]] for c in st.session_state.plano_contas}).fillna("")
            if 'data_lancamento' not in dfo.columns: dfo['data_lancamento'] = dfo['data_ref']
            st.markdown("<br><div class='saas-section-title'>Histórico de Planejamento</div>", unsafe_allow_html=True)
            cf1, cf2, cf3, cf4, cf5 = st.columns(5)
            with cf1: flo = st.date_input("📅 Lançamento", [], format="DD/MM/YYYY")
            with cf2: fvo = st.date_input("📅 Vencimento", [], format="DD/MM/YYYY")
            with cf3: fco = st.selectbox("🏷️ Categoria", ["Todas"] + sorted(list(dfo["Categoria"].unique())))
            with cf4: fso = st.selectbox("📂 Sub Categoria", ["Todas"] + (sorted(list(dfo[dfo["Categoria"] == fco]["conta"].unique())) if fco != "Todas" else sorted(list(dfo["conta"].unique()))))
            with cf5: foo = st.text_input("📝 Observação")
            
            m = pd.Series(True, index=dfo.index)
            if len(flo)==2: m &= (pd.to_datetime(dfo['data_lancamento']).dt.date >= flo[0]) & (pd.to_datetime(dfo['data_lancamento']).dt.date <= flo[1])
            if len(fvo)==2: m &= (pd.to_datetime(dfo['data_ref']).dt.date >= fvo[0]) & (pd.to_datetime(dfo['data_ref']).dt.date <= fvo[1])
            if fco != "Todas": m &= (dfo["Categoria"] == fco)
            if fso != "Todas": m &= (dfo["conta"] == fso)
            if foo: m &= dfo["descricao"].astype(str).str.lower().str.contains(foo.lower())

            dfof = dfo[m].copy().sort_values(by=["data_ref", "conta"])
            if dfof.empty: st.info("Nenhum planejamento encontrado.")
            else:
                dfof.insert(0, " ", st.checkbox("☑️ Selecionar todos"))
                dfof['Status'] = dfof.apply(lambda r: "✅ Efetivado" if r.get('efetivado') else ("🎯 Projetado" if r.get('Categoria') in ['Receita Bruta','Outras Receitas'] else "⏳ Pendente"), axis=1)
                
                dfof['Vencimento'] = pd.to_datetime(dfof['data_ref']).dt.date
                dfof['Lançamento'] = pd.to_datetime(dfof['data_lancamento']).dt.strftime('%d/%m/%Y')

                dfv = dfof[[" ", "Status", "Lançamento", "Vencimento", "Categoria", "conta", "p1", "p2", "p3", "descricao"]].rename(columns={"conta":"Conta", "p1":"C1", "p2":"C2", "p3":"C3", "descricao":"Obs"})
                edo = st.data_editor(dfv, hide_index=True, use_container_width=True, disabled=["Status", "Lançamento", "Categoria", "Conta"], column_config={" ": st.column_config.CheckboxColumn(" ", width="small"), "Vencimento": st.column_config.DateColumn("Vencimento (Prorrogar/Antecipar)", format="DD/MM/YYYY"), "C1": st.column_config.NumberColumn("C1", format="R$ %.2f"), "C2": st.column_config.NumberColumn("C2", format="R$ %.2f"), "C3": st.column_config.NumberColumn("C3", format="R$ %.2f")})
                
                he = False
                for idx in dfof.index:
                    try:
                        n1, n2, n3, no = float(edo.loc[idx, "C1"]), float(edo.loc[idx, "C2"]), float(edo.loc[idx, "C3"]), str(edo.loc[idx, "Obs"])
                        nd = edo.loc[idx, "Vencimento"].strftime("%Y-%m-%d")
                        o = st.session_state.orcamentos[idx]
                        if n1!=o["p1"] or n2!=o["p2"] or n3!=o["p3"] or no!=o.get("descricao","") or nd!=o["data_ref"]:
                            o["p1"], o["p2"], o["p3"], o["descricao"], o["data_ref"] = n1, n2, n3, no, nd; he = True
                    except: pass
                if he: save_db(); show_toast("Plano Atualizado!"); time.sleep(1); st.rerun()

                si = edo.index[edo[" "] == True].tolist()
                if si:
                    st.markdown("<div style='margin-top: 15px; padding: 15px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;'>", unsafe_allow_html=True)
                    ca1, ca2, _ = st.columns([2, 2, 6])
                    with ca1:
                        if st.button(f"🗑️ Excluir ({len(si)})", type="primary", use_container_width=True, key="btn_excluir_orcamentos_lote"):
                            for i in sorted(si, reverse=True): st.session_state.orcamentos.pop(i)
                            save_db(); show_toast("Excluído com sucesso!"); time.sleep(1); st.rerun()
                    with ca2:
                        if st.button(f"✅ Conciliar ({len(si)})", type="primary", use_container_width=True, key="btn_conciliar_orcamentos_lote"):
                            for i in si: st.session_state.orcamentos[i]["efetivado"] = True
                            save_db(); show_toast("Conciliado!"); time.sleep(1); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina_atual == "REALIZADO":
    dio = st.session_state.get("d_ini_op", st.session_state.data_inicio)
    dfo = st.session_state.get("d_fim_op", st.session_state.data_fim)
    mr = st.session_state.get("modo_realizado", "MANUAL")

    pi, po, ri, ro = 0.0, 0.0, 0.0, 0.0
    mc = {c["nome_conta"]: c["categoria_dre"] for c in st.session_state.plano_contas}
    for o in st.session_state.orcamentos:
        try:
            if dio <= datetime.strptime(o["data_ref"], "%Y-%m-%d").date() <= dfo:
                t = mc.get(o["conta"])
                if t in ["receita", "outras_receitas"]: pi += float(o.get("p1", 0.0))
                elif t: po += float(o.get("p1", 0.0))
        except: pass
    for l in st.session_state.lancamentos_reais:
        if l.get("ativo", True):
            try:
                if dio <= datetime.strptime(l["data_real"], "%Y-%m-%d").date() <= dfo:
                    t, v = mc.get(l["conta"]), float(l.get("valor", 0.0))
                    if t in ["receita", "outras_receitas"]: ri += v
                    elif t: ro += v
            except: pass

    st.markdown(f"<div class='saas-section-title' style='margin-top: 10px;'>🔍 Auditoria Prévia</div><div class='notranslate' style='display: flex; gap: 15px; margin-bottom: 15px; margin-top: 10px;'><div style='flex: 1; background-color: #F8FAFC; padding: 20px; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 11px; font-weight: 700; color: #64748B; margin-bottom: 4px;'>SAÍDA PROJETADA</div><div style='font-size: 22px; font-weight: 800; color: #4A5568;'>{formatar_moeda(po)}</div></div><div style='flex: 1; background-color: #FFF5F5; padding: 20px; border-radius: 16px; border: 1px solid #FED7D7; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 11px; font-weight: 700; color: #C53030; margin-bottom: 4px;'>SAÍDA REALIZADA</div><div style='font-size: 22px; font-weight: 800; color: #9B1C1C;'>{formatar_moeda(ro)}</div></div><div style='flex: 1; background-color: #F0F9FF; padding: 20px; border-radius: 16px; border: 1px solid #D1E0FF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 11px; font-weight: 700; color: #2B6CB0; margin-bottom: 4px;'>ENTRADA PROJETADA</div><div style='font-size: 22px; font-weight: 800; color: #2C5282;'>{formatar_moeda(pi)}</div></div><div style='flex: 1; background-color: #F0FDF4; padding: 20px; border-radius: 16px; border: 1px solid #BBF7D0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div style='font-size: 11px; font-weight: 700; color: #166534; margin-bottom: 4px;'>ENTRADA REALIZADA</div><div style='font-size: 22px; font-weight: 800; color: #14532D;'>{formatar_moeda(ri)}</div></div></div>", unsafe_allow_html=True)

    st.markdown("<div style='background-color: white; padding: 15px 20px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
    cf1, cf2, cf3, cf4 = st.columns([2.5, 2.5, 2, 2])
    with cf1:
        st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
        if st.button("✍️ Manual", type="primary" if mr == "MANUAL" else "secondary", use_container_width=True, key="btn_modo_manual"): st.session_state.modo_realizado = "MANUAL"; st.rerun()
    with cf2:
        st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
        if st.button("⚡ Lote", type="primary" if mr == "LOTE" else "secondary", use_container_width=True, key="btn_modo_lote"): st.session_state.modo_realizado = "LOTE"; st.rerun()
    with cf3: st.session_state.d_ini_op = st.date_input("Início", dio, format="DD/MM/YYYY")
    with cf4: st.session_state.d_fim_op = st.date_input("Fim", dfo, format="DD/MM/YYYY")
    st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state.plano_contas: st.warning("⚠️ Cadastre o Plano de Contas primeiro.")
    else:
        if mr == "MANUAL":
            st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
            rl = st.session_state.get("reset_lanc", 0)
            
            c1, c2, c3, c4, c5 = st.columns([1.5, 2.5, 2.5, 1.75, 1.75])
            with c1: dlan = st.date_input("Data", date.today(), format="DD/MM/YYYY")
            with c2: cl = st.selectbox("Categoria", list(TIPO_MAPEAMENTO.keys()), index=0); tl = TIPO_MAPEAMENTO[cl]
            c_disp = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == tl]
            with c3: csel = st.selectbox("Origem", c_disp) if c_disp else st.selectbox("Origem", ["Sem contas"], disabled=True)
            
            is_blocked = csel and ("master class" in csel.lower() or "masterclass" in csel.lower() or "boleto" in csel.lower())
            ef = next((c.get("exige_faturamento", False) for c in st.session_state.plano_contas if c["nome_conta"] == csel), False) if (csel and csel != "Sem contas" and not is_blocked) else False
            klq, klv = f"lq_{rl}", f"lv_{rl}"
            
            with c4:
                st.text_input("Faturado", key=klv, on_change=aplicar_mascara_moeda, args=(klv,), disabled=(not ef or is_blocked))
                fr = parse_currency(st.session_state.get(klv, "0")) if ef else 0.0
            with c5:
                st.text_input("Liquidez", key=klq, on_change=aplicar_mascara_moeda, args=(klq,), disabled=(not csel or csel == "Sem contas" or is_blocked))
                vr = parse_currency(st.session_state.get(klq, "0"))
                if vr > 0:
                    s, cr, bg = ("+", "#15803D", "#F0FDF4") if tl in ["receita", "outras_receitas"] else ("-", "#B91C1C", "#FEF2F2")
                    st.markdown(f"<div style='background-color:{bg}; border:1px solid {cr}50; padding:6px 10px; border-radius:6px; margin-top:-10px; font-size:11px; color:{cr}; font-weight:700;'>📊 Caixa: {s} {formatar_moeda(vr)}</div>", unsafe_allow_html=True)

            c6, c7, c8 = st.columns([5, 3, 2])
            with c6: obs = st.text_input("Observação (O que está pagando ou recebendo?)", key=f"obs_man_{rl}")
            with c7: f_pag = st.selectbox("Forma de Pagamento", st.session_state.formas_pagamento if st.session_state.formas_pagamento else ["Não Cadastrado"], key=f"fpag_{rl}")
            with c8:
                st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                bs = st.button("✅ SALVAR", type="primary", disabled=(not csel or csel == "Sem contas" or (is_blocked and vr == 0)), use_container_width=True, key="btn_salvar_lanc_manual")

            if bs:
                if vr <= 0: st.error("Valor zerado.")
                else:
                    st.session_state.lancamentos_reais.append({"transacao_id": str(uuid.uuid4()), "ativo": True, "data_real": dlan.strftime("%Y-%m-%d"), "conta": csel, "faturado": fr, "valor": vr, "descricao": obs, "forma_pagamento": f_pag, "nao_previsto": True})
                    save_db(); st.session_state.reset_lanc = rl + 1; show_toast("Salvo com sucesso!"); time.sleep(1); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        elif mr == "LOTE":
            st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
            st.info("💡 Escolha o período, marque 'Baixar?' e preencha o **Realizado**.")
            pds = [o for o in st.session_state.orcamentos if not o.get("efetivado") and mc.get(o["conta"]) not in ["receita", "outras_receitas"]]
            if not pds: st.success("Tudo em dia!")
            else:
                dfp = pd.DataFrame(pds)
                dfp["Categoria"] = dfp["conta"].map(mc).map({v: k for k, v in TIPO_MAPEAMENTO.items()}).fillna("")
                c1, c2, _ = st.columns([2, 2, 6])
                with c1: dbi = st.date_input("Vencimento Inicial", date.today(), format="DD/MM/YYYY")
                with c2: dbf = st.date_input("Vencimento Final", date.today() + timedelta(days=7), format="DD/MM/YYYY")
                mp = (pd.to_datetime(dfp['data_ref']).dt.date >= dbi) & (pd.to_datetime(dfp['data_ref']).dt.date <= dbf)
                dfpf = dfp[mp].copy().sort_values(by="data_ref")
                if dfpf.empty: st.info("Nenhum lançamento no período.")
                else:
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    dfpf.insert(0, "Baixar?", st.checkbox("☑️ Selecionar todos os visíveis"))
                    dfpf['Vencimento'] = pd.to_datetime(dfpf['data_ref']).dt.strftime('%d/%m/%Y')
                    dfvp = dfpf[["Baixar?", "Vencimento", "Categoria", "conta", "p1", "id", "descricao"]].rename(columns={"conta":"Origem (Conta)", "p1":"Projetado (R$)", "descricao":"Observação"})
                    dfvp["Projetado (R$)"] = dfvp["Projetado (R$)"].astype(float); dfvp["Realizado (Edite aqui)"] = np.nan
                    
                    edp = st.data_editor(dfvp, hide_index=True, use_container_width=True, disabled=["Vencimento", "Categoria", "Origem (Conta)", "Observação", "Projetado (R$)"], column_config={"Baixar?": st.column_config.CheckboxColumn("Baixar?", width="small"), "Projetado (R$)": st.column_config.NumberColumn("Projetado (R$)", format="R$ %.2f"), "Realizado (Edite aqui)": st.column_config.NumberColumn("Realizado (Edite aqui)", format="R$ %.2f", min_value=0.0)})
                    
                    st.markdown("<div style='background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px 20px; border-radius: 12px; margin-top: 15px;'>", unsafe_allow_html=True)
                    cb1, cb2, _ = st.columns([2, 3, 5])
                    with cb1: dba = st.date_input("Data da Efetivação (Pagamento):", date.today(), format="DD/MM/YYYY")
                    with cb2:
                        st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                        if st.button("⚡ Confirmar Efetivação", type="primary", use_container_width=True, key="btn_confirmar_efetivacao_lote_real"):
                            ls = edp[edp["Baixar?"] == True]
                            if ls.empty: st.error("Selecione itens.")
                            elif any(pd.isna(r["Realizado (Edite aqui)"]) or float(r["Realizado (Edite aqui)"]) <= 0 for _, r in ls.iterrows()): st.error("⚠️ Valores zerados detectados.")
                            else:
                                cbx = 0
                                for _, r in ls.iterrows():
                                    oid, vef = r["id"], float(r["Realizado (Edite aqui)"])
                                    for o in st.session_state.orcamentos:
                                        if o.get("id") == oid:
                                            o["efetivado"] = True
                                            o["data_ref"] = dba.strftime("%Y-%m-%d")
                                            st.session_state.lancamentos_reais.append({"transacao_id": str(uuid.uuid4()), "ativo": True, "data_real": dba.strftime("%Y-%m-%d"), "conta": o["conta"], "faturado": o.get("faturado", 0.0), "valor": vef, "descricao": o.get("descricao", "") + " (Baixa Lote)", "orcamento_id": oid, "forma_pagamento": "Lote", "nao_previsto": False}); cbx += 1
                                            break
                                save_db(); show_toast(f"{cbx} baixados e ajustados!"); time.sleep(1.5); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.lancamentos_reais:
            st.markdown("<div class='saas-section-title' style='margin-top: 20px;'>Extrato de Realizado</div>", unsafe_allow_html=True)
            dfl = pd.DataFrame(st.session_state.lancamentos_reais)
            dfl["Categoria"] = dfl["conta"].map(mc).map({v: k for k, v in TIPO_MAPEAMENTO.items()}).fillna("")

            with st.expander("🔍 Filtros de Busca Avançada", expanded=False):
                cf1, cf2, cf3, cf4 = st.columns(4)
                with cf1: fdl = st.date_input("📅 Data", [], format="DD/MM/YYYY")
                with cf2: fcl = st.selectbox("🏷️ Categoria", ["Todas"] + sorted(list(dfl["Categoria"].unique())))
                with cf3: fsl = st.selectbox("📂 Origem", ["Todas"] + (sorted(list(dfl[dfl["Categoria"] == fcl]["conta"].unique())) if fcl != "Todas" else ["Todas"]))
                with cf4: fol = st.text_input("📝 Busca")

            ml = pd.Series(True, index=dfl.index)
            if len(fdl)==2: ml &= (pd.to_datetime(dfl['data_real']).dt.date >= fdl[0]) & (pd.to_datetime(dfl['data_real']).dt.date <= fdl[1])
            if fcl != "Todas": ml &= (dfl["Categoria"] == fcl)
            if fsl != "Todas": ml &= (dfl["conta"] == fsl)
            if fol: ml &= dfl["descricao"].astype(str).str.lower().str.contains(fol.lower())
            
            vlx = st.toggle("🗑️ Ver Lixeira")
            ml &= (dfl["ativo"] == False) if vlx else (dfl["ativo"] != False)
            dflf = dfl[ml].copy().sort_values(by=["data_real", "conta"], ascending=False)

            if not dflf.empty:
                psz = 50; tp = math.ceil(len(dflf) / psz)
                cpg1, cpg2 = st.columns([8, 2])
                with cpg2: pg = st.number_input(f"Página (1 a {tp})", 1, tp, 1)
                
                dfp = dflf.iloc[(pg-1)*psz : pg*psz].copy()
                dfp.insert(0, "Sel.", False); dfp['Data'] = pd.to_datetime(dfp['data_real']).dt.strftime('%d/%m/%Y')
                
                if "forma_pagamento" not in dfp.columns: dfp["forma_pagamento"] = "Não Informado"
                else: dfp["forma_pagamento"] = dfp["forma_pagamento"].fillna("Não Informado")

                dfp['Origem'] = dfp.apply(lambda r: f"⚠️ {r['conta']}" if r.get('nao_previsto') else r['conta'], axis=1)

                dflv = dfp[["Sel.", "Data", "Categoria", "Origem", "descricao", "forma_pagamento", "faturado", "valor"]].rename(columns={"descricao":"Observação", "forma_pagamento": "Forma Pag.", "faturado":"Faturado Info (R$)", "valor":"Liquidez/Caixa (R$)"})
                
                edl = st.data_editor(dflv, hide_index=True, use_container_width=True, disabled=["Data", "Categoria", "Origem", "Forma Pag."], column_config={"Sel.": st.column_config.CheckboxColumn("Sel.", width="small"), "Faturado Info (R$)": st.column_config.NumberColumn("Faturado Info (R$)", format="R$ %.2f"), "Liquidez/Caixa (R$)": st.column_config.NumberColumn("Liquidez/Caixa (R$)", format="R$ %.2f")})

                hel = False
                for di, ri in enumerate(dfp.index):
                    try:
                        nf, nv, no = float(edl.iloc[di]["Faturado Info (R$)"]), float(edl.iloc[di]["Liquidez/Caixa (R$)"]), str(edl.iloc[di]["Observação"])
                        of, ov, oo = float(st.session_state.lancamentos_reais[ri].get("faturado", 0.0)), float(st.session_state.lancamentos_reais[ri]["valor"]), str(st.session_state.lancamentos_reais[ri].get("descricao", ""))
                        if nf!=of or nv!=ov or no!=oo: st.session_state.lancamentos_reais[ri]["faturado"], st.session_state.lancamentos_reais[ri]["valor"], st.session_state.lancamentos_reais[ri]["descricao"] = nf, nv, no; hel = True
                    except: pass
                if hel: save_db(); show_toast("Atualizado!"); time.sleep(1); st.rerun()

                sr = edl[edl["Sel."] == True]
                if not sr.empty:
                    sri = dfp.loc[sr.index].index.tolist()
                    st.markdown("<div style='margin-top: 15px; padding: 15px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;'><div style='font-weight:700; margin-bottom:10px;'>Ações em Lote</div>", unsafe_allow_html=True)
                    if vlx:
                        if st.button("♻️ Restaurar", type="primary", key="btn_restaurar_lixeira_lote"):
                            for i in sri: st.session_state.lancamentos_reais[i]["ativo"] = True
                            save_db(); show_toast("Restaurado!"); time.sleep(1); st.rerun()
                    else:
                        ca1, ca2, ca3 = st.columns([2, 3, 3])
                        with ca1:
                            if st.button("🗑️ Mover para Lixeira", key="btn_mover_lixeira_lote"):
                                for i in sri:
                                    st.session_state.lancamentos_reais[i]["ativo"] = False
                                    oid = st.session_state.lancamentos_reais[i].get("orcamento_id")
                                    if oid:
                                        for o in st.session_state.orcamentos:
                                            if o.get("id") == oid: o["efetivado"] = False; break
                                save_db(); show_toast("Enviado à lixeira"); time.sleep(1); st.rerun()
                        with ca2: ltc = st.selectbox("Nova Categoria", list(TIPO_MAPEAMENTO.keys()))
                        with ca3:
                            clt = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == TIPO_MAPEAMENTO[ltc]]
                            if clt:
                                lco = st.selectbox("Nova Origem", clt)
                                if st.button("🔄 Aplicar", type="primary", key="btn_aplicar_nova_categoria_lote"):
                                    for i in sri: st.session_state.lancamentos_reais[i]["conta"] = lco
                                    save_db(); show_toast("Alterado!"); time.sleep(1); st.rerun()
                            else: st.selectbox("Nova Origem", ["Sem contas"], disabled=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            else: st.info("Nenhum dado encontrado.")

elif st.session_state.pagina_atual == "CONCILIACAO":
    st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
    if not st.session_state.bancos: st.info("Nenhuma conta bancária cadastrada. Vá à aba **CADASTRO**.")
    else:
        st.markdown("<div class='saas-section-title'>🏦 Atualização de Saldos Bancários</div><div class='saas-section-subtitle'>Atualize o saldo das contas bancárias.</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, b in enumerate(st.session_state.bancos):
            with cols[i % 3]:
                st.markdown(f"<div style='background-color: #F8FAFC; padding: 15px 20px 8px 20px; border-radius: 16px 16px 0 0; border: 1px solid #D1E0FF; border-bottom: none;'><div style='display: flex; justify-content: space-between; align-items: center;'><div style='font-weight: 700; color: #1E293B; font-size: 15px;'>🏦 {b['nome']}</div><div style='font-size: 10px; background-color: #E2E8F0; color: #475569; padding: 2px 8px; border-radius: 10px;'>{b.get('ultima_atualizacao', '-')}</div></div></div>", unsafe_allow_html=True)
                ks = f"s_edit_{b['id']}"
                if ks not in st.session_state: st.session_state[ks] = formatar_moeda(b["saldo"])
                st.text_input("Saldo", key=ks, on_change=aplicar_mascara_e_salvar_saldo, args=(i, ks), label_visibility="collapsed")
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
    pi = [p for p in st.session_state.pendencias if p["tipo"] == "entrada" and not p.get("conta")]
    po = [p for p in st.session_state.pendencias if p["tipo"] == "saida" and not p.get("conta")]
    p_vin = [p for p in st.session_state.pendencias if p["tipo"] == "entrada" and p.get("conta")]
    p_vou = [p for p in st.session_state.pendencias if p["tipo"] == "saida" and p.get("conta")]
    qi, vi = len(pi), sum(float(p["valor"]) for p in pi)
    qo, vo = len(po), sum(float(p["valor"]) for p in po)

    ct, ck = st.columns([1.2, 1])
    with ct: st.markdown("<div class='saas-section-title'>Monitor de Pendências e Conciliações</div><div class='saas-section-subtitle'>Identifique valores e confirme recebimentos (Conciliação).</div>", unsafe_allow_html=True)
    with ck: st.markdown(f'<div style="display: flex; gap: 15px; margin-bottom: 10px;"><div style="flex: 1; background-color: #F0F9FF; padding: 12px 16px; border-radius: 12px; border: 1px solid #D1E0FF;"><div style="font-size: 10px; font-weight: 700; color: #2B6CB0;">Apenas Pendentes IN ({qi})</div><div style="font-size: 18px; font-weight: 800; color: #2C5282;">{formatar_moeda(vi)}</div></div><div style="flex: 1; background-color: #FFF5F5; padding: 12px 16px; border-radius: 12px; border: 1px solid #FED7D7;"><div style="font-size: 10px; font-weight: 700; color: #C53030;">Apenas Pendentes OUT ({qo})</div><div style="font-size: 18px; font-weight: 800; color: #9B1C1C;">{formatar_moeda(vo)}</div></div></div>', unsafe_allow_html=True)
    
    if not st.session_state.bancos: st.warning("⚠️ Cadastre um banco primeiro.")
    else:
        ti, to, tv_in, tv_out = st.tabs(["📥 Nova Entrada P.", "📤 Nova Saída P.", "✔️ Validar Entrada", "✔️ Validar Saída"])
        with ti:
            st.markdown("<div class='saas-form-group-title' style='margin-top: 10px;'>Adicionar Entrada Pendente</div>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 3])
            with c1: pdi = st.date_input("Data", date.today(), format="DD/MM/YYYY", key="pin_d")
            with c2: pbi = st.selectbox("Banco", [b["nome"] for b in st.session_state.bancos], key="pin_b")
            c_disp = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] in ["receita", "outras_receitas"]]
            with c3: pin_c = st.selectbox("Categoria (Opcional)", ["(Não Identificado)"] + c_disp, key="pin_c")
            with c4: st.text_input("Valor", key="p_in_val", on_change=aplicar_mascara_moeda, args=("p_in_val",)); vli = parse_currency(st.session_state.get("p_in_val", "0"))
            with c5: poi = st.text_input("Obs", key="pin_o")
            if st.button("➕ Salvar", type="primary", key="btn_add_pin_entrada"):
                if vli <= 0: st.error("Valor > 0.")
                else: 
                    st.session_state.pendencias.append({"id": str(uuid.uuid4()), "tipo": "entrada", "data": pdi.strftime("%Y-%m-%d"), "banco": pbi, "valor": vli, "observacao": poi, "conta": None if pin_c == "(Não Identificado)" else pin_c})
                    save_db(); show_toast("Pendente!"); time.sleep(1); st.rerun()

            if pi:
                st.markdown("<hr style='border-color: #E2E8F0; margin: 20px 0;'><div class='saas-form-group-title'>Resolver (Identificar)</div>", unsafe_allow_html=True)
                dfpi = pd.DataFrame(pi); dfpi.insert(0, "Sel", False); dfvpi = dfpi[["Sel", "data", "banco", "observacao", "valor", "id"]].copy(); dfvpi['data'] = pd.to_datetime(dfvpi['data']).dt.strftime('%d/%m/%Y')
                epi = st.data_editor(dfvpi, hide_index=True, use_container_width=True, disabled=["data", "banco", "observacao", "valor"], column_config={"Sel": st.column_config.CheckboxColumn("Sel", width="small"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"), "id": None})
                spi = epi[epi["Sel"] == True]
                if not spi.empty:
                    if len(spi) > 1: st.warning("⚠️ Um por vez.")
                    else:
                        r = spi.iloc[0]; pid, pval, pobs, pbk = r["id"], r["valor"], r["observacao"], r["banco"]
                        st.markdown(f"<div style='background-color: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #D1E0FF; margin-top: 15px;'><div style='font-size:14px; font-weight:700; margin-bottom:10px;'>Mover: <span style='color:#38A169;'>{formatar_moeda(pval)}</span> — {pobs}</div>", unsafe_allow_html=True)
                        m1, m2, m3 = st.columns([3, 3, 2])
                        with m1: csi = st.selectbox("Categoria", [k for k, v in TIPO_MAPEAMENTO.items() if v in ["receita", "outras_receitas"]], key=f"ci_{pid}")
                        with m2:
                            ori = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == TIPO_MAPEAMENTO[csi]]
                            osi = st.selectbox("Origem", ori, key=f"oi_{pid}") if ori else st.selectbox("Origem", ["Sem contas"], disabled=True, key=f"oiv_{pid}")
                        with m3:
                            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                            if st.button("Confirmar Identificação", type="primary", key=f"bi_conf_{pid}", use_container_width=True, disabled=not osi):
                                st.session_state.lancamentos_reais.append({"transacao_id": str(uuid.uuid4()), "ativo": True, "data_real": datetime.strptime(r["data"], "%d/%m/%Y").strftime("%Y-%m-%d"), "conta": osi, "faturado": 0.0, "valor": pval, "descricao": f"{pobs} (Resolvido: {pbk})", "nao_previsto": True})
                                st.session_state.pendencias = [x for x in st.session_state.pendencias if x["id"] != pid]; save_db(); show_toast("Resolvido!"); time.sleep(1); st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
        
        with to:
            st.markdown("<div class='saas-form-group-title' style='margin-top: 10px;'>Adicionar Saída Pendente</div>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 3])
            with c1: pdo = st.date_input("Data", date.today(), format="DD/MM/YYYY", key="pout_d")
            with c2: pbo = st.selectbox("Banco", [b["nome"] for b in st.session_state.bancos], key="pout_b")
            c_disp2 = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] not in ["receita", "outras_receitas"]]
            with c3: pout_c = st.selectbox("Categoria (Opcional)", ["(Não Identificado)"] + c_disp2, key="pout_c")
            with c4: st.text_input("Valor", key="p_out_val", on_change=aplicar_mascara_moeda, args=("p_out_val",)); vlo = parse_currency(st.session_state.get("p_out_val", "0"))
            with c5: poo = st.text_input("Obs", key="pout_o")
            if st.button("➕ Salvar", type="primary", key="btn_add_pout_saida"):
                if vlo <= 0: st.error("Valor > 0.")
                else: 
                    st.session_state.pendencias.append({"id": str(uuid.uuid4()), "tipo": "saida", "data": pdo.strftime("%Y-%m-%d"), "banco": pbo, "valor": vlo, "observacao": poo, "conta": None if pout_c == "(Não Identificado)" else pout_c})
                    save_db(); show_toast("Pendente!"); time.sleep(1); st.rerun()

            if po:
                st.markdown("<hr style='border-color: #E2E8F0; margin: 20px 0;'><div class='saas-form-group-title'>Resolver (Identificar)</div>", unsafe_allow_html=True)
                dfpo = pd.DataFrame(po); dfpo.insert(0, "Sel", False); dfvpo = dfpo[["Sel", "data", "banco", "observacao", "valor", "id"]].copy(); dfvpo['data'] = pd.to_datetime(dfvpo['data']).dt.strftime('%d/%m/%Y')
                epo = st.data_editor(dfvpo, hide_index=True, use_container_width=True, disabled=["data", "banco", "observacao", "valor"], column_config={"Sel": st.column_config.CheckboxColumn("Sel", width="small"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"), "id": None})
                spo = epo[epo["Sel"] == True]
                if not spo.empty:
                    if len(spo) > 1: st.warning("⚠️ Um por vez.")
                    else:
                        r = spo.iloc[0]; pid, pval, pobs, pbk = r["id"], r["valor"], r["observacao"], r["banco"]
                        st.markdown(f"<div style='background-color: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #D1E0FF; margin-top: 15px;'><div style='font-size:14px; font-weight:700; margin-bottom:10px;'>Mover: <span style='color:#E53E3E;'>{formatar_moeda(pval)}</span> — {pobs}</div>", unsafe_allow_html=True)
                        m1, m2, m3 = st.columns([3, 3, 2])
                        with m1: cso = st.selectbox("Categoria", [k for k, v in TIPO_MAPEAMENTO.items() if v not in ["receita", "outras_receitas"]], key=f"co_{pid}")
                        with m2:
                            oro = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == TIPO_MAPEAMENTO[cso]]
                            oso = st.selectbox("Origem", oro, key=f"oo_{pid}") if oro else st.selectbox("Origem", ["Sem contas"], disabled=True, key=f"oov_{pid}")
                        with m3:
                            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                            if st.button("Confirmar Identificação", type="primary", key=f"bo_conf_{pid}", use_container_width=True, disabled=not oso):
                                st.session_state.lancamentos_reais.append({"transacao_id": str(uuid.uuid4()), "ativo": True, "data_real": datetime.strptime(r["data"], "%d/%m/%Y").strftime("%Y-%m-%d"), "conta": oso, "faturado": 0.0, "valor": pval, "descricao": f"{pobs} (Resolvido: {pbk})", "nao_previsto": True})
                                st.session_state.pendencias = [x for x in st.session_state.pendencias if x["id"] != pid]; save_db(); show_toast("Resolvido!"); time.sleep(1); st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
        
        with tv_in:
            st.markdown("<div class='saas-form-group-title' style='margin-top: 10px;'>Validar Entradas (Cliente Identificado)</div>", unsafe_allow_html=True)
            if not p_vin: st.info("Tudo validado!")
            else:
                dfvi = pd.DataFrame(p_vin); dfvi.insert(0, "Validar?", False)
                dfv_v = dfvi[["Validar?", "data", "conta", "banco", "valor", "observacao", "id"]].rename(columns={"conta": "Pré-Categoria"}).copy()
                dfv_v['data'] = pd.to_datetime(dfv_v['data']).dt.strftime('%d/%m/%Y')
                ed_vi = st.data_editor(dfv_v, hide_index=True, use_container_width=True, disabled=["data", "Pré-Categoria", "banco", "valor", "observacao"], column_config={"Validar?": st.column_config.CheckboxColumn("Validar?", width="small"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})
                si = ed_vi[ed_vi["Validar?"] == True]
                if not si.empty:
                    if st.button("✅ Confirmar Validação em Lote", type="primary", key="btn_val_in"):
                        cbx = 0
                        for _, r in si.iterrows():
                            pid = r["id"]
                            pobj = next(p for p in st.session_state.pendencias if p["id"] == pid)
                            st.session_state.lancamentos_reais.append({"transacao_id": str(uuid.uuid4()), "ativo": True, "data_real": pobj["data"], "conta": pobj["conta"], "faturado": 0.0, "valor": float(pobj["valor"]), "descricao": f"{pobj.get('observacao','')} (Validado: {pobj['banco']})", "nao_previsto": True})
                            st.session_state.pendencias = [x for x in st.session_state.pendencias if x["id"] != pid]
                            cbx+=1
                        save_db(); show_toast(f"{cbx} validados!"); time.sleep(1); st.rerun()

        with tv_out:
            st.markdown("<div class='saas-form-group-title' style='margin-top: 10px;'>Validar Saídas (Fornecedor Identificado)</div>", unsafe_allow_html=True)
            if not p_vou: st.info("Tudo validado!")
            else:
                dfvo = pd.DataFrame(p_vou); dfvo.insert(0, "Validar?", False)
                dfv_o = dfvo[["Validar?", "data", "conta", "banco", "valor", "observacao", "id"]].rename(columns={"conta": "Pré-Categoria"}).copy()
                dfv_o['data'] = pd.to_datetime(dfv_o['data']).dt.strftime('%d/%m/%Y')
                ed_vo = st.data_editor(dfv_o, hide_index=True, use_container_width=True, disabled=["data", "Pré-Categoria", "banco", "valor", "observacao"], column_config={"Validar?": st.column_config.CheckboxColumn("Validar?", width="small"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})
                so = ed_vo[ed_vo["Validar?"] == True]
                if not so.empty:
                    if st.button("✅ Confirmar Validação em Lote", type="primary", key="btn_val_out"):
                        cbx = 0
                        for _, r in so.iterrows():
                            pid = r["id"]
                            pobj = next(p for p in st.session_state.pendencias if p["id"] == pid)
                            st.session_state.lancamentos_reais.append({"transacao_id": str(uuid.uuid4()), "ativo": True, "data_real": pobj["data"], "conta": pobj["conta"], "faturado": 0.0, "valor": float(pobj["valor"]), "descricao": f"{pobj.get('observacao','')} (Validado: {pobj['banco']})", "nao_previsto": True})
                            st.session_state.pendencias = [x for x in st.session_state.pendencias if x["id"] != pid]
                            cbx+=1
                        save_db(); show_toast(f"{cbx} validados!"); time.sleep(1); st.rerun()

elif st.session_state.pagina_atual == "ACAO_CFO":
    st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div class='saas-page-title notranslate'>Ação CFO (Análise de Cenários)</div><div class='saas-page-subtitle notranslate'>Simule o impacto de aumentos ou cortes nas projeções do sistema sem alterar os orçamentos originais. A simulação altera apenas projeções em data futura a partir de hoje.</div>", unsafe_allow_html=True)
    
    d_in, d_out = st.session_state.data_inicio, st.session_state.data_fim
    dre_simulado = calcular_dre(consolidar_dados_periodo(d_in, d_out, aplicar_cfo=True))
    dre_original = calcular_dre(consolidar_dados_periodo(d_in, d_out, aplicar_cfo=False))
    
    l_ori = dre_original["resultado_liquido"]["p1"]
    l_sim = dre_simulado["resultado_liquido"]["p1"]
    l_diff = l_sim - l_ori
    c_diff = "#38A169" if l_diff >= 0 else "#E53E3E"
    s_diff = "+" if l_diff >= 0 else ""
    
    st.markdown(f"<div style='display: flex; gap: 15px; margin-bottom: 20px;'><div style='flex: 1; background-color: #F8FAFC; padding: 15px; border-radius: 12px; border: 1px solid #E2E8F0;'><div style='font-size: 11px; font-weight: 700; color: #64748B;'>LUCRO PROJETADO (ORIGINAL)</div><div style='font-size: 20px; font-weight: 800; color: #4A5568;'>{formatar_moeda(l_ori)}</div></div><div style='flex: 1; background-color: #F0F9FF; padding: 15px; border-radius: 12px; border: 1px solid #BEE3F8;'><div style='font-size: 11px; font-weight: 700; color: #2B6CB0;'>LUCRO PROJETADO (SIMULADO)</div><div style='font-size: 20px; font-weight: 800; color: #2C5282;'>{formatar_moeda(l_sim)}</div></div><div style='flex: 1; background-color: white; padding: 15px; border-radius: 12px; border: 1px solid {c_diff}50;'><div style='font-size: 11px; font-weight: 700; color: {c_diff};'>IMPACTO DA AÇÃO CFO</div><div style='font-size: 20px; font-weight: 800; color: {c_diff};'>{s_diff}{formatar_moeda(l_diff)}</div></div></div></div>", unsafe_allow_html=True)

    st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
    t_in, t_out, t_reg = st.tabs(["📥 Simular Entradas", "📤 Simular Saídas", "📋 Regras Ativas"])
    
    with t_in:
        st.markdown("<div class='saas-section-title' style='margin-top: 10px;'>Ajuste de Receitas</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([2.5, 3, 2, 2.5])
        with c1: c_in = st.selectbox("Categoria", [k for k, v in TIPO_MAPEAMENTO.items() if v in ["receita", "outras_receitas"]], key="cfo_cat_in")
        c_in_int = TIPO_MAPEAMENTO[c_in]
        sc_in = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == c_in_int]
        with c2: s_in = st.selectbox("Subcategoria", ["Todas as contas"] + sc_in, key="cfo_sub_in") if sc_in else st.selectbox("Subcategoria", ["Sem contas"], disabled=True, key="cfo_sub_in")
        with c3: p_in = st.number_input("Ajuste (%)", value=0.0, step=1.0, key="cfo_pct_in", help="Ex: 5 para aumentar, -5 para reduzir.")
        with c4:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            if st.button("💾 Aplicar Regra", type="primary", use_container_width=True, key="btn_cfo_in", disabled=not sc_in):
                chv = "todas" if s_in == "Todas as contas" else s_in
                if c_in_int not in st.session_state.acao_cfo["entradas"]: st.session_state.acao_cfo["entradas"][c_in_int] = {}
                st.session_state.acao_cfo["entradas"][c_in_int][chv] = {"pct": p_in, "data": date.today().strftime("%Y-%m-%d")}
                save_db(); show_toast("Aplicado!"); time.sleep(1); st.rerun()
                
    with t_out:
        st.markdown("<div class='saas-section-title' style='margin-top: 10px;'>Ajuste de Custos e Despesas</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([2.5, 3, 2, 2.5])
        with c1: c_out = st.selectbox("Categoria", [k for k, v in TIPO_MAPEAMENTO.items() if v not in ["receita", "outras_receitas"]], key="cfo_cat_out")
        c_out_int = TIPO_MAPEAMENTO[c_out]
        sc_out = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == c_out_int]
        with c2: s_out = st.selectbox("Subcategoria", ["Todas as contas"] + sc_out, key="cfo_sub_out") if sc_out else st.selectbox("Subcategoria", ["Sem contas"], disabled=True, key="cfo_sub_out")
        with c3: p_out = st.number_input("Ajuste (%)", value=0.0, step=1.0, key="cfo_pct_out", help="Ex: -5 para economizar, 5 para inflacionar.")
        with c4:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            if st.button("💾 Aplicar Regra", type="primary", use_container_width=True, key="btn_cfo_out", disabled=not sc_out):
                chv = "todas" if s_out == "Todas as contas" else s_out
                if c_out_int not in st.session_state.acao_cfo["saidas"]: st.session_state.acao_cfo["saidas"][c_out_int] = {}
                st.session_state.acao_cfo["saidas"][c_out_int][chv] = {"pct": p_out, "data": date.today().strftime("%Y-%m-%d")}
                save_db(); show_toast("Aplicado!"); time.sleep(1); st.rerun()
                
    with t_reg:
        regras_ativas = []
        rev_map = {v: k for k, v in TIPO_MAPEAMENTO.items()}
        for t_mac, cor_mac, icon in [("entradas", "#2B6CB0", "📥"), ("saidas", "#C53030", "📤")]:
            for cat, rgs in st.session_state.acao_cfo[t_mac].items():
                cat_vis = rev_map.get(cat, cat)
                for sub, cfg in list(rgs.items()):
                    pct = cfg.get("pct", 0.0) if isinstance(cfg, dict) else cfg
                    dt_r = cfg.get("data", "Sempre") if isinstance(cfg, dict) else "Sempre"
                    if pct != 0.0:
                        regras_ativas.append({"tipo_mac": t_mac, "cat_int": cat, "cat_vis": cat_vis, "sub": sub, "pct": pct, "data": dt_r, "cor": cor_mac, "icon": icon})
        
        if not regras_ativas:
            st.info("Nenhuma regra de simulação ativa no momento.")
        else:
            c1, c2 = st.columns([8, 2])
            with c1: st.markdown("<div class='saas-section-title' style='margin-top: 10px;'>Regras em Vigor</div>", unsafe_allow_html=True)
            with c2: 
                if st.button("🗑️ Zerar Simulação", type="secondary", use_container_width=True):
                    st.session_state.acao_cfo = {"entradas": {}, "saidas": {}}
                    save_db(); show_toast("Zerado!"); time.sleep(1); st.rerun()
                    
            for rg in regras_ativas:
                cr1, cr2, cr3 = st.columns([6, 3, 1])
                with cr1:
                    st.markdown(f"<div style='margin-top: 8px; font-size: 14px; font-weight: 600; color: #1E293B;'>{rg['icon']} {rg['cat_vis']} <span style='color: #94A3B8;'>➔</span> {rg['sub'].capitalize()} <span style='font-size:10px; color:#A0AEC0; font-weight:500;'>(A partir de {rg['data']})</span></div>", unsafe_allow_html=True)
                with cr2:
                    novo_pct = st.number_input("Ajuste (%)", value=float(rg['pct']), step=1.0, key=f"edit_rg_{rg['tipo_mac']}_{rg['cat_int']}_{rg['sub']}", label_visibility="collapsed")
                    if novo_pct != float(rg['pct']):
                        st.session_state.acao_cfo[rg['tipo_mac']][rg['cat_int']][rg['sub']]["pct"] = novo_pct
                        save_db(); st.rerun()
                with cr3:
                    if st.button("🗑️", key=f"del_rg_{rg['tipo_mac']}_{rg['cat_int']}_{rg['sub']}", help="Excluir regra específica"):
                        del st.session_state.acao_cfo[rg['tipo_mac']][rg['cat_int']][rg['sub']]
                        save_db(); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina_atual == "CADASTRO":
    st.markdown("<div style='background-color: white; padding: 24px; border-radius: 16px; border: 1px solid #D1E0FF; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'><div class='saas-page-title notranslate'>Configurações e Cadastros</div><div class='saas-page-subtitle notranslate'>Centralize aqui todas as configurações.</div>", unsafe_allow_html=True)
    t_emp, tc, tb, tfp, tv = st.tabs(["🏢 Empresas", "📋 Plano de Contas", "🏦 Contas Bancárias", "💳 Formas de Pagamento", "✨ Design & Cenários"])

    with t_emp:
        st.markdown("<div class='saas-section-title' style='margin-top:15px;'>Cadastrar Nova Empresa</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
        with c1: e_nome = st.text_input("Razão Social / Nome da Empresa")
        with c2: e_cnpj = st.text_input("CNPJ")
        with c3: e_obs = st.text_input("Observação")
        with c4:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Cadastrar", type="primary", use_container_width=True, key="btn_add_empresa"):
                if not e_nome.strip(): st.error("Digite a Razão Social.")
                else:
                    nid = f"emp_{str(uuid.uuid4())[:8]}"
                    st.session_state.db["empresas"][nid] = {
                        "nome": e_nome.strip(), "cnpj": e_cnpj.strip(), "obs": e_obs.strip(), "ativo": True,
                        "cenarios": {"c2": 30.0, "c3": 70.0},
                        "dados": {"plano_contas": [], "orcamentos": [], "lancamentos_reais": [], "bancos": [], "pendencias": [], "saldo_inicial": 0.0, "regras_pendencia": {"tipo": "Quantidade", "limite": 5}, "formas_pagamento": ["PIX", "Cartão de Crédito", "Boleto", "Dinheiro"], "acao_cfo": {"entradas": {}, "saidas": {}}}
                    }
                    save_db(); show_toast("Empresa cadastrada com sucesso!"); time.sleep(1.5); st.rerun()
                    
        st.markdown("<hr style='border-color: #E2E8F0; margin: 25px 0;'><div class='saas-section-title'>Empresas Cadastradas</div>", unsafe_allow_html=True)
        lista_empresas = []
        for k, v in st.session_state.db["empresas"].items():
            lista_empresas.append({"ID": k, "Razão Social": v["nome"], "CNPJ": v.get("cnpj", ""), "Obs": v.get("obs", ""), "Status": "Ativa" if v.get("ativo", True) else "Inativa"})
        
        df_emp = pd.DataFrame(lista_empresas)
        df_emp["Ação"] = False
        ed_emp = st.data_editor(df_emp, hide_index=True, use_container_width=True, disabled=["ID", "Razão Social", "CNPJ", "Obs", "Status"], column_config={"Ação": st.column_config.CheckboxColumn("Selecionar")})
        si_emp = ed_emp[ed_emp["Ação"] == True]
        
        if not si_emp.empty:
            st.markdown("<div style='margin-top: 15px; padding: 15px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;'>", unsafe_allow_html=True)
            ea1, ea2, ea3 = st.columns(3)
            with ea1:
                if st.button("⏸️ Inativar / Ativar", use_container_width=True):
                    for _, r in si_emp.iterrows():
                        k = r["ID"]
                        st.session_state.db["empresas"][k]["ativo"] = not st.session_state.db["empresas"][k].get("ativo", True)
                    save_db(); st.rerun()
            with ea2:
                if st.button("🗑️ Excluir Definitivo", use_container_width=True, type="primary"):
                    for _, r in si_emp.iterrows():
                        k = r["ID"]
                        d_chk = st.session_state.db["empresas"][k]["dados"]
                        if len(d_chk.get("lancamentos_reais", [])) > 0 or len(d_chk.get("orcamentos", [])) > 0:
                            st.error(f"⚠️ A empresa {r['Razão Social']} possui lançamentos. Inative-a em vez de excluir.")
                        else:
                            del st.session_state.db["empresas"][k]
                            save_db(); show_toast("Excluído!"); time.sleep(1); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with tc:
        st.markdown("<div class='saas-section-title' style='margin-top:15px;'>Estrutura do DRE</div>", unsafe_allow_html=True)
        ta, te, td = st.tabs(["➕ Adicionar", "✏️ Editar / Remover", "📋 Duplicar Plano"])
        with ta:
            c1, c2, c3 = st.columns([2.5, 2.5, 1.5])
            with c1: nc = st.text_input("Nome da Subcategoria")
            with c2:
                ts = st.selectbox("Grupo no DRE", list(TIPO_MAPEAMENTO.keys()))
                ef = st.checkbox("Controlar Faturado?", key="chk_add_fat") if TIPO_MAPEAMENTO[ts] in ["receita", "outras_receitas"] else False
            with c3:
                st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                if st.button("➕ Adicionar", type="primary", use_container_width=True, key="btn_add_plano_conta"):
                    if not nc.strip(): st.error("Digite o nome.")
                    elif any(c["nome_conta"].lower() == nc.lower() for c in st.session_state.plano_contas): st.error("Já existe!")
                    else: st.session_state.plano_contas.append({"nome_conta": nc, "categoria_dre": TIPO_MAPEAMENTO[ts], "exige_faturamento": ef}); save_db(); show_toast("Cadastrado!"); time.sleep(1); st.rerun()

        with te:
            if not st.session_state.plano_contas: st.info("Vazio.")
            else:
                ca = st.selectbox("Subcategoria para editar:", [c["nome_conta"] for c in st.session_state.plano_contas])
                if ca:
                    da = next(c for c in st.session_state.plano_contas if c["nome_conta"] == ca)
                    c1, c2, c3, c4 = st.columns([3, 3, 2, 2])
                    with c1: nn = st.text_input("Novo Nome", value=ca)
                    with c2:
                        ng = st.selectbox("Novo Grupo", list(TIPO_MAPEAMENTO.keys()), index=list(TIPO_MAPEAMENTO.keys()).index(next(k for k, v in TIPO_MAPEAMENTO.items() if v == da["categoria_dre"])))
                        nef = st.checkbox("Controlar Faturado?", value=da.get("exige_faturamento", False), key="chk_edit_fat") if TIPO_MAPEAMENTO[ng] in ["receita", "outras_receitas"] else False
                    with c3:
                        st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                        if st.button("💾 Salvar", type="primary", use_container_width=True, key="btn_salvar_plano_conta_unico"):
                            if not nn.strip(): st.error("Vazio.")
                            elif nn != ca and any(c["nome_conta"].lower() == nn.lower() for c in st.session_state.plano_contas): st.error("Já existe.")
                            else:
                                for c in st.session_state.plano_contas:
                                    if c["nome_conta"] == ca: c["nome_conta"], c["categoria_dre"], c["exige_faturamento"] = nn, TIPO_MAPEAMENTO[ng], nef
                                if nn != ca:
                                    for o in st.session_state.orcamentos:
                                        if o["conta"] == ca: o["conta"] = nn
                                    for l in st.session_state.lancamentos_reais:
                                        if l["conta"] == ca: l["conta"] = nn
                                save_db(); show_toast("Salvo!"); time.sleep(1); st.rerun()
                    with c4:
                        st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️ Excluir", type="secondary", use_container_width=True, key="btn_excluir_plano_conta_unico"):
                            st.session_state.plano_contas = [c for c in st.session_state.plano_contas if c["nome_conta"] != ca]
                            st.session_state.orcamentos = [o for o in st.session_state.orcamentos if o["conta"] != ca]
                            st.session_state.lancamentos_reais = [l for l in st.session_state.lancamentos_reais if l["conta"] != ca]
                            save_db(); show_toast("Excluído!"); time.sleep(1); st.rerun()

        with td:
            st.info("💡 Escolha a empresa modelo, marque as contas e aplique nas empresas de destino.")
            emp_op = {k: v["nome"] for k, v in st.session_state.db["empresas"].items() if v.get("ativo", True)}
            
            if not emp_op: st.warning("Nenhuma empresa cadastrada.")
            else:
                c_mod, c_dest = st.columns([4, 6])
                with c_mod: emp_modelo = st.selectbox("1. Empresa Modelo (Origem)", list(emp_op.keys()), format_func=lambda x: emp_op[x])
                
                plano_modelo = st.session_state.db["empresas"][emp_modelo]["dados"].get("plano_contas", [])
                
                if not plano_modelo: st.warning("A empresa modelo não possui contas cadastradas.")
                else:
                    st.markdown("<div style='margin-top: 15px; font-weight: 600;'>2. Selecione as Contas para Duplicar</div>", unsafe_allow_html=True)
                    df_pm = pd.DataFrame(plano_modelo)
                    df_pm.insert(0, "Duplicar?", True)
                    df_pm["Categoria DRE"] = df_pm["categoria_dre"].map({v: k for k, v in TIPO_MAPEAMENTO.items()})
                    df_pm_view = df_pm[["Duplicar?", "Categoria DRE", "nome_conta", "exige_faturamento"]].rename(columns={"nome_conta": "Subcategoria", "exige_faturamento": "Exige Faturamento?"})
                    ed_pm = st.data_editor(df_pm_view, hide_index=True, use_container_width=True, disabled=["Categoria DRE", "Subcategoria", "Exige Faturamento?"], column_config={"Duplicar?": st.column_config.CheckboxColumn("Duplicar?", width="small")})
                    
                    with c_dest:
                        emp_destinos = st.multiselect("3. Empresas de Destino", [k for k in emp_op.keys() if k != emp_modelo], format_func=lambda x: emp_op[x])
                        st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
                        if st.button("🔄 Duplicar Plano", type="primary", use_container_width=True, disabled=not emp_destinos):
                            contas_selecionadas = ed_pm[ed_pm["Duplicar?"] == True]["Subcategoria"].tolist()
                            contas_originais_filtradas = [c for c in plano_modelo if c["nome_conta"] in contas_selecionadas]
                            
                            for dest in emp_destinos:
                                plano_dest = st.session_state.db["empresas"][dest]["dados"].setdefault("plano_contas", [])
                                nomes_dest = [c["nome_conta"].lower() for c in plano_dest]
                                
                                for c_nova in contas_originais_filtradas:
                                    if c_nova["nome_conta"].lower() not in nomes_dest:
                                        plano_dest.append(c_nova.copy())
                            
                            save_db(); show_toast("Plano duplicado com sucesso!"); time.sleep(1.5); st.rerun()

        if st.session_state.plano_contas:
            st.markdown("<hr style='border-color: #E2E8F0; margin: 15px 0 10px 0;'><div class='saas-section-title' style='font-size: 14px; color: #64748B;'>Plano de Contas Ativo</div>", unsafe_allow_html=True)
            for ng_t, cg in TIPO_MAPEAMENTO.items():
                cdg = [c["nome_conta"] for c in st.session_state.plano_contas if c["categoria_dre"] == cg]
                if cdg:
                    with st.expander(f"{'📈' if cg in ['receita', 'outras_receitas'] else '📉' if cg in ['deducao', 'custo_variavel', 'despesa_operacional', 'outras_despesas'] else '💼'} {ng_t} ({len(cdg)})"):
                        st.dataframe(pd.DataFrame({"Conta": cdg}), use_container_width=True, hide_index=True)

    with tb:
        st.markdown("<div class='saas-section-title' style='margin-top: 15px;'>💰 Caixa Inicial</div>", unsafe_allow_html=True)
        c1, _ = st.columns([3, 7])
        with c1:
            if "input_saldo_ini" not in st.session_state: st.session_state["input_saldo_ini"] = formatar_moeda(st.session_state.saldo_inicial)
            st.text_input("Saldo", key="input_saldo_ini", on_change=aplicar_mascara_moeda, args=("input_saldo_ini",))
            if st.button("💾 Salvar Saldo", type="primary", use_container_width=True, key="btn_salvar_saldo_inicial"): st.session_state.saldo_inicial = parse_currency(st.session_state["input_saldo_ini"]); save_db(); show_toast("Salvo!"); time.sleep(1); st.rerun()

        st.markdown("<hr style='border-color: #E2E8F0; margin: 25px 0;'><div class='saas-section-title'>Novo Banco</div>", unsafe_allow_html=True)
        rb = st.session_state.get("reset_banco", 0)
        c1, c2, c3 = st.columns([3, 2, 2]); nb = c1.text_input("Banco", key=f"bn_{rb}"); gr = c2.text_input("Gerente", key=f"bg_{rb}"); wp = c3.text_input("WhatsApp", key=f"bw_{rb}", on_change=aplicar_mascara_telefone, args=(f"bw_{rb}",))
        c4, c5, c6 = st.columns([2, 2, 3]); ag = c4.text_input("Agência", key=f"ba_{rb}"); cc = c5.text_input("Conta", key=f"bc_{rb}")
        with c6:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Cadastrar Banco", type="primary", use_container_width=True, key="btn_cadastrar_banco"):
                if not nb.strip(): st.error("Digite o nome.")
                elif any(b["nome"].lower() == nb.lower() for b in st.session_state.bancos): st.error("Já existe.")
                else: st.session_state
