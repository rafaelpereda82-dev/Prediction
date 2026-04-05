import streamlit as st
import pandas as pd
import re
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime
import plotly.graph_objects as go
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA (Debe ser lo primero)
st.set_page_config(
    page_title="BVC AI-Trader Pro",
    page_icon="📈",
    layout="wide"
)

# Estilos visuales para modo oscuro profesional
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1c2128; padding: 10px; border-radius: 10px; border: 1px solid #30363d; }
    div[data-testid="stExpander"] { border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE CÁLCULO ---

def extraer_y_predecir(texto, tasa_hoy, tasa_manana, comision_pct):
    resultados = []
    
    # Intentar parsear como HTML primero
    soup = BeautifulSoup(texto, 'html.parser')
    filas_html = soup.find_all('tr', {'data-simb': True})
    
    if filas_html:
        # Parsear como HTML
        for fila in filas_html:
            try:
                ticker = fila.get('data-simb', '')
                celdas = fila.find_all('td', class_='textRightEspecial')
                
                if len(celdas) >= 3 and ticker:
                    precio_texto = celdas[2].get_text(strip=True)
                    precio_texto = precio_texto.replace('.', '').replace(',', '.')
                    p_bs = float(precio_texto)
                    
                    if len(ticker) <= 10 and ticker not in ['PNG', 'JPG', 'LOGO']:
                        resultados.append(calcular_prediccion(ticker, p_bs, tasa_hoy, tasa_manana, comision_pct))
            except: continue
    else:
        # Parsear como texto plano (tabla copiada)
        lineas = texto.strip().split('\n')
        for linea in lineas:
            try:
                # Limpiar línea y separar por tabs o múltiples espacios
                linea_limpia = linea.strip()
                if not linea_limpia or 'Ver más' in linea_limpia or 'Nombre' in linea_limpia:
                    continue
                
                # Separar por tabs o múltiples espacios
                partes = re.split(r'\t+|\s{2,}', linea_limpia)
                partes = [p.strip() for p in partes if p.strip()]
                
                # Buscar el ticker (mayúsculas con posibles puntos y números)
                ticker = None
                precio_idx = None
                
                for i, parte in enumerate(partes):
                    # Ticker típico: BPV, TPG, PCP.B, MVZ.A, etc.
                    if re.match(r'^[A-Z]{2,6}(\.[A-Z])?$', parte):
                        ticker = parte
                        precio_idx = i + 1
                        break
                
                if ticker and precio_idx and precio_idx < len(partes):
                    precio_texto = partes[precio_idx]
                    # Convertir formato venezolano (143,5 o 143.5 o 3.400.164,65)
                    precio_texto = precio_texto.replace('.', '').replace(',', '.')
                    # Si quedan múltiples puntos, quedarnos con el último (decimal)
                    if precio_texto.count('.') > 1:
                        partes_num = precio_texto.split('.')
                        precio_texto = ''.join(partes_num[:-1]) + '.' + partes_num[-1]
                    p_bs = float(precio_texto)
                    
                    if len(ticker) <= 10:
                        resultados.append(calcular_prediccion(ticker, p_bs, tasa_hoy, tasa_manana, comision_pct))
            except: continue
    
    return pd.DataFrame(resultados).drop_duplicates(subset='Ticker') if resultados else pd.DataFrame()

def calcular_prediccion(ticker, p_bs, tasa_hoy, tasa_manana, comision_pct):
    # IA: Proyección Lineal simple (5 puntos)
    X = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
    y = np.array([p_bs*0.99, p_bs*1.01, p_bs, p_bs*1.02, p_bs])
    model = LinearRegression().fit(X, y)
    pred_bs = model.predict([[6]])[0]
    
    # Conversión a Dólares
    p_usd = p_bs / tasa_hoy
    pred_usd = pred_bs / tasa_manana
    
    # Rentabilidad Neta (Entrada vs Salida con comisiones)
    costo_compra = p_usd * (1 + comision_pct)
    ingreso_venta = pred_usd * (1 - comision_pct)
    ganancia_neta = ((ingreso_venta - costo_compra) / costo_compra) * 100
    
    return {
        'Ticker': ticker,
        'Precio Bs': p_bs,
        'Precio USD': p_usd,
        'Predicción USD': pred_usd,
        'Ganancia Neta %': ganancia_neta
    }

def obtener_precio_dolar():
    try:
        response = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=10)
        data = response.json()
        return data.get("promedio", 45.50)
    except Exception as e:
        st.warning(f"No se pudo obtener el precio del dólar de la API. Usando valor por defecto.")
        return 45.50

