#!/usr/bin/env python3
"""一次性生成 demo 页面的 QR 码。

跑法：
    pip install qrcode[pil]
    python scripts/gen_qr.py https://huggingface.co/spaces/Silll1/as-skill-demo

输出：docs/qr-demo.png + 控制台打印 ASCII 版本（即时预览）
"""
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_URL = "https://huggingface.co/spaces/Silll1/as-skill-demo"

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "docs" / "qr-demo.png"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    try:
        import qrcode
    except ImportError:
        print("[error] qrcode package not installed.")
        print("        pip install qrcode[pil]")
        print(f"        Or open https://api.qrserver.com/v1/create-qr-code/?size=600x600&data={url}")
        sys.exit(1)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(OUT_PATH)

    print(f"[OK] QR code saved: {OUT_PATH}")
    print(f"     URL: {url}")
    print(f"     Size: {img.size}")
    print()
    print("ASCII preview:")
    print("-" * 40)
    qr.print_ascii(invert=True)


if __name__ == "__main__":
    main()
