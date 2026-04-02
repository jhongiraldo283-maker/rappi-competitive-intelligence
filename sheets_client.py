"""
Google Sheets integration.
Lee configuración desde la hoja "Productos" y escribe resultados por plataforma.
"""

import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path(__file__).resolve().parent / "config"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

RESULT_HEADERS = [
    "Timestamp", "Producto Buscado", "Restaurante/Tienda", "Plataforma",
    "Dirección", "Zona", "Producto Encontrado", "Precio Producto (MXN)",
    "Delivery Fee (MXN)", "Service Fee (MXN)", "Tiempo Estimado",
    "Descuento Activo", "Disponible", "Precio Final Total (MXN)"
]

COMP_HEADERS = [
    "Producto", "Restaurante", "Dirección", "Zona",
    "Precio Rappi", "Precio UberEats", "Precio DiDiFood",
    "Fee Rappi", "Fee UberEats", "Fee DiDiFood",
    "Tiempo Rappi", "Tiempo UberEats", "Tiempo DiDiFood",
    "Más Barato", "Diferencia $"
]


class SheetsClient:

    def __init__(self, sheet_name="Rappi Competitive Intelligence"):
        creds_path = CONFIG_DIR / "credentials.json"
        creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self.sheet_name = sheet_name
        self.spreadsheet = None

    def connect(self):
        try:
            self.spreadsheet = self.gc.open(self.sheet_name)
            print(f"Conectado a: {self.sheet_name}")
            return True
        except gspread.SpreadsheetNotFound:
            print(f"ERROR: Sheet '{self.sheet_name}' no encontrado")
            return False

    def setup_sheets(self):
        existing = [ws.title for ws in self.spreadsheet.worksheets()]
        sheets_config = {
            "Productos": ["Producto", "Restaurante/Tienda", "Plataforma", "Lugar", "Direcciones a consultar"],
            "Rappi": RESULT_HEADERS,
            "UberEats": RESULT_HEADERS,
            "DiDiFood": RESULT_HEADERS,
            "Comparativo": COMP_HEADERS
        }
        for name, headers in sheets_config.items():
            if name not in existing:
                self.spreadsheet.add_worksheet(title=name, rows=2000, cols=20)
            ws = self.spreadsheet.worksheet(name)
            if not ws.row_values(1):
                ws.append_row(headers)
        print("Hojas configuradas")

    def read_products_config(self):
        ws = self.spreadsheet.worksheet("Productos")
        rows = ws.get_all_records()
        if not rows:
            print("Hoja 'Productos' vacía")
            return []

        configs = []
        for row in rows:
            product = str(row.get("Producto", "")).strip()
            restaurant = str(row.get("Restaurante/Tienda", "")).strip()
            platform = str(row.get("Plataforma", "")).strip()
            location = str(row.get("Lugar", "")).strip()
            addresses_raw = str(row.get("Direcciones a consultar", "")).strip()

            if not product or not restaurant:
                continue

            if platform.lower() in ["rappi", "ubereats", "didifood"]:
                platforms = [platform.lower()]
            elif "," in platform:
                platforms = [p.strip().lower() for p in platform.split(",")]
            else:
                platforms = ["rappi", "ubereats", "didifood"]

            custom_addresses = []
            if addresses_raw:
                custom_addresses = [a.strip() for a in addresses_raw.split(";") if a.strip()]

            configs.append({
                "product": product,
                "restaurant": restaurant,
                "platforms": platforms,
                "location": location or "Ciudad de México",
                "custom_addresses": custom_addresses
            })

        print(f"Productos configurados: {len(configs)}")
        for c in configs:
            print(f"  {c['product']} @ {c['restaurant']} → {', '.join(c['platforms'])}")
        return configs

    def write_results(self, platform, records):
        sheet_map = {"rappi": "Rappi", "ubereats": "UberEats", "didifood": "DiDiFood"}
        sheet_name = sheet_map.get(platform.lower())
        if not sheet_name or not records:
            return
        ws = self.spreadsheet.worksheet(sheet_name)
        rows = []
        for r in records:
            rows.append([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(r.get("product_searched", "")),
                str(r.get("restaurant", "")),
                platform,
                str(r.get("address", "")),
                str(r.get("zone", "")),
                str(r.get("product_found", "")),
                str(r.get("product_price", "") if r.get("product_price") else ""),
                str(r.get("delivery_fee", "") if r.get("delivery_fee") is not None else ""),
                str(r.get("service_fee", "") if r.get("service_fee") else ""),
                str(r.get("estimated_time", "")),
                str(r.get("discount", "")),
                "Sí" if r.get("available") else "No",
                str(r.get("total_price", "") if r.get("total_price") else "")
            ])
        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")
            print(f"  {len(rows)} registros → {sheet_name}")

    def clear_results(self):
        for name in ["Rappi", "UberEats", "DiDiFood", "Comparativo"]:
            try:
                ws = self.spreadsheet.worksheet(name)
                ws.clear()
                ws.append_row(COMP_HEADERS if name == "Comparativo" else RESULT_HEADERS)
            except Exception:
                pass
        print("Datos anteriores limpiados")

    def build_comparative(self):
        all_data = {}
        for platform, sheet_name in [("rappi", "Rappi"), ("ubereats", "UberEats"), ("didifood", "DiDiFood")]:
            try:
                ws = self.spreadsheet.worksheet(sheet_name)
                rows = ws.get_all_records()
                for row in rows:
                    key = f"{row.get('Producto Buscado','')}|{row.get('Restaurante/Tienda','')}|{row.get('Dirección','')}"
                    if key not in all_data:
                        all_data[key] = {
                            "product": row.get("Producto Buscado", ""),
                            "restaurant": row.get("Restaurante/Tienda", ""),
                            "address": row.get("Dirección", ""),
                            "zone": row.get("Zona", "")
                        }
                    all_data[key][f"price_{platform}"] = row.get("Precio Producto (MXN)", "")
                    all_data[key][f"fee_{platform}"] = row.get("Delivery Fee (MXN)", "")
                    all_data[key][f"time_{platform}"] = row.get("Tiempo Estimado", "")
            except Exception:
                pass

        ws_comp = self.spreadsheet.worksheet("Comparativo")
        ws_comp.clear()
        ws_comp.append_row(COMP_HEADERS)
        comp_rows = []
        for data in all_data.values():
            prices = {}
            for p in ["rappi", "ubereats", "didifood"]:
                try:
                    val = float(data.get(f"price_{p}", 0) or 0)
                    if val > 0:
                        prices[p] = val
                except (ValueError, TypeError):
                    pass
            cheapest = min(prices, key=prices.get).capitalize() if prices else ""
            diff = round(max(prices.values()) - min(prices.values()), 2) if len(prices) >= 2 else ""
            comp_rows.append([
                data["product"], data["restaurant"], data["address"], data["zone"],
                data.get("price_rappi", ""), data.get("price_ubereats", ""), data.get("price_didifood", ""),
                data.get("fee_rappi", ""), data.get("fee_ubereats", ""), data.get("fee_didifood", ""),
                data.get("time_rappi", ""), data.get("time_ubereats", ""), data.get("time_didifood", ""),
                cheapest, diff
            ])
        if comp_rows:
            ws_comp.append_rows(comp_rows, value_input_option="USER_ENTERED")
            print(f"Comparativo: {len(comp_rows)} filas")
