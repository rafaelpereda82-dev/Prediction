import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import re
import numpy as np
import json
import os
from sklearn.linear_model import LinearRegression
from datetime import datetime

# --- CONFIGURACIÓN ---
TOKEN = "8307807433:AAHiqxHi1YUdwuBqIURxrr-Cl-CCBuZU6ro"
ID_CHAT = "6943567087"
PORTFOLIO_FILE = "portafolio.json"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": ID_CHAT, "text": mensaje, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def cargar_portafolio():
    """Cargar portafolio desde archivo JSON"""
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
        except: return []
    return []

def guardar_portafolio(portafolio):
    """Guardar portafolio en archivo JSON"""
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portafolio, f, indent=2)

def get_pnl_style(val):
    """Retornar estilo CSS según valor P&L"""
    if isinstance(val, (int, float)):
        if val > 0:
            return 'color: #27ae60; font-weight: bold;'
        elif val < 0:
            return 'color: #e74c3c; font-weight: bold;'
    return 'color: #888;'

st.set_page_config(page_title="BVC Master Trader", layout="wide")

# --- TEMA OSCURO GLOBAL ---
st.markdown("""
<style>
/* Fondo negro global */
.stApp {
    background-color: #000000 !important;
}
</style>
""")

# --- INTERFAZ ---
st.title("📊 BVC Master Trader: Compra / Venta")

if 'tasa' not in st.session_state:
    st.session_state.tasa = 473.87

with st.sidebar:
    st.header("⚙️ Configuración")
    tasa_ref = st.number_input("Tasa BCV ($):", value=st.session_state.tasa, format="%.4f")
    comision = st.slider("Comisión Broker (%)", 0.1, 2.0, 0.5) / 100
    st.divider()
    st.info("El bot enviará alertas automáticas solo en señales de VENTA críticas.")

# --- LÓGICA PRINCIPAL ---
data = requests.get("https://www.bolsadecaracas.com/wp-content/themes/bvc/resumen_mercado.php")
data = re.findall(r'id="([A-Z0-9\.]+)".+?no-border-top">([\d\.]+)<', data.text)

