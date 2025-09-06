from playwright.sync_api import sync_playwright

def run(tests, preview_url):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(preview_url, wait_until="networkidle")

        for t in tests:
            method = t.get("method")
            sel = t.get("selector")
            ok = False
            if method == "dom":
                if "assert" in t:
                    html = page.inner_html(sel)
                    ok = all(s in html for s in t["assert"])
                elif "assert_count" in t:
                    counts = {k: page.locator(f'{sel} [data-test="{k}"]').count()
                              for k in t["assert_count"].keys()}
                    ok = all(counts[k] == v for k, v in t["assert_count"].items())
                elif "range" in t:
                    n = page.locator(sel).count()
                    lo, hi = t["range"]
                    ok = lo <= n <= hi
            elif method == "playwright":
                for act in t.get("actions", []):
                    if "swipe" in act:
                        dx = -400 if act["swipe"] == "left" else 400
                        page.mouse.move(400, 400)
                        page.mouse.down(); page.mouse.move(400+dx, 400); page.mouse.up()
                ok = True
            results.append({"id": t.get("id"), "ok": ok})
        browser.close()
    return type("Report",(object,),{
        "passed": all(r["ok"] for r in results),
        "results": results
    })
