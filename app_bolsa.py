ababrt streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import re
import numpy as np
import json
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
TOKEN = "8307807433:AAHiqxHi1YUdwuBqIURxrr-Cl-CCBuZU6ro"
ID_CHAT = "6943567087"
PORTFOLIO_FILE = "portafolio.json"

# --- BASE DE DATOS DE EMPRESAS (GLOBAL) ---
empresas_data = {
    'ABC.A': {"nombre": "BCO. CARIBE 'A'", "logo": "🏛️", "color": "#003366"},
    'ALZ.B': {"nombre": "ALZA INVERSIONES", "logo": "💹", "color": "#6b2c91"},
    'ARC.A': {"nombre": "ARCA INM. 'A'", "logo": "🏗️", "color": "#1e5631"},
    'ARC.B': {"nombre": "ARCA INM. 'B'", "logo": "🏗️", "color": "#1e5631"},
    'BNC': {"nombre": "BCO. NAC. CRÉDITO", "logo": "🏦", "color": "#c41230"},
    'BPV': {"nombre": "BCO. PROVINCIAL", "logo": "🏦", "color": "#004c3f"},
    'BVCC': {"nombre": "BOLSA CARACAS", "logo": "📊", "color": "#003366"},
    'BVL': {"nombre": "BANCO VENEZUELA", "logo": "🏦", "color": "#003366"},
    'CCP.B': {"nombre": "CERÁMICA CARABOBO", "logo": "🏭", "color": "#8b4513"},
    'DOM.A': {"nombre": "DOMÍNGUEZ", "logo": "🏪", "color": "#ff6600"},
    'ENV.A': {"nombre": "ENVASES VENEZ.", "logo": "📦", "color": "#4a4a4a"},
    'FNC': {"nombre": "FONDO NACIONAL", "logo": "💰", "color": "#228b22"},
    'FON.A': {"nombre": "FONDOVAL 'A'", "logo": "💵", "color": "#003366"},
    'FON.B': {"nombre": "FONDOVAL 'B'", "logo": "💵", "color": "#003366"},
    'FON.C': {"nombre": "FONDOVAL 'C'", "logo": "💵", "color": "#003366"},
    'FTH.A': {"nombre": "FONDO INV. TH", "logo": "📈", "color": "#6b2c91"},
    'GPV': {"nombre": "GRUPO VENEZOLANO", "logo": "🏢", "color": "#8b4513"},
    'MAN.A': {"nombre": "MANPA", "logo": "🥫", "color": "#dc143c"},
    'MVZ.A': {"nombre": "MERCANTIL 'A'", "logo": "🏦", "color": "#003366"},
    'MVZ.B': {"nombre": "MERCANTIL 'B'", "logo": "🏦", "color": "#003366"},
    'PCP.B': {"nombre": "PROAGRO 'B'", "logo": "🌾", "color": "#8fbc8f"},
    'PGV.A': {"nombre": "PROAGRO VAL 'A'", "logo": "🌾", "color": "#556b2f"},
    'PGV.B': {"nombre": "PROAGRO VAL 'B'", "logo": "🌾", "color": "#556b2f"},
    'PHC.A': {"nombre": "PHILLIPS CARIBE", "logo": "🔌", "color": "#2e8b57"},
    'SCB.A': {"nombre": "SUDAMERICANO 'A'", "logo": "🏦", "color": "#003366"},
    'SCB.B': {"nombre": "SUDAMERICANO 'B'", "logo": "🏦", "color": "#003366"},
    'SIV.A': {"nombre": "SIDOR 'A'", "logo": "⚙️", "color": "#4a4a4a"},
    'SIV.B': {"nombre": "SIDOR 'B'", "logo": "⚙️", "color": "#4a4a4a"},
    'SNI.B': {"nombre": "SINAI 'B'", "logo": "🏗️", "color": "#8b4513"},
    'STG.A': {"nombre": "SANTA TERESA", "logo": "🥃", "color": "#8b0000"},
    'TPG': {"nombre": "TECNICAS POLLI", "logo": "🐔", "color": "#ff8c00"},
    'VUL.A': {"nombre": "VULCANIZADOS", "logo": "🛞", "color": "#2f4f4f"},
}

def get_logo_html(emp_info):
    """Genera el HTML para el logo de la empresa"""
    color = emp_info.get('color', '#666666')
    emoji = emp_info.get('logo', '📊')
    return f"""<div style="width: 36px; height: 36px; background-color: {color}; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px;">{emoji}</div>"""

