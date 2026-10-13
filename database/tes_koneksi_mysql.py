# -*- coding: utf-8 -*-
"""
Menguji koneksi MySQL dari kredensial di .streamlit/secrets.toml.
Jalankan dari akar proyek: python database/tes_koneksi_mysql.py
"""
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Pustaka tomllib tidak ditemukan. Pastikan Python >= 3.11 atau install tomli.")
        sys.exit(1)

from sqlalchemy import create_engine, text, inspect
from urllib.parse import quote_plus

# Path ke secrets.toml relatif terhadap akar proyek
secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"

if not secrets_path.exists():
    print(f"File secrets.toml tidak ditemukan di {secrets_path}")
    print("Salin .streamlit/secrets.toml.example menjadi .streamlit/secrets.toml dan isi dengan kredensial Anda.")
    sys.exit(1)

with open(secrets_path, "rb") as f:
    cfg = tomllib.load(f)

mysql_cfg = cfg.get("mysql", {})
host = mysql_cfg.get("host", "localhost")
port = mysql_cfg.get("port", 3306)
user = mysql_cfg.get("user", "root")
password = mysql_cfg.get("password", "")
database = mysql_cfg.get("database", "banjir_db")

url = f"mysql+pymysql://{user}:{quote_plus(str(password))}@{host}:{port}/{database}?charset=utf8mb4"

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        insp = inspect(engine)
        tabel = insp.get_table_names()
    print(f"Koneksi berhasil ke {database}@{host}:{port}")
    print(f"Daftar tabel ({len(tabel)}): {', '.join(tabel)}")
except Exception as e:
    print(f"Koneksi gagal: {e}")
    sys.exit(1)
