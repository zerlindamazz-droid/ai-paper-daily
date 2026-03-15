"""Extract key figures from arXiv paper PDFs by rendering pages as images."""
import requests
import os
import base64
from pathlib import Path
import fitz  # PyMuPDF


def extract_figures(paper_id, pdf_url, output_dir, max_figures=2):
    """
    Download PDF and render pages as images to capture figures.
    Returns list of dicts with base64-encoded PNG data URIs.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_id = paper_id.replace('/', '_').replace('.', '_')
    pdf_path = output_dir / f'{safe_id}.pdf'

    try:
        print(f'  Downloading PDF for {paper_id}...')
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)',
            'Accept': 'application/pdf',
        }
        resp = requests.get(pdf_url, headers=headers, timeout=45, stream=True)
        resp.raise_for_status()

        # Limit download to 25MB
        content = b''
        for chunk in resp.iter_content(chunk_size=65536):
            content += chunk
            if len(content) > 25 * 1024 * 1024:
                print(f'  PDF >25MB, truncating')
                break

        with open(pdf_path, 'wb') as f:
            f.write(content)

        doc = fitz.open(str(pdf_path))
        figures = []

        # Render pages 1-6 at 1.5x zoom and find pages with large figures
        zoom = 1.5
        mat = fitz.Matrix(zoom, zoom)

        for page_num in range(min(6, len(doc))):
            page = doc[page_num]

            # Skip pages that are mostly text (low image area ratio)
            # Use image blocks to detect figure-heavy pages
            blocks = page.get_text('dict')['blocks']
            img_area = sum(
                (b['bbox'][2] - b['bbox'][0]) * (b['bbox'][3] - b['bbox'][1])
                for b in blocks if b['type'] == 1  # type 1 = image block
            )
            page_area = page.rect.width * page.rect.height

            # Also check for drawing elements (vector figures)
            drawings = page.get_drawings()
            has_drawings = len(drawings) > 10  # pages with figures have many drawing commands

            if img_area / page_area > 0.05 or has_drawings:
                # Render this page as PNG
                pix = page.get_pixmap(matrix=mat, alpha=False)
                png_bytes = pix.tobytes('png')
                b64 = base64.b64encode(png_bytes).decode('utf-8')

                figures.append({
                    'data_uri': f'data:image/png;base64,{b64}',
                    'width': pix.width,
                    'height': pix.height,
                    'page': page_num + 1,
                })

                if len(figures) >= max_figures:
                    break

        doc.close()
        print(f'  Extracted {len(figures)} figures from {paper_id}')
        return figures

    except Exception as e:
        print(f'  Figure extraction failed for {paper_id}: {e}')
        return []
    finally:
        try:
            if pdf_path.exists():
                os.remove(pdf_path)
        except Exception:
            pass