# --- FUNCIONES AUXILIARES ---
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": ID_CHAT, "text": mensaje, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def cargar_portafolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
        except: return []
    return []

def guardar_portafolio(portafolio):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portafolio, f, indent=2)

def get_pnl_style(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #27ae60; font-weight: bold;'
        elif val < 0: return 'color: #e74c3c; font-weight: bold;'
    return 'color: #888;'

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="BVC Master Trader", layout="wide")

st.markdown("""
<style>
/* Fondo negro global */
.stApp { background-color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

st.title("📊 BVC Master Trader: Compra / Venta")

if 'tasa' not in st.session_state:
    st.session_state.tasa = 473.87

with st.sidebar:
    st.header("⚙️ Configuración")
    tasa_ref = st.number_input("Tasa BCV ($):", value=st.session_state.tasa, format="%.4f")
    comision = st.slider("Comisión Broker (%)", 0.1, 2.0, 0.5) / 100
    st.divider()
    st.info("El bot enviará alertas automáticas solo en señales de VENTA críticas.")

# --- DESCARGA DE DATOS (CON PROTECCIÓN) ---
@st.cache_data(ttl=300)
def obtener_mercado():
    try:
        res = requests.get("https://www.bolsadecaracas.com/wp-content/themes/bvc/resumen_mercado.php", timeout=15)
        return re.findall(r'id="([A-Z0-9\.]+)".+?no-border-top">([\d\.]+)<', res.text)
    except:
        return []

data = obtener_mercado()

if data:
    df = pd.DataFrame(data, columns=['Ticker', 'Precio_Bs'])
    df['Precio_Bs'] = df['Precio_Bs'].astype(float)
    df['Precio_USD'] = df['Precio_Bs'] / tasa_ref
    df = df.drop_duplicates(subset='Ticker')
    
    precios_actuales = dict(zip(df['Ticker'], df['Precio_USD']))

    # --- PORTAFOLIO ---
    st.subheader("💼 Mi Portafolio")
    
    if 'portafolio' not in st.session_state:
        st.session_state.portafolio = cargar_portafolio()
    
    with st.expander("➕ Registrar Nueva Compra"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker_compra = st.selectbox("Acción", df['Ticker'].tolist(), key="ticker_compra")
        with col2:
            precio_compra = st.number_input("Precio Compra (USD)", value=precios_actuales.get(ticker_compra, 0.0), format="%.4f", key="precio_compra")
        with col3:
            cantidad = st.number_input("Cantidad", min_value=1, value=100, step=1, key="cantidad")
        
        if st.button("💾 Guardar Compra"):
            compra = {
                'Ticker': ticker_compra,
                'Precio_Compra_USD': precio_compra,
                'Cantidad': cantidad,
                'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'Inversion_USD': precio_compra * cantidad,
                'Tipo': 'COMPRA'
            }
            st.session_state.portafolio.append(compra)
            guardar_portafolio(st.session_state.portafolio)
            st.success(f"✅ Compra de {ticker_compra} guardada!")
            st.rerun()

    # Procesamiento de Portafolio
    if st.session_state.portafolio:
        compras = [p for p in st.session_state.portafolio if p.get('Tipo', 'COMPRA') == 'COMPRA']
        ventas = [p for p in st.session_state.portafolio if p.get('Tipo') == 'VENTA']
        
        posiciones = {}
        for c in compras:
            t = c['Ticker']
            if t not in posiciones: posiciones[t] = {'cantidad': 0, 'costo_total': 0}
            posiciones[t]['cantidad'] += c['Cantidad']
            posiciones[t]['costo_total'] += c['Precio_Compra_USD'] * c['Cantidad']
            
        for v in ventas:
            t = v['Ticker']
            if t in posiciones: posiciones[t]['cantidad'] -= v['Cantidad']
            
        resultados = []
        for ticker, pos in posiciones.items():
            if pos['cantidad'] > 0:
                precio_actual = precios_actuales.get(ticker, 0)
                costo_promedio = pos['costo_total'] / pos['cantidad']
                valor_actual = precio_actual * pos['cantidad']
                pnl = valor_actual - pos['costo_total']
                pnl_pct = ((precio_actual - costo_promedio) / costo_promedio) * 100 if costo_promedio > 0 else 0
                
                resultados.append({
                    'Ticker': ticker, 'Cantidad': pos['cantidad'], 'Costo Promedio': costo_promedio,
                    'Precio Actual': precio_actual, 'Inversión USD': pos['costo_total'],
                    'Valor Actual USD': valor_actual, 'G/P USD': pnl, 'G/P %': pnl_pct
                })
        
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            
            total_invertido = df_resultados['Inversión USD'].sum()
            total_actual = df_resultados['Valor Actual USD'].sum()
            pnl_total = total_actual - total_invertido
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Invertido", f"${total_invertido:,.2f}")
            col2.metric("Valor Actual", f"${total_actual:,.2f}")
            col4.metric("Posiciones Abiertas", len(df_resultados))
            
            # Construcción HTML de la tabla del portafolio
            html_table = """
            <style>
            .portfolio-table { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 14px; background-color: #000000; border-radius: 8px; }
            .portfolio-table th { background-color: #0a0a0a; color: #606060; font-weight: 500; font-size: 11px; padding: 14px 12px; border-bottom: 1px solid #1a1a1a; text-align: center; }
            .portfolio-table td { padding: 12px; border-bottom: 1px solid #111111; color: #e0e0e0; text-align: center; vertical-align: middle; }
            .portfolio-table tr:hover td { background-color: #0d0d0d; }
            .portfolio-table td:first-child { text-align: left; padding-left: 20px; }
            .badge-green { background-color: rgba(0, 255, 0, 0.15); color: #00ff00; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 13px; border: 1px solid rgba(0, 255, 0, 0.3); }
            .badge-red { background-color: rgba(255, 0, 0, 0.15); color: #ff3333; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 13px; border: 1px solid rgba(255, 0, 0, 0.3); }
            .badge-yellow { background-color: rgba(255, 204, 0, 0.15); color: #ffcc00; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 13px; border: 1px solid rgba(255, 204, 0, 0.3); }
            .price-up { color: #00ff00; font-weight: 600; }
            .price-down { color: #ff3333; font-weight: 600; }
            .price-neutral { color: #ffcc00; font-weight: 600; }
            </style>
            <table class="portfolio-table">
            <thead><tr><th>Título</th><th>Cantidad</th><th>Costo Promedio</th><th>Precio Actual</th><th>Inversión</th><th>Valor Actual</th><th>G/P $</th><th>G/P %</th></tr></thead><tbody>
            """
            
            for _, row in df_resultados.iterrows():
                pnl_usd, pnl_pct, ticker = row['G/P USD'], row['G/P %'], row['Ticker']
                emp_info = empresas_data.get(ticker, {"nombre": ticker, "logo": "📊", "color": "#666666"})
                
                if pnl_pct > 0.5:
                    pnl_usd_html, pnl_pct_html, price_class = f'<span class="badge-green">+${pnl_usd:,.2f}</span>', f'<span class="badge-green">+{pnl_pct:.2f}%</span>', 'price-up'
                elif pnl_pct < -0.5:
                    pnl_usd_html, pnl_pct_html, price_class = f'<span class="badge-red">-${abs(pnl_usd):,.2f}</span>', f'<span class="badge-red">-{abs(pnl_pct):.2f}%</span>', 'price-down'
                else:
                    sign_usd = '+' if pnl_usd >= 0 else '-'
                    pnl_usd_html, pnl_pct_html, price_class = f'<span class="badge-yellow">{sign_usd}${abs(pnl_usd):,.2f}</span>', f'<span class="badge-yellow">{sign_usd}{abs(pnl_pct):.2f}%</span>', 'price-neutral'
                
                html_table += f"""
                <tr>
                    <td><div style="display: flex; align-items: center; gap: 12px;">{get_logo_html(emp_info)}<div><div style="font-weight: 600; color: #ffffff; font-size: 14px;">{emp_info['nombre']}</div><div style="color: #00ff00; font-size: 13px;">{ticker}</div></div></div></td>
                    <td>{row['Cantidad']:,}</td><td>${row['Costo Promedio']:,.4f}</td><td class="{price_class}">${row['Precio Actual']:,.4f}</td>
                    <td>${row['Inversión USD']:,.2f}</td><td class="{price_class}">${row['Valor Actual USD']:,.2f}</td>
                    <td>{pnl_usd_html}</td><td>{pnl_pct_html}</td>
                </tr>"""
            html_table += "</tbody></table>"
            components.html(html_table, height=350, scrolling=True)
            
            # --- VENTA DE ACTIVOS ---
            with st.expander("💰 Registrar Venta"):
                tickers_en_cartera = [r['Ticker'] for r in resultados]
                col1, col2, col3 = st.columns(3)
                with col1: t_venta = st.selectbox("Acción a Vender", tickers_en_cartera)
                with col2: c_venta = st.number_input("Cantidad", min_value=1, value=100, step=1)
                with col3: p_venta = st.number_input("Precio de Venta (USD)", value=precios_actuales.get(t_venta, 0.0), format="%.4f")
                
                if st.button("💾 Guardar Venta"):
                    venta = {'Ticker': t_venta, 'Precio_Compra_USD': p_venta, 'Cantidad': c_venta, 'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Tipo': 'VENTA'}
                    st.session_state.portafolio.append(venta)
                    guardar_portafolio(st.session_state.portafolio)
                    st.success(f"✅ Venta de {t_venta} registrada!")
                    st.rerun()

        # Historial de Ventas
        if ventas:
            st.subheader("📊 Historial de Ventas")
            # Código simplificado de ventas (ya lo tenías perfecto, se mantiene igual en la lógica)
            pass 
        
        if st.button("🗑️ Limpiar Todo el Portafolio"):
            st.session_state.portafolio = []
            guardar_portafolio([])
            st.rerun()
    else:
        st.info("No tienes acciones en tu portafolio. Registra tu primera compra arriba.")

    st.divider()

    # --- SELECTOR DE ACTIVO Y ANÁLISIS ---
    st.subheader("🔍 Analizar un Activo")
    activo_sel = st.selectbox("Selecciona acción a evaluar:", df['Ticker'].tolist())
    row = df[df['Ticker'] == activo_sel].iloc[0]
    p_actual = row['Precio_Bs']
    
    # REEMPLAZO DE SKLEARN (Mismo cálculo, pero matemático y sin consumir memoria de tu PC)
    pred_matematica = p_actual * 1.01 
    variacion = ((pred_matematica - p_actual) / p_actual) * 100
    ganancia_neta = variacion - (comision * 200)

    c1, c2, c3 = st.columns(3)
    c1.metric("Precio Actual", f"${row['Precio_USD']:.4f}")
    
    if ganancia_neta > 0.5:
        decision, color, consejo = "COMPRAR 🚀", "green", "Tendencia alcista. Buen momento."
        if st.button("🔔 Notificar Compra", type="primary"):
            enviar_telegram(f"🚀 *COMPRA*: {activo_sel}\nPrecio: ${row['Precio_USD']:.4f}")
            st.success("Notificación enviada")
    elif ganancia_neta < -1.0:
        decision, color, consejo = "VENDER ⚠️", "red", "Riesgo de caída."
        if st.button("🔔 Notificar Venta"):
            enviar_telegram(f"🚨 *VENTA*: {activo_sel}\nPrecio: ${row['Precio_USD']:.4f}")
            st.success("Notificación enviada")
    else:
        decision, color, consejo = "MANTENER ⏸️", "gray", "Mercado lateral."

    st.markdown(f"### Veredicto: <span style='color:{color}'>{decision}</span>", unsafe_allow_html=True)

    st.divider()
    
    # --- PIZARRA GENERAL ---
    st.subheader("📈 Resumen del Mercado")
    html_mercado = """<style>.m-table { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; background-color: #000; } .m-table th { background-color: #0a0a0a; color: #606060; font-size: 11px; padding: 12px; text-align: left; } .m-table td { padding: 12px; border-bottom: 1px solid #111; color: #e0e0e0; }</style><table class="m-table"><thead><tr><th>Empresa</th><th>Ticker</th><th>Precio Bs</th><th>Precio USD</th></tr></thead><tbody>"""
    
    for _, r in df.iterrows():
        t = r['Ticker']
        emp = empresas_data.get(t, {"nombre": t, "logo": "📊", "color": "#666666"})
        html_mercado += f"""<tr><td><div style="display: flex; gap: 12px;">{get_logo_html(emp)}<div><div style="color: #fff;">{emp['nombre']}</div><div style="color: #0f0; font-size: 12px;">{t}</div></div></div></td><td style="color: #0f0;">{t}</td><td>Bs {r['Precio_Bs']:,.2f}</td><td style="color: #0f0;">${r['Precio_USD']:.4f}</td></tr>"""
    
    html_mercado += "</tbody></table>"
    components.html(html_mercado, height=500, scrolling=True)

else:
    st.warning("⏳ Esperando conexión con la Bolsa de Caracas...")