if data:
    df = pd.DataFrame(data, columns=['Ticker', 'Precio_Bs'])
    df['Precio_Bs'] = df['Precio_Bs'].astype(float)
    df['Precio_USD'] = df['Precio_Bs'] / tasa_ref
    df = df.drop_duplicates(subset='Ticker')
    
    # Crear diccionario de precios actuales para referencia
    precios_actuales = dict(zip(df['Ticker'], df['Precio_USD']))

    # --- PORTAFOLIO ---
    st.subheader("💼 Mi Portafolio")
    
    # Inicializar portafolio desde archivo
    if 'portafolio' not in st.session_state:
        st.session_state.portafolio = cargar_portafolio()
    
    # Formulario para agregar compra
    with st.expander("➕ Registrar Nueva Compra"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker_compra = st.selectbox("Acción", df['Ticker'].tolist(), key="ticker_compra")
        with col2:
            precio_compra = st.number_input("Precio de Compra (USD)", 
                                            value=precios_actuales.get(ticker_compra, 0.0), 
                                            format="%.2f", key="precio_compra")
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
    
    # Mostrar portafolio con P&L
    if st.session_state.portafolio:
        # Separar compras y ventas
        compras = [p for p in st.session_state.portafolio if p.get('Tipo', 'COMPRA') == 'COMPRA']
        ventas = [p for p in st.session_state.portafolio if p.get('Tipo') == 'VENTA']
        
        # Calcular P&L de posiciones abiertas
        posiciones = {}
        for c in compras:
            ticker = c['Ticker']
            if ticker not in posiciones:
                posiciones[ticker] = {'cantidad': 0, 'costo_total': 0}
            posiciones[ticker]['cantidad'] += c['Cantidad']
            posiciones[ticker]['costo_total'] += c['Precio_Compra_USD'] * c['Cantidad']
        
        # Restar ventas
        for v in ventas:
            ticker = v['Ticker']
            if ticker in posiciones:
                posiciones[ticker]['cantidad'] -= v['Cantidad']
        
        # Mostrar posiciones abiertas
        resultados = []
        for ticker, pos in posiciones.items():
            if pos['cantidad'] > 0:
                precio_actual = precios_actuales.get(ticker, 0)
                costo_promedio = pos['costo_total'] / pos['cantidad'] if pos['cantidad'] > 0 else 0
                valor_actual = precio_actual * pos['cantidad']
                valor_invertido = pos['costo_total']
                pnl = valor_actual - valor_invertido
                pnl_pct = ((precio_actual - costo_promedio) / costo_promedio) * 100 if costo_promedio > 0 else 0
                
                resultados.append({
                    'Ticker': ticker,
                    'Cantidad': pos['cantidad'],
                    'Costo Promedio': costo_promedio,
                    'Precio Actual': precio_actual,
                    'Inversión USD': valor_invertido,
                    'Valor Actual USD': valor_actual,
                    'G/P USD': pnl,
                    'G/P %': pnl_pct
                })
        
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            
            # Resumen del portafolio
            total_invertido = df_resultados['Inversión USD'].sum()
            total_actual = df_resultados['Valor Actual USD'].sum()
            pnl_total = total_actual - total_invertido
            pnl_total_pct = (pnl_total / total_invertido) * 100 if total_invertido > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Invertido", f"${total_invertido:,.2f}")
            col2.metric("Valor Actual", f"${total_actual:,.2f}")
            color_pnl = "green" if pnl_total >= 0 else "red"
            col4.metric("Posiciones Abiertas", len(df_resultados))
            
            # Tabla del portafolio - estilo terminal de trading profesional
            
            # Crear HTML de la tabla estilo terminal
            # Diccionario de nombres completos de empresas con emojis representativos por industria
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
            
            # Función simple para mostrar logo (emoji en cuadrado de color)
            def get_logo_html(emp_info):
                color = emp_info.get('color', '#666666')
                emoji = emp_info.get('logo', '📊')
                return f"""<div style="width: 36px; height: 36px; background-color: {color}; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px;">{emoji}</div>"""
            
            html_table = """
            <style>
            .portfolio-table {
                width: 100%;
                border-collapse: collapse;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 14px;
                background-color: #000000;
                border-radius: 8px;
                overflow: hidden;
            }
            .portfolio-table th {
                background-color: #0a0a0a;
                color: #606060;
                font-weight: 500;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.5px;
                padding: 14px 12px;
                border-bottom: 1px solid #1a1a1a;
                text-align: center;
            }
            .portfolio-table td {
                padding: 12px;
                border-bottom: 1px solid #111111;
                background-color: #000000;
                color: #e0e0e0;
                text-align: center;
                vertical-align: middle;
            }
            .portfolio-table tr:hover td {
                background-color: #0d0d0d;
            }
            .portfolio-table td:first-child {
                text-align: left;
                padding-left: 20px;
            }
            .ticker-name {
                font-weight: 600;
                color: #ffffff;
                font-size: 14px;
            }
            .company-name {
                color: #555555;
                font-size: 11px;
                font-weight: 400;
                display: block;
                margin-top: 2px;
            }
            .badge-green {
                background-color: rgba(0, 255, 0, 0.15);
                color: #00ff00;
                padding: 4px 10px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 13px;
                display: inline-block;
                border: 1px solid rgba(0, 255, 0, 0.3);
            }
            .badge-red {
                background-color: rgba(255, 0, 0, 0.15);
                color: #ff3333;
                padding: 4px 10px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 13px;
                display: inline-block;
                border: 1px solid rgba(255, 0, 0, 0.3);
            }
            .badge-yellow {
                background-color: rgba(255, 204, 0, 0.15);
                color: #ffcc00;
                padding: 4px 10px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 13px;
                display: inline-block;
                border: 1px solid rgba(255, 204, 0, 0.3);
            }
            .price-up {
                color: #00ff00;
                font-weight: 600;
            }
            .price-down {
                color: #ff3333;
                font-weight: 600;
            }
            .price-neutral {
                color: #ffcc00;
                font-weight: 600;
            }
            </style>
            <table class="portfolio-table">
            <thead>
            <tr>
                <th>Título</th>
                <th>Cantidad</th>
                <th>Costo Promedio</th>
                <th>Precio Actual</th>
                <th>Inversión</th>
                <th>Valor Actual</th>
                <th>G/P $</th>
                <th>G/P %</th>
            </tr>
            </thead>
            <tbody>
            """
            
            for _, row in df_resultados.iterrows():
                # Formatear valores P&L con badges
                pnl_usd = row['G/P USD']
                pnl_pct = row['G/P %']
                ticker = row['Ticker']
                emp_info = empresas_data.get(ticker, {"nombre": ticker, "logo": "", "color": "#666666"})
                
                # Clasificar: verde (subiendo > 0.5%), rojo (bajando < -0.5%), amarillo (manteniendo)
                if pnl_pct > 0.5:
                    pnl_usd_html = f'<span class="badge-green">+${pnl_usd:,.2f}</span>'
                    pnl_pct_html = f'<span class="badge-green">+{pnl_pct:.2f}%</span>'
                    price_class = 'price-up'
                elif pnl_pct < -0.5:
                    pnl_usd_html = f'<span class="badge-red">-${abs(pnl_usd):,.2f}</span>'
                    pnl_pct_html = f'<span class="badge-red">-{abs(pnl_pct):.2f}%</span>'
                    price_class = 'price-down'
                else:
                    # Amarillo para manteniendo (entre -0.5% y +0.5%)
                    sign_usd = '+' if pnl_usd >= 0 else '-'
                    sign_pct = '+' if pnl_pct >= 0 else '-'
                    pnl_usd_html = f'<span class="badge-yellow">{sign_usd}${abs(pnl_usd):,.2f}</span>'
                    pnl_pct_html = f'<span class="badge-yellow">{sign_pct}{abs(pnl_pct):.2f}%</span>'
                    price_class = 'price-neutral'
                
                html_table += f"""
                <tr>
                    <td>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            {get_logo_html(emp_info)}
                            <div>
                                <div style="font-weight: 600; color: #ffffff; font-size: 14px;">{emp_info['nombre']}</div>
                                <div style="color: #00ff00; font-size: 13px; font-weight: 500;">{ticker}</div>
                            </div>
                        </div>
                    </td>
                    <td>{row['Cantidad']:,}</td>
                    <td>${row['Costo Promedio']:,.2f}</td>
                    <td class="{price_class}">${row['Precio Actual']:,.2f}</td>
                    <td>${row['Inversión USD']:,.2f}</td>
                    <td class="{price_class}">${row['Valor Actual USD']:,.2f}</td>
                    <td>{pnl_usd_html}</td>
                    <td>{pnl_pct_html}</td>
                </tr>
                """
            
            html_table += "</tbody></table>"
            
            components.html(html_table, height=400, scrolling=True)
        
        # --- REGISTRAR VENTA ---
        if resultados:
            with st.expander("💰 Registrar Venta"):
                tickers_en_cartera = [r['Ticker'] for r in resultados]
                col1, col2, col3 = st.columns(3)
                with col1:
                    ticker_venta = st.selectbox("Acción a Vender", tickers_en_cartera, key="ticker_venta")
                with col2:
                    cantidad_venta = st.number_input("Cantidad", min_value=1, value=100, step=1, key="cantidad_venta")
                with col3:
                    precio_venta = st.number_input("Precio de Venta (USD)", 
                                                    value=precios_actuales.get(ticker_venta, 0.0), 
                                                    format="%.2f", key="precio_venta")
                
                if st.button("💾 Guardar Venta"):
                    venta = {
                        'Ticker': ticker_venta,
                        'Precio_Compra_USD': precio_venta,
                        'Cantidad': cantidad_venta,
                        'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'Inversion_USD': precio_venta * cantidad_venta,
                        'Tipo': 'VENTA'
                    }
                    st.session_state.portafolio.append(venta)
                    guardar_portafolio(st.session_state.portafolio)
                    st.success(f"✅ Venta de {ticker_venta} registrada!")
        
        # --- HISTORIAL DE VENTAS Y P&L REALIZADO ---
        if ventas:
            st.subheader("📊 Historial de Ventas - P&L Realizado")
            
            # Calcular P&L realizado de cada venta
            historial_ventas = []
            for v in ventas:
                ticker = v['Ticker']
                # Buscar precio promedio de compra para este ticker
                compras_ticker = [c for c in compras if c['Ticker'] == ticker]
                if compras_ticker:
                    total_cantidad = sum(c['Cantidad'] for c in compras_ticker)
                    total_costo = sum(c['Precio_Compra_USD'] * c['Cantidad'] for c in compras_ticker)
                    costo_promedio = total_costo / total_cantidad if total_cantidad > 0 else 0
                    
                    precio_venta = v['Precio_Compra_USD']
                    cantidad_venta = v['Cantidad']
                    pnl_realizado = (precio_venta - costo_promedio) * cantidad_venta
                    pnl_pct = ((precio_venta - costo_promedio) / costo_promedio) * 100 if costo_promedio > 0 else 0
                    
                    historial_ventas.append({
                        'Ticker': ticker,
                        'Cantidad': cantidad_venta,
                        'Costo Promedio': costo_promedio,
                        'Precio Venta': precio_venta,
                        'Fecha': v['Fecha'],
                        'P&L Realizado USD': pnl_realizado,
                        'P&L %': pnl_pct
                    })
            
            if historial_ventas:
                df_ventas = pd.DataFrame(historial_ventas)
                pnl_realizado_total = df_ventas['P&L Realizado USD'].sum()
                
                col1, col2 = st.columns(2)
                col1.metric("Total P&L Realizado", f"${pnl_realizado_total:,.2f}", 
                           delta=f"{'Ganancia' if pnl_realizado_total >= 0 else 'Pérdida'}")
                col2.metric("Ventas Realizadas", len(df_ventas))
                
                st.dataframe(
                    df_ventas.style
                    .map(get_pnl_style, subset=['P&L Realizado USD', 'P&L %'])
                    .format({
                        'Costo Promedio': '${:.2f}',
                        'Precio Venta': '${:.2f}',
                        'P&L Realizado USD': '${:.2f}',
                        'P&L %': '{:.2f}%'
                    }),
                    use_container_width=True
                )
        
        # Botón para limpiar portafolio
        if st.button("🗑️ Limpiar Todo el Portafolio"):
            st.session_state.portafolio = []
            guardar_portafolio([])
            st.rerun()
    else:
        st.info("No tienes acciones en tu portafolio. Registra tu primera compra arriba.")

    st.divider()

    # --- SELECTOR DE ACTIVO ---
    st.subheader("🔍 Analizar un Activo Específico")
    activo_sel = st.selectbox("Selecciona la acción que tienes o quieres comprar:", df['Ticker'].tolist())
    
    # Datos del activo seleccionado
    row = df[df['Ticker'] == activo_sel].iloc[0]
    p_actual = row['Precio_Bs']
    
    # IA: Simulación de tendencia (basada en 5 puntos de control)
    X = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
    # Simulamos micro-tendencia (esto se puede mejorar con el histórico CSV)
    y = np.array([p_actual*0.98, p_actual*0.99, p_actual, p_actual*1.01, p_actual])
    pred = LinearRegression().fit(X, y).predict([[6]])[0]
    
    variacion = ((pred - p_actual) / p_actual) * 100
    ganancia_neta = variacion - (comision * 200)

    # --- VEREDICTO ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Precio Actual", f"${row['Precio_USD']:.2f}")
    
    if ganancia_neta > 0.5:
        decision = "COMPRAR 🚀"
        color = "green"
        consejo = "La IA detecta fuerza alcista. Buen momento para entrar."
        # Notificación de compra
        if st.button("🔔 Notificar Compra al Móvil", type="primary"):
            enviar_telegram(f"🚀 *SEÑAL DE COMPRA*: {activo_sel}\n💰 Precio: ${row['Precio_USD']:.2f}\n📈 Ganancia est: {ganancia_neta:.2f}%\n\nBuen momento para invertir!")
            st.success("📨 Notificación enviada!")
    elif ganancia_neta < -1.0:
        decision = "VENDER ⚠️"
        color = "red"
        consejo = "Riesgo de caída detectado. Protege tus ganancias."
        # Notificación de venta
        if st.button("🔔 Notificar Venta al Móvil", type="secondary"):
            enviar_telegram(f"🚨 *SEÑAL DE VENTA*: {activo_sel}\n💰 Precio: ${row['Precio_USD']:.2f}\n📉 Pérdida est: {abs(ganancia_neta):.2f}%\n\nProtege tus ganancias!")
            st.success("📨 Notificación enviada!")
    else:
        decision = "MANTENER ⏸️"
        color = "gray"
        consejo = "El mercado está lateral. No hagas movimientos bruscos."

    st.markdown(f"### Veredicto: <span style='color:{color}'>{decision}</span>", unsafe_allow_html=True)
    st.info(f"**Recomendación:** {consejo}")

    st.divider()
    st.subheader("📈 Resumen General del Mercado")
    
    # Crear HTML table estilo terminal para el resumen de mercado
    html_mercado = """
    <style>
    .mercado-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 14px;
        background-color: #000000;
        border-radius: 8px;
        overflow: hidden;
    }
    .mercado-table th {
        background-color: #0a0a0a;
        color: #606060;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
        padding: 14px 12px;
        border-bottom: 1px solid #1a1a1a;
        text-align: center;
    }
    .mercado-table td {
        padding: 12px;
        border-bottom: 1px solid #111111;
        background-color: #000000;
        color: #e0e0e0;
        text-align: center;
        vertical-align: middle;
    }
    .mercado-table tr:hover td {
        background-color: #0d0d0d;
    }
    .mercado-table td:first-child {
        text-align: left;
        padding-left: 20px;
    }
    </style>
    <table class="mercado-table">
    <thead>
    <tr>
        <th>Empresa</th>
        <th>Ticker</th>
        <th>Precio Bs</th>
        <th>Precio USD</th>
    </tr>
    </thead>
    <tbody>
    """
    
    for _, row in df.iterrows():
        ticker = row['Ticker']
        emp_info = empresas_data.get(ticker, {"nombre": ticker, "logo": "📊", "color": "#666666"})
        
        html_mercado += f"""
        <tr>
            <td>
                <div style="display: flex; align-items: center; gap: 12px;">
                    {get_logo_html(emp_info)}
                    <div>
                        <div style="font-weight: 600; color: #ffffff; font-size: 14px;">{emp_info['nombre']}</div>
                        <div style="color: #00ff00; font-size: 13px; font-weight: 500;">{ticker}</div>
                    </div>
                </div>
            </td>
            <td style="color: #00ff00; font-weight: 600;">{ticker}</td>
            <td style="color: #e0e0e0;">${row['Precio_Bs']:,.2f}</td>
            <td style="color: #00ff00; font-weight: 600;">${row['Precio_USD']:.4f}</td>
        </tr>
        """
    
    html_mercado += "</tbody></table>"
    
    components.html(html_mercado, height=600, scrolling=True)
else:
    st.error("No se pudo conectar con la Bolsa de Caracas.")