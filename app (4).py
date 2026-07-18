
import streamlit as st
import pandas as pd
import base64
import io
import requests
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

# --- Config ---
COMPANY_NAME = "KarArtz Jewellers"
GOLD_API_KEY = "goldapi-9a71fe00f592364fcbf030e1a6a549dd-io"

st.set_page_config(page_title="KarArtz POS", layout="wide")

# --- Session State ---
if 'items' not in st.session_state:
    st.session_state.items = []
if 'rates' not in st.session_state:
    st.session_state.rates = {"24KT": 0.0, "22KT": 0.0, "18KT": 0.0, "14KT": 0.0, "9KT": 0.0, "Silver": 0.0}

# --- Logic ---
def fetch_rates():
    headers = {"x-access-token": GOLD_API_KEY}
    try:
        g = requests.get("https://www.goldapi.io/api/XAU/INR", headers=headers).json()
        if "price_gram_24k" in g:
            p24 = round(g["price_gram_24k"], 2)
            st.session_state.rates.update({
                "24KT": p24,
                "22KT": round(p24 * (22/24), 2),
                "18KT": round(p24 * (18/24), 2),
                "14KT": round(p24 * (14/24), 2),
                "9KT": round(p24 * (9/24), 2)
            })
        s = requests.get("https://www.goldapi.io/api/XAG/INR", headers=headers).json()
        if "price_gram" in s: 
            st.session_state.rates["Silver"] = round(s["price_gram"], 2)
        st.success("Rates Updated!")
    except:
        st.error("API Fetch Failed")

def generate_pdf(customer_name, items):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=24)
    elements = [Paragraph(COMPANY_NAME, title_style), Paragraph(f"Customer: {customer_name}"), Spacer(1, 20)]
    
    data = [["Photo", "Item", "Weight", "Rate", "Total"]]
    for i in items:
        img = ""
        if i["Img"]:
            header, encoded = i["Img"].split(",", 1)
            img = RLImage(io.BytesIO(base64.b64decode(encoded)), width=0.7*inch, height=0.7*inch)
        
        data.append([img, i['Item'], f"{i['Net']}g", i['Rate'], f"{i['Amount']:.2f}"])

    t = Table(data, colWidths=[1*inch, 2*inch, 1*inch, 1*inch, 1.5*inch])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(t)
    doc.build(elements)
    return buf.getvalue()

# --- Sidebar ---
st.sidebar.header("Market Rates")
if st.sidebar.button("Fetch Live Rates"): fetch_rates()
rates = {}
for k in st.session_state.rates:
    rates[k] = st.sidebar.number_input(f"{k} Rate", value=st.session_state.rates[k])

# --- Main UI ---
st.title("KarArtz POS Terminal")
col1, col2 = st.columns([2, 1])

with col1:
    cust = st.text_input("Customer Name", "Walk-in")
    item_name = st.text_input("Item Description")
    m_col1, m_col2 = st.columns(2)
    m_type = m_col1.selectbox("Metal Type", list(st.session_state.rates.keys()))
    g_wt = m_col2.number_input("Gross Wt (g)", min_value=0.0)
    s_wt = st.number_input("Stone Wt (g)", min_value=0.0)
    making = st.number_input("Making Charge /g", min_value=0.0)

with col2:
    st.write("Item Photo")
    photo_input = st.camera_input("Capture")
    upload_input = st.file_uploader("Upload", type=['jpg','png'])
    
    img_str = None
    src = photo_input if photo_input else upload_input
    if src: img_str = f"data:image/jpeg;base64,{base64.b64encode(src.getvalue()).decode()}"

if st.button("Add to Invoice"):
    net = g_wt - s_wt
    amt = net * (rates[m_type] + making)
    st.session_state.items.append({"Item": item_name, "Net": net, "Rate": rates[m_type], "Amount": amt, "Img": img_str})

if st.session_state.items:
    st.table(pd.DataFrame(st.session_state.items)[["Item", "Net", "Amount"]])
    pdf = generate_pdf(cust, st.session_state.items)
    st.download_button("Download PDF", data=pdf, file_name="invoice.pdf")
    if st.button("Clear Invoice"): 
        st.session_state.items = []
        st.rerun()
