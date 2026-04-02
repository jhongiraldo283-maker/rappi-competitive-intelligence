"""
Rappi Competitive Intelligence System
Lee productos del Google Sheet → Scrapea → Escribe resultados al Sheet

Uso:
    python main.py                          # Lee Sheet y scrapea todo
    python main.py --max-addresses 5        # Solo 5 direcciones por producto
    python main.py --visible                # Browser visible (para demo)
"""

import argparse
import asyncio
import json
import csv
from pathlib import Path
from datetime import datetime

from scraper import run_rappi_scrape
from sheets_client import SheetsClient


def save_local(results_by_platform):
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_records = []
    for platform, records in results_by_platform.items():
        for r in records:
            r["platform"] = platform
            all_records.append(r)

    json_path = data_dir / f"scrape_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "total": len(all_records), "data": all_records}, f, ensure_ascii=False, indent=2, default=str)

    csv_path = data_dir / f"scrape_{ts}.csv"
    if all_records:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_records[0].keys())
            writer.writeheader()
            writer.writerows(all_records)

    print(f"\nDatos locales: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Rappi Competitive Intelligence")
    parser.add_argument("--max-addresses", type=int, default=None)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--sheet-name", default="Rappi Competitive Intelligence")
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════╗")
    print("║  RAPPI COMPETITIVE INTELLIGENCE SYSTEM       ║")
    print("╚══════════════════════════════════════════════╝\n")

    sheets = SheetsClient(sheet_name=args.sheet_name)
    if not sheets.connect():
        print("No se pudo conectar al Google Sheet")
        return

    sheets.setup_sheets()
    configs = sheets.read_products_config()

    if not configs:
        print("\nNo hay productos configurados en la hoja 'Productos'")
        print("Agrega filas con: Producto | Restaurante/Tienda | Plataforma | Lugar")
        return

    print(f"\nIniciando scraping...")
    print(f"  Productos: {len(configs)}")
    print(f"  Direcciones por producto: {args.max_addresses or 20}")
    print(f"  Browser: {'Visible' if args.visible else 'Headless'}\n")

    results = asyncio.run(run_rappi_scrape(
        product_configs=configs,
        max_addresses=args.max_addresses,
        headless=not args.visible,
        sheets_client=sheets
    ))

    save_local({"rappi": results})

    total = len(results)
    found = sum(1 for r in results if r.get("available"))

    print(f"\n{'='*50}")
    print(f"  COMPLETADO")
    print(f"  Total registros: {total}")
    print(f"  Productos encontrados: {found}")
    print(f"  Google Sheet actualizado: {args.sheet_name}")
    print(f"{'='*50}")
    print(f"\n✅ Listo. Revisa tu Google Sheet y conecta Looker Studio.")


if __name__ == "__main__":
    main()