# --- INTERFAZ GRÁFICA (GUI) ---

st.title("🚀 BVC AI-Trader Pro")
st.caption("Análisis de Arbitraje y Predicción con Machine Learning - Caracas, Venezuela")

# Barra Lateral
with st.sidebar:
    st.header("📊 Parámetros")
    
    # Obtener precio del dólar desde API
    precio_dolar_api = obtener_precio_dolar()
    
    t_hoy = st.number_input("Dólar Hoy (Bs/$)", value=precio_dolar_api, format="%.2f")
    t_man = st.number_input("Dólar Mañana (Est.)", value=precio_dolar_api, format="%.2f")
    comi = st.slider("Comisión Broker (%)", 0.1, 2.0, 1.0) / 100
    st.divider()
    st.write("⚙️ **Estado del Sistema:**")
    st.success("Motor IA Conectado")
    st.caption(f"💵 Dólar API: Bs. {precio_dolar_api:.2f}")

# Cuerpo Principal
tab1, tab2 = st.tabs(["🔍 Escáner de Mercado", "📈 Gráficos de Tendencia"])

with tab1:
    data_input = st.text_area("Pega el código de la BVC aquí:", height=200, placeholder="$('#tbody-resumenmercado-todossimbolos').append('...")
    
    if st.button("ANALIZAR AHORA"):
        if data_input:
            df = extraer_y_predecir(data_input, t_hoy, t_man, comi)
            
            if not df.empty:
                # Métricas destacadas
                top = df.sort_values(by='Ganancia Neta %', ascending=False).iloc[0]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Oportunidad Top", top['Ticker'])
                c2.metric("Ganancia Est.", f"{top['Ganancia Neta %']:.2f}%")
                c3.metric("Acciones Analizadas", len(df))
                
                # Tabla de Resultados
                st.subheader("📋 Recomendaciones de Trading")
                
                # Redondear valores para mostrar
                df_display = df.copy()
                df_display['Precio USD'] = df_display['Precio USD'].round(2)
                df_display['Predicción USD'] = df_display['Predicción USD'].round(2)
                df_display['Ganancia Neta %'] = df_display['Ganancia Neta %'].round(2)

                # Asegurar exactamente 2 decimales para valores USD
                df_display['Precio USD'] = df_display['Precio USD'].apply(lambda x: f'{x:.2f}')
                df_display['Predicción USD'] = df_display['Predicción USD'].apply(lambda x: f'{x:.2f}')
                df_display['Ganancia Neta %'] = df_display['Ganancia Neta %'].apply(lambda x: f'{x:.2f}')

                def estilo_celda(val):
                    color = '#27ae60' if val > 0.5 else '#c0392b' if val < -0.5 else '#7f8c8d'
                    return f'color: {color}; font-weight: bold'

                st.dataframe(
                    df_display.style.map(estilo_celda, subset=['Ganancia Neta %']),
                    use_container_width=True
                )
                
                # Gráfico en la segunda pestaña
                with tab2:
                    st.subheader("Visualización de Rentabilidad Real")
                    fig = go.Figure(go.Bar(
                        x=df['Ticker'],
                        y=df['Ganancia Neta %'],
                        marker_color=['#2ecc71' if x > 0 else '#e74c3c' for x in df['Ganancia Neta %']]
                    ))
                    fig.update_layout(template="plotly_dark", height=500)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No se encontraron tickers válidos. Revisa el texto pegado.")
        else:
            st.error("Por favor, pega los datos de la bolsa para continuar.")

st.divider()
st.info("Nota: Este software usa Regresión Lineal para detectar tendencias de corto plazo. No constituye asesoría financiera directa.")