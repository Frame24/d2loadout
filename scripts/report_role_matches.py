"""Per-role match totals, inclusion cutoff, WR threshold = max(100, p15) (same as ConfigProcessor)."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "configs", "heroes_data.csv")

ROLE_PCTL_SHARE = 0.0025
ROLE_PCTL_MIN = 100
WR_Q = 0.15
WR_MIN = 100


def inclusion_cutoff(matches_sum: int) -> int:
    return max(ROLE_PCTL_MIN, int(matches_sum * ROLE_PCTL_SHARE))


def main() -> None:
    df = pd.read_csv(CSV)
    qs = [0.10, 0.25, 0.15, 0.30, 0.50, 0.75, 0.90]
    qs = sorted(set(qs))
    print("File:", CSV)
    print(
        "WR threshold per role: max(100, p15) on sample with Matches > max(100, 0.0025*sum_role)"
    )
    print()
    for role in ["pos 1", "pos 2", "pos 3", "pos 4", "pos 5"]:
        m = df.loc[df["Role"] == role, "Matches"].dropna()
        if m.empty:
            print(role, "no rows")
            continue
        ssum = int(m.sum())
        cut = inclusion_cutoff(ssum)
        elig = m[m > cut]
        sample = elig if not elig.empty else m
        thr = max(WR_MIN, int(sample.quantile(WR_Q)))
        print(
            f"{role}: heroes={len(m)}, sum_matches={ssum}, "
            f"inclusion_Matches>{cut}, in_sample={len(sample)}, "
            f"p15_raw={int(sample.quantile(WR_Q))}, wr_threshold=max(100,p15)={thr}"
        )
        parts = []
        for q in qs:
            v = max(1, int(sample.quantile(q)))
            parts.append(f"p{int(q * 100)}={v}")
        print("    ", ", ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
