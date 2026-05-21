"""One-time repair: extract inline base64 images from HTML files → save as PNG files.

Run from repo root:
    python scripts/fix_inline_images.py
"""
import base64
import re
import sys
from pathlib import Path

DOCS = Path('docs')
IMAGES = DOCS / 'images'
IMAGES.mkdir(parents=True, exist_ok=True)

# Match   src="data:image/png;base64,<b64data>"
IMG_RE = re.compile(r'src="data:image/[^;]+;base64,([^"]+)"')

counter = 0
total_saved_kb = 0


def fix_html(html_path: Path, img_prefix: str) -> int:
    """Replace inline base64 images with external files. Returns count of replacements."""
    global counter, total_saved_kb
    text = html_path.read_text(encoding='utf-8')
    replacements = 0

    def replace_match(m):
        global counter, total_saved_kb
        b64 = m.group(1)
        counter += 1
        fname = f'fig_{counter:04d}.png'
        img_file = IMAGES / fname
        try:
            data = base64.b64decode(b64)
            img_file.write_bytes(data)
            total_saved_kb += len(data) / 1024
        except Exception as e:
            print(f'  Warning: could not decode image {counter}: {e}')
            return m.group(0)  # keep original on error
        return f'src="{img_prefix}{fname}"'

    new_text = IMG_RE.sub(replace_match, text)
    fixed = IMG_RE.subn(lambda m: '', text)[1]  # count originals
    if new_text != text:
        html_path.write_text(new_text, encoding='utf-8')
        return text.count('data:image')
    return 0


total_replaced = 0

# Fix index.html — images/ relative to docs/
index = DOCS / 'index.html'
if index.exists():
    n = fix_html(index, 'images/')
    print(f'  index.html: processed ({counter} images so far)')
    total_replaced += counter

# Fix all archive HTML files — ../images/ relative to docs/archive/
archive_dir = DOCS / 'archive'
for html_file in sorted(archive_dir.glob('????-??-??.html')):
    before = counter
    fix_html(html_file, '../images/')
    added = counter - before
    if added:
        print(f'  archive/{html_file.name}: {added} images')

print(f'\nDone. {counter} images saved to docs/images/ ({total_saved_kb:.0f} KB total).')
print(f'Run: git add docs/ && git commit -m "fix: extract inline images to files" && git push')
