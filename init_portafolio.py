import json
import os

PORTFOLIO_FILE = "portafolio.json"

def inicializar_portafolio_demo():
    """Crear datos de ejemplo si el portafolio está vacío"""
    if not os.path.exists(PORTFOLIO_FILE) or os.path.getsize(PORTFOLIO_FILE) < 10:
        datos_demo = [
            {
                "Ticker": "ABC.A",
                "Precio_Compra_USD": 3.50,
                "Cantidad": 100,
                "Fecha": "2026-04-01 10:00",
                "Inversion_USD": 350.00,
                "Tipo": "COMPRA"
            },
            {
                "Ticker": "BPV",
                "Precio_Compra_USD": 0.30,
                "Cantidad": 500,
                "Fecha": "2026-04-02 14:30",
                "Inversion_USD": 150.00,
                "Tipo": "COMPRA"
            },
            {
                "Ticker": "BVCC",
                "Precio_Compra_USD": 1.20,
                "Cantidad": 200,
                "Fecha": "2026-04-03 09:15",
                "Inversion_USD": 240.00,
                "Tipo": "COMPRA"
            }
        ]
        
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(datos_demo, f, indent=2)
        
        print("✅ Portafolio de demostración creado con éxito!")
        print("📊 Se agregaron 3 posiciones de ejemplo:")
        print("   - ABC.A: 100 acciones a $3.50")
        print("   - BPV: 500 acciones a $0.30")
        print("   - BVCC: 200 acciones a $1.20")
        return True
    
    return False

if __name__ == "__main__":
    if inicializar_portafolio_demo():
        print("\n🚀 Ahora ejecuta: .\ABRIR_BOLSA.bat")
    else:
        print("ℹ️ El portafolio ya existe. No se sobrescribieron datos.")
