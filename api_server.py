from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

PORTFOLIO_FILE = "portafolio.json"

def cargar_portafolio():
    """Cargar portafolio desde archivo JSON"""
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_portafolio(portafolio):
    """Guardar portafolio en archivo JSON"""
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portafolio, f, indent=2)

def obtener_precios_bvc():
    """Obtener precios actuales de la BVC"""
    try:
        res = requests.get("https://www.bolsadecaracas.com/wp-content/themes/bvc/resumen_mercado.php", timeout=10)
        import re
        matches = re.findall(r'id="([A-Z0-9\.]+)".+?no-border-top">([\d\.]+)<', res.text)
        return {ticker: float(precio) for ticker, precio in matches}
    except:
        return {}

def obtener_tasa_bcv():
    """Obtener tasa del dólar BCV"""
    try:
        res = requests.get("https://pydolarve.org/api/v1/views?page=bcv", timeout=5)
        m = res.json().get('monitors', [])[0]
        return float(str(m.get('price')).replace(',', '.'))
    except:
        return 473.87

# Nombres de empresas
nombres_empresas = {
    'ABC.A': "BCO. CARIBE 'A'",
    'ALZ.B': "ALZA INVERSIONES",
    'ARC.A': "ARCA INM. Y VAL. 'A'",
    'ARC.B': "ARCA INM.VAL.'B'",
    'BNC': "BCO.NAC.CREDITO",
    'BPV': "BCO. PROVINCIAL",
    'BVCC': "BOLSA Y CC. CCS",
    'BVL': "B. DE VENEZUELA",
    'CCP.B': "CERAMICA CARABOBO",
    'DOM.A': "DOMINGUI",
    'ENV.A': "ENVASES VENEZOLANOS",
    'FNC': "FONDO NACIONAL",
    'FON.A': "FONDOVAL 'A'",
    'FON.B': "FONDOVAL 'B'",
    'FON.C': "FONDOVAL 'C'",
    'FTH.A': "FONDO DE INVERS. TH",
    'GPV': "GRUPO VENEZOLANO",
    'MAN.A': "MANPA",
    'MVZ.A': "MERCANTIL VEN. 'A'",
    'MVZ.B': "MERCANTIL VEN. 'B'",
    'PCP.B': "PROAGRO 'B'",
    'PGV.A': "PROAGRO VAL 'A'",
    'PGV.B': "PROAGRO VAL 'B'",
    'PHC.A': "PHILLIPS CARIBE",
    'SCB.A': "SUDAMERICANO 'A'",
    'SCB.B': "SUDAMERICANO 'B'",
    'SIV.A': "SIDOR 'A'",
    'SIV.B': "SIDOR 'B'",
    'SNI.B': "SINAI 'B'",
    'STG.A': "SANTA TERESA",
    'TPG': "TECNICAS POLLI",
    'VUL.A': "VULCANIZADOS",
}

@app.route('/')
def index():
    """Serve the HTML frontend"""
    return render_template('portfolio.html')

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """API endpoint to get portfolio data with calculations"""
    portafolio = cargar_portafolio()
    precios_bs = obtener_precios_bvc()
    tasa = obtener_tasa_bcv()
    
    # Convertir precios a USD
    precios_usd = {ticker: precio / tasa for ticker, precio in precios_bs.items()}
    
    # Separar compras y ventas
    compras = [p for p in portafolio if p.get('Tipo', 'COMPRA') == 'COMPRA']
    ventas = [p for p in portafolio if p.get('Tipo') == 'VENTA']
    
    # Calcular posiciones
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
    
    # Calcular resultados
    resultados = []
    total_invertido = 0
    total_actual = 0
    
    for ticker, pos in posiciones.items():
        if pos['cantidad'] > 0:
            precio_actual = precios_usd.get(ticker, 0)
            costo_promedio = pos['costo_total'] / pos['cantidad']
            valor_actual = precio_actual * pos['cantidad']
            valor_invertido = pos['costo_total']
            pnl = valor_actual - valor_invertido
            pnl_pct = ((precio_actual - costo_promedio) / costo_promedio) * 100 if costo_promedio > 0 else 0
            
            resultados.append({
                'ticker': ticker,
                'nombre': nombres_empresas.get(ticker, ticker),
                'cantidad': pos['cantidad'],
                'costo_promedio': round(costo_promedio, 2),
                'precio_actual': round(precio_actual, 2),
                'inversion_usd': round(valor_invertido, 2),
                'valor_actual_usd': round(valor_actual, 2),
                'pnl_usd': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2)
            })
            
            total_invertido += valor_invertido
            total_actual += valor_actual
    
    return jsonify({
        'posiciones': resultados,
        'resumen': {
            'total_invertido': round(total_invertido, 2),
            'total_actual': round(total_actual, 2),
            'pnl_total': round(total_actual - total_invertido, 2),
            'pnl_total_pct': round(((total_actual - total_invertido) / total_invertido) * 100, 2) if total_invertido > 0 else 0,
            'num_posiciones': len(resultados),
            'tasa_bcv': tasa
        }
    })

@app.route('/api/portfolio', methods=['POST'])
def add_position():
    """API endpoint to add a new position"""
    data = request.json
    portafolio = cargar_portafolio()
    
    nueva_compra = {
        'Ticker': data.get('ticker'),
        'Precio_Compra_USD': data.get('precio'),
        'Cantidad': data.get('cantidad'),
        'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'Inversion_USD': data.get('precio') * data.get('cantidad'),
        'Tipo': 'COMPRA'
    }
    
    portafolio.append(nueva_compra)
    guardar_portafolio(portafolio)
    
    return jsonify({'success': True, 'message': 'Compra registrada'})

@app.route('/api/prices', methods=['GET'])
def get_prices():
    """API endpoint to get current prices"""
    precios_bs = obtener_precios_bvc()
    tasa = obtener_tasa_bcv()
    precios_usd = {ticker: round(precio / tasa, 4) for ticker, precio in precios_bs.items()}
    
    return jsonify({
        'tasa_bcv': tasa,
        'precios_usd': precios_usd,
        'precios_bs': precios_bs
    })

if __name__ == '__main__':
    # Create templates directory if not exists
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
