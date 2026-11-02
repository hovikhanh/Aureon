"""Ad-hoc verification (R-DEC-146): run the IDP preprocess/OCR stage over every real file
in `./data` and print a per-file summary (pages, extracted text length, whether OCR ran,
mean OCR confidence). Not a product endpoint — run with `OCR_PROVIDER=paddle uv run python
-m app.scripts.ocr_verify_data`.

This exercises exactly the code path `idp/services/pipeline.py:run_pipeline` uses
(`extract_pages`), so a green run here means real documents in /data are parsed/OCR'd end to
end before classification + extraction.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from app.modules.idp.services.mime import EXT_MIME  # noqa: E402
from app.modules.idp.services.preprocess import extract_pages  # noqa: E402

DATA = Path(__file__).resolve().parents[5] / "data"


def main() -> int:
    files = sorted(p for p in DATA.iterdir() if p.is_file() and p.suffix.lower() in EXT_MIME)
    if not files:
        print(f"no data files under {DATA}")
        return 1
    print(f"OCR verify over {len(files)} files in {DATA}\n")
    print(f"{'file':<42}{'pages':>6}{'text':>8}{'ocr':>5}{'conf':>7}")
    print("-" * 68)
    failures = 0
    for f in files:
        mime = EXT_MIME[f.suffix.lower()]
        try:
            res = extract_pages(f.read_bytes(), mime)
            ocr_pages = [p for p in res.pages if p.ocr_used]
            confs = [p.ocr_confidence for p in ocr_pages if p.ocr_confidence is not None]
            mean_conf = sum(confs) / len(confs) if confs else None
            text_len = len(res.full_text)
            ocr_flag = "yes" if ocr_pages else "no"
            conf_s = f"{mean_conf:.3f}" if mean_conf is not None else "-"
            print(f"{f.name:<42}{res.page_count:>6}{text_len:>8}{ocr_flag:>5}{conf_s:>7}")
            # A document that produced zero text AND used OCR is an OCR failure to flag.
            if text_len == 0 and ocr_pages:
                failures += 1
                print(f"    !! {f.name}: OCR produced no text")
        except Exception as exc:  # pragma: no cover - diagnostic script
            failures += 1
            print(f"{f.name:<42}  ERROR: {type(exc).__name__}: {exc}")
    print("-" * 68)
    print(f"{len(files) - failures}/{len(files)} files parsed with text")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
