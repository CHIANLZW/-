# -*- coding: utf-8 -*-
"""Process operation certificate images only; update manifest.operation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from process_credentials import (
    MANIFEST,
    OUT,
    display_title,
    file_base,
    load_image,
    pick_operation_files,
    redact_privacy,
    source_rel,
)


def main() -> None:
    op_out = OUT / "operation"
    op_out.mkdir(parents=True, exist_ok=True)
    for old in op_out.glob("*.jpg"):
        old.unlink()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    operation: list[dict] = []

    for idx, src in enumerate(pick_operation_files(), start=1):
        out_name = f"operation-{idx:02d}.jpg"
        out_path = op_out / out_name
        base = file_base(src)
        try:
            img = load_image(src)
            img = redact_privacy(img)
            img.save(out_path, "JPEG", quality=92, optimize=True)
            operation.append(
                {
                    "file": f"assets/images/credentials/operation/{out_name}",
                    "title": display_title(src, "operation"),
                    "source": source_rel(src, base),
                }
            )
            print(f"OK {out_name} <- {src.name}")
        except Exception as exc:
            print(f"FAIL {src}: {exc}")

    manifest["operation"] = operation
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"operation cases: {len(operation)}")


if __name__ == "__main__":
    main()
