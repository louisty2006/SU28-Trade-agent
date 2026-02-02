import os

import pandas as pd


BASE_DIR = os.path.dirname(__file__)
# 最終完整股票清單：全部美股 + 港股
SRC = os.path.join(BASE_DIR, "COMPLETE_ALL_STOCKS_FINAL.csv")

OUT_US = os.path.join(BASE_DIR, "us_universe.csv")
OUT_HK = os.path.join(BASE_DIR, "hk_universe.csv")


def main() -> None:
    if not os.path.exists(SRC):
        raise FileNotFoundError(f"Missing source file: {SRC}")

    df = pd.read_csv(SRC)

    required_cols = {"Market", "Exchange", "Symbol"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Source CSV missing columns: {sorted(missing)}")

    # US universe
    us = df[df["Market"] == "US"].copy()
    us["symbol"] = us["Symbol"].astype(str).str.strip()
    us["sector"] = us["Exchange"].fillna("Unknown").astype(str)
    us_out = us[["symbol", "sector"]].dropna(subset=["symbol"]).drop_duplicates()
    us_out.to_csv(OUT_US, index=False, encoding="utf-8-sig")
    print(f"Wrote {OUT_US} ({len(us_out)} symbols)")

    # HK universe (yfinance format: 4-digit + .HK)
    hk = df[df["Market"] == "HK"].copy()
    code = hk["Symbol"].astype(str).str.strip()
    code = code.str.replace(".HK", "", regex=False)
    hk["symbol"] = code.str.zfill(4) + ".HK"
    hk["sector"] = hk["Exchange"].fillna("HKEX").astype(str)
    hk_out = hk[["symbol", "sector"]].dropna(subset=["symbol"]).drop_duplicates()
    hk_out.to_csv(OUT_HK, index=False, encoding="utf-8-sig")
    print(f"Wrote {OUT_HK} ({len(hk_out)} symbols)")


if __name__ == "__main__":
    main()

