"""Extract key figures from arXiv paper PDFs."""
import requests
import os
import base64
from pathlib import Path
import fitz  # PyMuPDF


def extract_figures(paper_id, pdf_url, output_dir, max_figures=2):
    """
    Download PDF and extract the most prominent figures.
    Returns list of base64-encoded images (PNG).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_id = paper_id.replace('/', '_').replace('.', '_')

    try:
        print(f'  Downloading PDF for {paper_id}...')
        headers = {'User-Agent': 'Mozilla/5.0 (research bot; mailto:research@example.com)'}
        resp = requests.get(pdf_url, headers=headers, timeout=45, stream=True)

        # Limit download to 20MB
        content = b''
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 20 * 1024 * 1024:
                print(f'  PDF too large, stopping at 20MB')
                break

        pdf_path = output_dir / f'{safe_id}.pdf'
        with open(pdf_path, 'wb') as f:
            f.write(content)

        doc = fitz.open(str(pdf_path))
        figures = []

        for page_num in range(min(8, len(doc))):
            page = doc[page_num]
            images = page.get_images(full=True)

            for img_info in images:
                xref = img_info[0]
                try:
                    base_img = doc.extract_image(xref)
                except Exception:
                    continue

                w, h = base_img['width'], base_img['height']
                # Filter: must be reasonably large (likely a real figure, not icon)
                if w < 200 or h < 150:
                    continue
                # Filter: not extremely wide/tall banners
                aspect = w / h
                if aspect > 10 or aspect < 0.1:
                    continue

                # Convert to PNG via Pillow for consistency
                img_bytes = base_img['image']
                ext = base_img['ext']
                img_path = output_dir / f'{safe_id}_p{page_num}_fig{len(figures)}.{ext}'

                with open(img_path, 'wb') as f:
                    f.write(img_bytes)

                # Encode as base64 for HTML embedding
                b64 = base64.b64encode(img_bytes).decode('utf-8')
                mime = 'image/png' if ext == 'png' else f'image/{ext}'
                figures.append({
                    'data_uri': f'data:{mime};base64,{b64}',
                    'width': w,
                    'height': h,
                    'page': page_num + 1,
                })

                if len(figures) >= max_figures:
                    break

            if len(figures) >= max_figures:
                break

        doc.close()

        # Clean up temp files
        try:
            os.remove(pdf_path)
            for f in output_dir.glob(f'{safe_id}_*.png'):
                os.remove(f)
            for f in output_dir.glob(f'{safe_id}_*.jpeg'):
                os.remove(f)
        except Exception:
            pass

        print(f'  Extracted {len(figures)} figures from {paper_id}')
        return figures

    except Exception as e:
        print(f'  Figure extraction failed for {paper_id}: {e}')
        return []
