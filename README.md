# Rappi Competitive Intelligence System

Caso técnico para AI Engineer @ Rappi.

Sistema que scrapea datos reales de Rappi, Uber Eats y DiDi Food en CDMX, los exporta a Google Sheets organizados por competidor, y los visualiza automáticamente en Looker Studio.

## Arquitectura

```
Google Sheet (Botón "Scrapear" o comando Python)
        │
        ▼
Python + Playwright (scrapea las 3 plataformas)
        │
        ▼
Google Sheets API (escribe datos por competidor)
        │
        ▼
Looker Studio (dashboard auto-actualizable)
```

## Qué scrapea

**Plataformas:** Rappi, Uber Eats, DiDi Food

**Métricas (7):** Precio producto, Delivery Fee, Service Fee, Tiempo estimado, Descuentos activos, Disponibilidad, Precio final total

**Verticales:** Fast food (McDonald's, Burger King, KFC) + Retail (OXXO, 7-Eleven) + Pharmacy (bonus)

**Cobertura:** 30 direcciones en CDMX en 5 zonas: Premium (Polanco, Lomas, Santa Fe), Media-Alta (Condesa, Roma, Del Valle), Media (Centro, Reforma, Narvarte), Popular (Iztapalapa, GAM), Periferia (Ecatepec, Neza, Chalco)

## Setup

```bash
git clone https://github.com/jhongiraldo283-maker/rappi-competitive-intelligence.git
cd rappi-competitive-intelligence

py -3.12 -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

Coloca tu archivo de credenciales de Google Cloud en `config/credentials.json` y comparte el Google Sheet con el email de la service account como Editor.

## Cómo correrlo

```bash
# Scraping completo → Google Sheets
python main.py

# Demo rápida (5 direcciones, browser visible)
python main.py --max-addresses 5 --visible

# Solo Rappi
python main.py --platforms rappi --max-addresses 3

# Sin Google Sheets (solo local)
python main.py --no-sheets
```

## Estructura del Google Sheet

- **Rappi** → Datos scrapeados de Rappi
- **UberEats** → Datos scrapeados de Uber Eats
- **DiDiFood** → Datos scrapeados de DiDi Food
- **Comparativo** → Comparación cross-platform (quién es más barato, más rápido)
- **Config** → Direcciones y productos configurables

## Estructura del repo

```
main.py             -> Orquestador principal
scraper.py          -> Scrapers Playwright (Rappi, UberEats, DiDi) con API interception
sheets_client.py    -> Integración con Google Sheets (lectura/escritura)
config/
  addresses.json    -> 30 direcciones en CDMX con justificación
  products.json     -> Productos de referencia por vertical
  credentials.json  -> Credenciales Google Cloud (no incluido en repo)
data/               -> Datos locales (CSV + JSON)
screenshots/        -> Capturas automáticas del scraping
```

## Enfoque técnico

- **Playwright** con interceptación de API responses internas (más robusto que parsear HTML)
- Fallback a extracción del DOM si la API no devuelve el dato
- Anti-detection: user-agent real, delays aleatorios, geolocation spoofing
- Rate limiting: 2-5 seg entre requests
- Screenshots automáticos como evidencia
- Escritura batch a Google Sheets (más rápido que fila por fila)
- Hoja comparativa auto-generada

## Looker Studio

El dashboard se conecta directamente al Google Sheet. Se actualiza automático cada vez que el scraper corre. Para configurarlo:
1. Abre Looker Studio (lookerstudio.google.com)
2. Nuevo reporte → Agregar datos → Google Sheets
3. Selecciona el sheet "Rappi Competitive Intelligence"
4. Crea gráficos conectados a cada hoja

## Consideraciones éticas

- Rate limiting de 2-5 seg entre requests
- Solo datos públicos visibles en las plataformas
- User-Agent de browser real
- Uso exclusivo para evaluación técnica

---

Jhon Fernando Giraldo Lamprea — 2025
