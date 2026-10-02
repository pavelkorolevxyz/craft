# QR code

```bash
python3 scripts/qr.py https://example.com/ --link
```

It prints a `.qr-link` block: inline SVG with `currentColor`, a two-module margin, `data-qr` with the value and a clickable URL. Do not insert QR as an image or repeat the URL as a second caption. The check compares `data-qr` with the link and scans the code in both themes.
