"""
Scraper Rappi - Flujo completo con sesion de Chrome logueada:
1. Abre Chrome con tu sesion (logueado en Rappi)
2. Configura direccion de entrega
3. Busca producto en barra de busqueda
4. Click en producto -> Agregar -> Checkout
5. Extrae precio, delivery fee, service fee, tiempo, total
6. Vuelve atras y repite con siguiente direccion
"""

import asyncio
import re
import random
import logging
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(open(1, 'w', encoding='utf-8', closefd=False)),
        logging.FileHandler(BASE_DIR / "scraper.log", encoding="utf-8")
    ]
)
log = logging.getLogger("scraper")

DEFAULT_ADDRESSES = [
    {"name": "Polanco", "zone": "premium", "address": "Av Presidente Masaryk 460, Polanco"},
    {"name": "Lomas", "zone": "premium", "address": "Av de las Palmas 800, Lomas de Chapultepec"},
    {"name": "Santa Fe", "zone": "premium", "address": "Av Vasco de Quiroga 3800, Santa Fe"},
    {"name": "Condesa", "zone": "media_alta", "address": "Av Tamaulipas 150, Condesa"},
    {"name": "Roma Norte", "zone": "media_alta", "address": "Av Alvaro Obregon 200, Roma Norte"},
    {"name": "Del Valle", "zone": "media_alta", "address": "Av Insurgentes Sur 1602, Del Valle"},
    {"name": "Coyoacan", "zone": "media_alta", "address": "Jardin Centenario 10, Coyoacan"},
    {"name": "Centro Historico", "zone": "media", "address": "Av 5 de Mayo 39, Centro Historico"},
    {"name": "Reforma", "zone": "media", "address": "Paseo de la Reforma 222, Juarez"},
    {"name": "Narvarte", "zone": "media", "address": "Av Universidad 815, Narvarte"},
    {"name": "Lindavista", "zone": "media", "address": "Av Montevideo 370, Lindavista"},
    {"name": "Coapa", "zone": "media", "address": "Calz del Hueso 400, Coapa"},
    {"name": "Mixcoac", "zone": "media", "address": "Av Revolucion 900, Mixcoac"},
    {"name": "Iztapalapa", "zone": "popular", "address": "Av Ermita Iztapalapa 3018, Iztapalapa"},
    {"name": "Iztacalco", "zone": "popular", "address": "Av Rio Churubusco 481, Iztacalco"},
    {"name": "GAM Norte", "zone": "popular", "address": "Av Insurgentes Norte 1800, GAM"},
    {"name": "Ecatepec", "zone": "periferia", "address": "Av Central 250, Ecatepec"},
    {"name": "Nezahualcoyotl", "zone": "periferia", "address": "Av Chimalhuacan 202, Nezahualcoyotl"},
    {"name": "Tlalnepantla", "zone": "periferia", "address": "Blvd M Avila Camacho 2900, Tlalnepantla"},
    {"name": "Chalco", "zone": "periferia", "address": "Av Solidaridad 140, Chalco"},
]


