"""Opt-in browser audit against a local checkout; no source acquisition.

Use --output outside the repository. Bytes are decoded response bodies, not an
estimate of GitHub Pages compressed transfers. Timing is local and non-benchmark.
"""
import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def run(url, channel, output):
    output.mkdir(parents=True, exist_ok=True)
    results = {"channel": channel, "modules": [], "responsive": [], "errors": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        page.on("pageerror", lambda error: results["errors"].append(str(error)))
        start = time.monotonic()
        page.goto(url, wait_until="domcontentloaded")
        page.locator("#loadingOverlay").wait_for(state="hidden", timeout=120000)
        for module in ("quantityView", "priceView", "commodityView", "carnesView"):
            if module != "quantityView":
                start = time.monotonic()
                page.locator(f'[data-module="{module}"]').click()
                if module == "carnesView":
                    page.wait_for_function("document.getElementById('carnesRoot').getAttribute('aria-busy') === 'false'")
                else:
                    page.locator(f'#{module}[aria-busy="false"]').wait_for(timeout=120000)
            resources = page.evaluate("""performance.getEntriesByType('resource').map(r =>
                ({url:r.name, bytes:r.decodedBodySize, transfer:r.transferSize}))""")
            local = [r for r in resources if r["url"].startswith(url.rstrip("/"))]
            results["modules"].append({"module": module, "elapsed_seconds": round(time.monotonic()-start, 3),
                "cumulative_requests": len(resources), "cumulative_local_bytes": sum(r["bytes"] for r in local),
                "largest_payload": max(local, key=lambda r:r["bytes"], default=None), "resources": local})
            if module == "quantityView":
                assert not any("PRECIOS_MAYORISTAS" in r["url"] or "/data/carnes/" in r["url"] or "/data/commodities_sio/" in r["url"] for r in local)
            for width in (1440, 1000, 900, 640):
                page.set_viewport_size({"width": width, "height": 1050})
                page.locator(f'#{module}').scroll_into_view_if_needed()
                page.screenshot(path=str(output/f'{channel}-{module}-{width}.png'))
                overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                results["responsive"].append({"module":module, "width":width, "page_overflow":overflow})
                if module == "commodityView":
                    trigger=page.locator('#commodityFilterCommodityTrigger')
                    trigger.click()
                    menu=page.locator('#commodityFilterCommodityMenu')
                    menu.wait_for(state='visible')
                    assert menu.evaluate("""el=>{const r=el.getBoundingClientRect();const hit=document.elementFromPoint(r.left+20,Math.min(r.bottom-10,innerHeight-10));return !!hit && el.contains(hit);} """)
                    page.screenshot(path=str(output/f'{channel}-dropdown-{width}.png'))
                    trigger.click()
                    menu.wait_for(state='hidden')
            page.set_viewport_size({"width":1440,"height":1050})
            if module == "carnesView":
                page.locator('[data-module="commodityView"]').click()
                results['commodity_sources']=[]
                for source,frequency in [('magyp_internal','mensual'),('magyp_board','diaria'),('magyp_fas','diaria'),('magyp_fob','diaria'),('magyp_futures','diaria'),('sio',None)]:
                    page.locator('#commodityFilterSource').select_option(source)
                    page.wait_for_function('(source)=>commoditySource===source',arg=source)
                    actual_frequency=page.locator('#commodityFilterFrequency').input_value()
                    assert actual_frequency==frequency if frequency else actual_frequency in ('mensual','diaria'), (source,actual_frequency,frequency)
                    if source=='magyp_futures':
                        assert page.locator('#commodityConditionLabel').text_content().strip()=='Vencimiento / Posición'
                    results['commodity_sources'].append({'source':source,'frequency':actual_frequency,
                        'subtitle':page.locator('#commoditySourceSubtitle').inner_text(),
                        'status':page.locator('#commodityView .source-update-status').inner_text()})
                page.locator('#commodityFilterSource').select_option('magyp_internal')
                page.wait_for_function("commoditySource==='magyp_internal'")
                page.locator('[data-module="carnesView"]').click()
        # Actual keyboard navigation, not only tab-index inspection.
        page.keyboard.press("Tab")
        results["keyboard_focus"] = page.evaluate("({tag:document.activeElement.tagName,outline:getComputedStyle(document.activeElement).outlineStyle})")
        results["forbidden_requests"] = [r["url"] for r in local if any(s in r["url"].lower() for s in ("/raw/", "/normalized/", "/analytical/"))]
        assert not results["errors"], results["errors"]
        assert not results["forbidden_requests"], results["forbidden_requests"]
        assert not any(r["page_overflow"] for r in results["responsive"]), results["responsive"]
        browser.close()
    (output/f'{channel}-results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"channel":channel,"modules":[{k:v for k,v in r.items() if k!="resources"} for r in results["modules"]],
                      "responsive_checks":len(results["responsive"]),"errors":results["errors"]},ensure_ascii=False))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8768")
    parser.add_argument("--channel", choices=("msedge","chrome"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args()
    run(args.url,args.channel,args.output)
