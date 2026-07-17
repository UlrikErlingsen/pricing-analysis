"""Regenerate deterministic fictional example files and starter workbooks."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def main() -> None:
    from tagsignal.examples import historical_demo, randomized_demo, starter_template, valuation_demo
    from tagsignal.io import dataframe_to_xlsx

    def write_pair(frame, stem: str) -> None:
        folder = ROOT / "examples"
        frame.to_csv(folder / f"{stem}.csv", index=False)
        (folder / f"{stem}.xlsx").write_bytes(dataframe_to_xlsx(frame))

    write_pair(randomized_demo(), "tagsignal-fictional-randomized-demo")
    write_pair(historical_demo(), "tagsignal-fictional-historical-demo")
    write_pair(valuation_demo(), "tagsignal-fictional-valuation-demo")
    for mode in ("randomized", "historical", "valuation"):
        (ROOT / "examples" / f"tagsignal-{mode}-starter.xlsx").write_bytes(dataframe_to_xlsx(starter_template(mode)))


if __name__ == "__main__":
    main()
