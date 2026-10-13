# -*- coding: utf-8 -*-
"""
Memuat riwayat_harian.csv ke tabel lokasi, debit_harian, hujan_harian di MySQL banjir_db.
Jalankan setelah schema_banjir_db.sql:

    python muat_data_mysql.py --host localhost --user root --password "kata_sandi"

Data lama di ketiga tabel dihapus lebih dulu, lalu diisi ulang.
"""
import argparse
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

p = argparse.ArgumentParser()
p.add_argument("--host", default="localhost")
p.add_argument("--port", type=int, default=3306)
p.add_argument("--user", default="root")
p.add_argument("--password", default="")
p.add_argument("--database", default="banjir_db")
p.add_argument("--csv", default=str(Path(__file__).parent.parent / "artifacts_banjir" / "riwayat_harian.csv"))
a = p.parse_args()

eng = create_engine(f"mysql+pymysql://{a.user}:{quote_plus(a.password)}@{a.host}:{a.port}/{a.database}?charset=utf8mb4")
d = pd.read_csv(a.csv, parse_dates=["obs_date"])

lokasi = (d.groupby("location_id").first().reset_index()[
    ["location_id", "kota", "river_name", "province", "latitude", "longitude", "elevation_m", "population"]]
    .rename(columns={"river_name": "sungai", "province": "provinsi", "elevation_m": "elevasi_m", "population": "populasi"}))
debit = d[["location_id", "obs_date", "debit"]].rename(columns={"debit": "debit_m3s"})
hujan = d[["location_id", "obs_date", "hujan"]].rename(columns={"hujan": "hujan_mm"})

with eng.begin() as c:
    for t in ("hujan_harian", "debit_harian", "lokasi"):
        c.execute(text(f"DELETE FROM {t}"))
    lokasi.to_sql("lokasi", c, if_exists="append", index=False)
    debit.to_sql("debit_harian", c, if_exists="append", index=False, chunksize=2000)
    hujan.to_sql("hujan_harian", c, if_exists="append", index=False, chunksize=2000)

print(f"Selesai: {len(lokasi)} lokasi, {len(debit)} baris debit, {len(hujan)} baris hujan.")