async def delay(min_s=1.0, max_s=3.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


def parse_price(text):
    if not text:
        return None
    text = text.replace(",", "").replace("MXN", "").replace("MX$", "").replace("$", "").strip()
    matches = re.findall(r'(\d+\.?\d*)', text)
    for m in matches:
        val = float(m)
        if 1.0 < val < 50000:
            return round(val, 2)
    return None


async def screenshot(page, name):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOTS_DIR / f"{name}_{ts}.png"
    await page.screenshot(path=str(path), full_page=False)
    log.info(f"  Screenshot: {path.name}")


async def accept_cookies(page):
    try:
        btn = await page.query_selector('text="Ok, entendido"')
        if btn:
            await btn.click()
            log.info("  Cookies aceptadas")
            await delay(0.5, 1)
    except Exception:
        pass


async def set_address(page, address_text, is_first=False):
    log.info(f"  Configurando direccion: {address_text}")

    try:
        if is_first:
            addr_input = await page.query_selector('input[placeholder*="quieres recibir"]')
            if not addr_input:
                addr_input = await page.query_selector('input[placeholder*="direcci"]')
            if not addr_input:
                addr_input = await page.query_selector('input[placeholder*="Escribe"]')
            if addr_input:
                await addr_input.click()
                await delay(0.5, 1)
        else:
            try:
                header_addr = await page.query_selector('header [class*="address"], header [class*="location"]')
                if not header_addr:
                    header_spans = await page.query_selector_all('header span, header button, header a')
                    for el in header_spans:
                        text = await el.inner_text()
                        if any(kw in text for kw in ["Avenida", "Av ", "Polanco", "Lomas", "Condesa", "Roma", "Valle", "Centro", "Masaryk", "Palmas", "Insurgentes", "Reforma", "Ciudad"]):
                            header_addr = el
                            break
                if header_addr:
                    await header_addr.click()
                    await delay(1, 2)
            except Exception:
                pass

        input_el = await page.query_selector('input[placeholder*="direcci"]')
        if not input_el:
            input_el = await page.query_selector('input[placeholder*="Escribe"]')
        if not input_el:
            input_el = await page.query_selector('input[placeholder*="quieres"]')
        if not input_el:
            all_inputs = await page.query_selector_all('input[type="text"]')
            for inp in all_inputs:
                ph = await inp.get_attribute("placeholder") or ""
                if any(kw in ph.lower() for kw in ["direcci", "escribe", "donde", "ubicaci"]):
                    input_el = inp
                    break

        if not input_el:
            log.warning("  No se encontro campo de direccion")
            return False

        await input_el.click()
        await input_el.fill("")
        await delay(0.3, 0.5)
        await input_el.type(address_text, delay=50)
        await delay(2, 3)

        suggestion = None
        suggestion_selectors = [
            '[class*="suggestion"]', '[class*="autocomplete"] li',
            '[class*="dropdown"] li', '[class*="result"] li',
            '[class*="option"]', '[role="option"]'
        ]
        for sel in suggestion_selectors:
            suggestion = await page.query_selector(sel)
            if suggestion:
                break

        if not suggestion:
            all_items = await page.query_selector_all('li, [role="option"], [class*="item"]')
            first_word = address_text.split(",")[0].split(" ")[-1] if "," in address_text else address_text.split(" ")[-1]
            for item in all_items[:10]:
                text = await item.inner_text()
                if first_word.lower() in text.lower():
                    suggestion = item
                    break
            if not suggestion and all_items:
                suggestion = all_items[0]

        if suggestion:
            await suggestion.click()
            log.info("  Sugerencia seleccionada")
            await delay(2, 3)
        else:
            log.warning("  No se encontro sugerencia")
            return False

        confirm_btn = await page.query_selector('button:has-text("Confirmar")')
        if not confirm_btn:
            confirm_btn = await page.query_selector('text="Confirmar direcci"')
        if confirm_btn:
            await confirm_btn.click()
            log.info("  Direccion confirmada")
            await delay(1, 2)

        save_btn = await page.query_selector('button:has-text("Guardar")')
        if not save_btn:
            save_btn = await page.query_selector('text="Guardar direcci"')
        if save_btn:
            await save_btn.click()
            log.info("  Direccion guardada")
            await delay(2, 3)

        await screenshot(page, f"address_{address_text[:20].replace(' ', '_')}")
        return True

    except Exception as e:
        log.error(f"  Error configurando direccion: {e}")
        return False


async def search_product(page, product_name):
    log.info(f"  Buscando: {product_name}")

    try:
        search_bar = await page.query_selector('input[placeholder*="Comida"]')
        if not search_bar:
            search_bar = await page.query_selector('input[placeholder*="restaurantes"]')
        if not search_bar:
            search_bar = await page.query_selector('input[placeholder*="productos"]')
        if not search_bar:
            search_bar = await page.query_selector('header input')
        if not search_bar:
            all_inputs = await page.query_selector_all('input')
            for inp in all_inputs:
                ph = await inp.get_attribute("placeholder") or ""
                if any(kw in ph.lower() for kw in ["busca", "comida", "producto", "restaurante", "tienda"]):
                    search_bar = inp
                    break

        if not search_bar:
            search_icon = await page.query_selector('header svg, header [class*="search"]')
            if search_icon:
                await search_icon.click()
                await delay(1, 2)
                search_bar = await page.query_selector('input')

        if not search_bar:
            log.warning("  No se encontro barra de busqueda")
            return False

        await search_bar.click()
        await delay(0.5, 1)
        await search_bar.fill("")
        await search_bar.type(product_name, delay=60)
        await delay(1, 2)
        await page.keyboard.press("Enter")
        await delay(3, 5)

        await screenshot(page, f"search_{product_name[:20].replace(' ', '_')}")
        return True

    except Exception as e:
        log.error(f"  Error buscando: {e}")
        return False


async def extract_product_data(page, product_name):
    record = {
        "product_found": "",
        "product_price": None,
        "delivery_fee": None,
        "service_fee": None,
        "estimated_time": None,
        "discount": None,
        "available": False,
        "total_price": None,
        "restaurant": ""
    }

    try:
        for _ in range(8):
            await page.evaluate("window.scrollBy(0, 500)")
            await delay(0.3, 0.5)

        await page.evaluate("window.scrollTo(0, 0)")
        await delay(0.5, 1)

        body_text = await page.inner_text("body")

        time_match = re.search(r'(\d+)\s*min', body_text)
        if time_match:
            record["estimated_time"] = f"{time_match.group(1)} min"

        if "envio gratis" in body_text.lower() or "Envio Gratis" in body_text:
            record["delivery_fee"] = 0.0
            record["discount"] = "Envio Gratis"

        all_products = await page.evaluate("""(searchTerm) => {
            const results = [];
            const seen = new Set();
            const elements = document.querySelectorAll('div, li, article, section, a');

            for (const el of elements) {
                const text = el.innerText || '';
                if (!text.includes('$')) continue;
                if (text.length > 500) continue;

                const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                let name = '';
                let price = null;

                for (const line of lines) {
                    const priceMatch = line.match(/^\\$\\s*([\\d,.]+)/);
                    if (priceMatch && !price) {
                        price = parseFloat(priceMatch[1].replace(',', ''));
                    } else if (!name && line.length > 3 && line.length < 80
                        && !line.startsWith('$') && !line.match(/^-?\\d+%/)
                        && !line.match(/^\\d+\\.?\\d*$/)
                        && !line.includes('Envio') && !line.includes('Agregar')
                        && !line.includes('min') && !line.includes('Gratis')
                        && !line.includes('Buscar') && !line.includes('Ingresa')
                        && !line.includes('Top resultado')) {
                        name = line;
                    }
                }

                if (name && price && price > 5 && price < 5000 && !seen.has(name)) {
                    seen.add(name);
                    const nameLC = name.toLowerCase();
                    const searchLC = searchTerm.toLowerCase();
                    const words = searchLC.split(' ');
                    const isExact = nameLC.includes(searchLC);
                    const isPartial = words.every(w => nameLC.includes(w));
                    const isAny = words.some(w => nameLC.includes(w));
                    results.push({name, price, isExact, isPartial, isAny});
                }
            }

            results.sort((a, b) => {
                if (a.isExact !== b.isExact) return b.isExact ? 1 : -1;
                if (a.isPartial !== b.isPartial) return b.isPartial ? 1 : -1;
                if (a.isAny !== b.isAny) return b.isAny ? 1 : -1;
                return 0;
            });
            return results;
        }""", product_name)

        log.info(f"  Productos encontrados: {len(all_products)}")

        best = None
        if all_products:
            best = all_products[0]

        if best:
            record["product_found"] = best["name"]
            record["product_price"] = best["price"]
            record["available"] = True
            log.info(f"  ENCONTRADO: {best['name']} -> ${best['price']}")

            try:
                escaped_name = best["name"].replace("'", "\\'").replace('"', '\\"')
                await page.evaluate(f"""() => {{
                    const els = document.querySelectorAll('*');
                    for (const el of els) {{
                        const t = (el.innerText || '').trim();
                        if (t === '{escaped_name}' || t.startsWith('{escaped_name}')) {{
                            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            setTimeout(() => el.click(), 500);
                            break;
                        }}
                    }}
                }}""")
                await delay(3, 5)
                await screenshot(page, f"product_{product_name[:15].replace(' ', '_')}")

                modal_text = await page.inner_text("body")

                add_btn = await page.query_selector('button:has-text("Agregar e ir a pagar")')
                if not add_btn:
                    add_btn = await page.query_selector('button:has-text("Agregar")')
                if add_btn:
                    btn_text = await add_btn.inner_text()
                    btn_price = parse_price(btn_text)
                    if btn_price:
                        record["product_price"] = btn_price

                    await add_btn.click()
                    await delay(4, 6)

                    checkout_text = await page.inner_text("body")
                    await screenshot(page, f"checkout_{product_name[:15].replace(' ', '_')}")

                    envio = re.search(r'Costo de env.o\s*\$\s*([\d,.]+)', checkout_text)
                    if envio:
                        record["delivery_fee"] = parse_price(envio.group(1))

                    servicio = re.search(r'Tarifa de Servicio\s*\$\s*([\d,.]+)', checkout_text)
                    if servicio:
                        record["service_fee"] = parse_price(servicio.group(1))

                    total_m = re.search(r'Total\s*\$\s*([\d,.]+)', checkout_text)
                    if total_m:
                        record["total_price"] = parse_price(total_m.group(1))

                    tiempo = re.search(r'(\d+\s*-\s*\d+)\s*min', checkout_text)
                    if tiempo:
                        record["estimated_time"] = f"{tiempo.group(1)} min"

                    costo_prod = re.search(r'Costo de productos\s*\$\s*([\d,.]+)', checkout_text)
                    if costo_prod:
                        record["product_price"] = parse_price(costo_prod.group(1))

                    log.info(f"  CHECKOUT: fee={record['delivery_fee']}, servicio={record['service_fee']}, total={record['total_price']}")

                    back = await page.query_selector('text="Volver"')
                    if back:
                        await back.click()
                    else:
                        await page.go_back()
                    await delay(2, 3)
                    await page.go_back()
                    await delay(2, 3)

            except Exception as e:
                log.warning(f"  Error en click/checkout: {e}")

        if record["product_price"] and not record["total_price"]:
            fee = record["delivery_fee"] or 0
            sfee = record["service_fee"] or 0
            record["total_price"] = round(record["product_price"] + fee + sfee, 2)

    except Exception as e:
        log.error(f"  Error extrayendo datos: {e}")

    return record


async def run_rappi_scrape(product_configs, max_addresses=None, headless=True, sheets_client=None):
    addresses = DEFAULT_ADDRESSES
    if max_addresses:
        addresses = addresses[:max_addresses]

    if sheets_client:
        sheets_client.clear_results()

    all_records = []

    async with async_playwright() as pw:
        user_data = str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data")
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=user_data,
            channel="chrome",
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            locale="es-MX",
            args=["--disable-blink-features=AutomationControlled", "--profile-directory=Default"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        log.info("Navegando a rappi.com.mx...")
        await page.goto("https://www.rappi.com.mx", wait_until="domcontentloaded", timeout=30000)
        await delay(3, 5)

        await accept_cookies(page)

        for config in product_configs:
            product = config["product"]
            platforms = config.get("platforms", ["rappi"])

            if "rappi" not in platforms:
                continue

            print(f"\n{'='*50}")
            print(f"  RAPPI -> {product}")
            print(f"  Direcciones: {len(addresses)}")
            print(f"{'='*50}")

            platform_records = []

            for i, addr in enumerate(addresses):
                log.info(f"\n[{i+1}/{len(addresses)}] {addr['name']}")

                await page.goto("https://www.rappi.com.mx", wait_until="domcontentloaded", timeout=30000)
                await delay(2, 3)

                addr_ok = await set_address(page, addr["address"], is_first=(i == 0))
                if not addr_ok:
                    log.warning(f"  Direccion fallo, usando URL directa")
                    await page.goto(f"https://www.rappi.com.mx/search?query={product.replace(' ', '%20')}", wait_until="domcontentloaded", timeout=30000)
                    await delay(3, 5)
                else:
                    search_ok = await search_product(page, product)
                    if not search_ok:
                        await page.goto(f"https://www.rappi.com.mx/search?query={product.replace(' ', '%20')}", wait_until="domcontentloaded", timeout=30000)
                        await delay(3, 5)

                data = await extract_product_data(page, product)
                data["product_searched"] = product
                data["address"] = addr["name"]
                data["zone"] = addr["zone"]

                platform_records.append(data)
                await delay(2, 4)

            all_records.extend(platform_records)

            if sheets_client:
                sheets_client.write_results("rappi", platform_records)

            found = sum(1 for r in platform_records if r.get("available"))
            print(f"\n  Resultado: {found}/{len(platform_records)} encontrados")

        await context.close()

    if sheets_client:
        sheets_client.build_comparative()

    return all_records
