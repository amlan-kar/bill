import streamlit as st
import pandas as pd
import base64
import io
import requests
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# --- Config ---
COMPANY_NAME = "KARARTZ JEWELLERS"
COMPANY_DETAILS = "Exquisite Gold & Silver Jewelry | GSTIN: 07AAAAA0000A1Z5"
ADDRESS = "123 Jewel Lane, Gold Bazaar, Mumbai - 400001"
GOLD_API_KEY = "goldapi-9a71fe00f592364fcbf030e1a6a549dd-io"

st.set_page_config(page_title="KarArtz POS Premium", layout="wide")

# --- Custom CSS ---
st.markdown(f'''<style>
.main { background-color: #f5f7f9; }
.stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1a242f; color: white; }
.stDownloadButton>button { background-color: #27ae60 !important; color: white !important; }
h1 { color: #1a242f; }
</style>''', unsafe_allow_html=True)

# --- Initialization ---
if 'items' not in st.session_state:
    st.session_state['items'] = []
if 'rates' not in st.session_state:
    st.session_state['rates'] = {"24KT": 0.0, "22KT": 0.0, "18KT": 0.0, "14KT": 0.0, "9KT": 0.0, "Silver": 0.0}

def fetch_rates():
    headers = {"x-access-token": GOLD_API_KEY}
    try:
        g = requests.get("https://www.goldapi.io/api/XAU/INR", headers=headers).json()
        if "price_gram_24k" in g:
            p24 = round(g["price_gram_24k"], 2)
            st.session_state.rates.update({
                "24KT": p24, "22KT": round(p24 * (22/24), 2), "18KT": round(p24 * (18/24), 2),
                "14KT": round(p24 * (14/24), 2), "9KT": round(p24 * (9/24), 2)
            })
        s = requests.get("https://www.goldapi.io/api/XAG/INR", headers=headers).json()
        if "price_gram" in s: st.session_state.rates["Silver"] = round(s["price_gram"], 2)
        st.success("Rates Updated!")
    except: st.error("API connection failed.")

def generate_pdf(customer_name, items):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T', fontSize=22, textColor=colors.HexColor("#1a242f"), spaceAfter=10, fontName="Helvetica-Bold")
    header_style = ParagraphStyle('H', fontSize=10, textColor=colors.grey, spaceAfter=2)
    label_style = ParagraphStyle('L', fontSize=10, fontName="Helvetica-Bold")

    elements = []
    header_data = [[
        [Paragraph(COMPANY_NAME, title_style), Paragraph(COMPANY_DETAILS, header_style), Paragraph(ADDRESS, header_style)],
        [Paragraph("INVOICE", ParagraphStyle('Inv', fontSize=20, alignment=TA_RIGHT, textColor=colors.grey)),
         Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d-%b-%Y')}", ParagraphStyle('D', alignment=TA_RIGHT))]
    ]]
    header_table = Table(header_data, colWidths=[4*inch, 3*inch])
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=10, spaceAfter=15))
    
    elements.append(Paragraph(f"<b>BILL TO:</b> {customer_name}", label_style))
    elements.append(Spacer(1, 15))

    data = [["Item", "Metal", "Net Wt", "Charge Wt", "Rate/g", "Amount"]]
    for i in items:
        data.append([
            i.get('Item', '-'), i.get('Type', '-'), 
            f"{i.get('Net', 0)}g", f"{i.get('ChargeWt', 0)}g", 
            f"{i.get('TotalRate', 0):,.2f}", f"{i.get('Amount', 0):,.2f}"
        ])

    t = Table(data, colWidths=[2.2*inch, 0.8*inch, 0.9*inch, 1.0*inch, 1.1*inch, 1.3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a242f")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")])
    ]))
    elements.append(t)
    
    total_amt = sum(i.get('Amount', 0) for i in items)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"<div align='right'><b>GRAND TOTAL: INR {total_amt:,.2f}</b></div>", styles['Normal']))
    doc.build(elements)
    return buf.getvalue()

# --- UI ---
st.title("💎 KarArtz Premium POS")
with st.expander("📊 Live Market Rates"):
    if st.button("🔄 Sync Market Rates"): fetch_rates()
    r_cols = st.columns(6)
    for idx, (k, v) in enumerate(st.session_state.rates.items()):
        r_cols[idx].metric(k, f"₹{v:,.0f}")

col_main, col_side = st.columns([2, 1])
with col_main:
    st.subheader("📝 Item Entry")
    cust = st.text_input("Customer Name", "Walk-in")
    item_name = st.text_input("Item Description")
    c1, c2, c3 = st.columns(3)
    m_type = c1.selectbox("Metal Type", list(st.session_state.rates.keys()))
    g_wt = c2.number_input("Gross Wt (g)", min_value=0.0, step=0.001)
    s_wt = c3.number_input("Stone Wt (g)", min_value=0.0, step=0.001)
    making = st.number_input("Making Charge (per gram)", min_value=0.0)

    if st.button("➕ Add Item"):
        net = round(max(g_wt - s_wt, 0), 3)
        charge_wt = round(net * 1.15, 3)
        rate = st.session_state.rates[m_type]
        amt = round(charge_wt * (rate + making), 2)
        st.session_state['items'].append({"Item": item_name, "Type": m_type, "Net": net, "ChargeWt": charge_wt, "Rate": rate, "TotalRate": rate+making, "Amount": amt})
        st.rerun()

with col_side:
    st.subheader("📄 Invoice Summary")
    if st.session_state['items']:
        df = pd.DataFrame(st.session_state['items'])
        st.dataframe(df[["Item", "ChargeWt", "Amount"]], use_container_width=True)
        st.markdown(f"### Total: ₹{df['Amount'].sum():,.2f}")
        pdf_data = generate_pdf(cust, st.session_state['items'])
        st.download_button("📥 Download PDF", data=pdf_data, file_name=f"Invoice_{cust}.pdf")
        if st.button("🗑️ Clear All"): 
            st.session_state['items'] = []
            st.rerun()
    else: st.info("No items added.")
