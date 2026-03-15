"""Generate PDF from the HTML report using Playwright (headless Chromium)."""
from pathlib import Path


def generate_pdf(html_path, pdf_path):
    """
    Render HTML report to PDF using Playwright.
    Waits for MathJax to finish rendering before capturing.
    """
    from playwright.sync_api import sync_playwright

    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path).resolve()

    print(f'  Rendering PDF from {html_path.name}...')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1200, 'height': 900})

        # Load the local HTML file
        page.goto(f'file://{html_path}')

        # Wait for MathJax to finish typesetting
        try:
            page.wait_for_function(
                "() => window.MathJax && window.MathJax.startup && window.MathJax.startup.promise",
                timeout=10000
            )
            page.evaluate("() => window.MathJax.startup.promise")
        except Exception:
            pass  # MathJax might not be present or takes too long

        # Extra wait to ensure images and fonts are loaded
        page.wait_for_timeout(2500)

        # Export as A4 PDF with full backgrounds
        page.pdf(
            path=str(pdf_path),
            format='A4',
            print_background=True,
            margin={
                'top': '16mm',
                'bottom': '16mm',
                'left': '12mm',
                'right': '12mm',
            }
        )

        browser.close()

    size_kb = pdf_path.stat().st_size // 1024
    print(f'  PDF saved: {pdf_path.name} ({size_kb} KB)')
    return pdf_path
