-- Skema MySQL untuk database banjir_db
-- Jalankan:  mysql -u root -p < schema_banjir_db.sql

CREATE DATABASE IF NOT EXISTS banjir_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE banjir_db;

CREATE TABLE IF NOT EXISTS lokasi (
  location_id VARCHAR(10)  NOT NULL,
  kota        VARCHAR(50)  NOT NULL,
  sungai      VARCHAR(80),
  provinsi    VARCHAR(80),
  latitude    DOUBLE,
  longitude   DOUBLE,
  elevasi_m   DOUBLE,
  populasi    INT,
  PRIMARY KEY (location_id),
  UNIQUE KEY uq_lokasi_kota (kota)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS debit_harian (
  location_id VARCHAR(10) NOT NULL,
  obs_date    DATE        NOT NULL,
  debit_m3s   DOUBLE      NOT NULL,
  PRIMARY KEY (location_id, obs_date),
  CONSTRAINT fk_debit_lokasi FOREIGN KEY (location_id) REFERENCES lokasi (location_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS hujan_harian (
  location_id VARCHAR(10) NOT NULL,
  obs_date    DATE        NOT NULL,
  hujan_mm    DOUBLE      NOT NULL,
  PRIMARY KEY (location_id, obs_date),
  CONSTRAINT fk_hujan_lokasi FOREIGN KEY (location_id) REFERENCES lokasi (location_id)
) ENGINE=InnoDB;

-- Tabel ini juga dibuat otomatis oleh app.py bila belum ada.
CREATE TABLE IF NOT EXISTS prediksi_log (
  id              INT          NOT NULL AUTO_INCREMENT,
  waktu_prediksi  DATETIME     NOT NULL,
  kota            VARCHAR(50)  NOT NULL,
  tanggal_acuan   DATE,
  tanggal_target  DATE,
  debit_hari_ini  DOUBLE,
  hujan_hari_ini  DOUBLE,
  hujan_sum3      DOUBLE,
  hujan_sum7      DOUBLE,
  prediksi_debit  DOUBLE,
  baseline_debit  DOUBLE,
  status_risiko   VARCHAR(10),
  catatan         VARCHAR(255),
  PRIMARY KEY (id),
  KEY idx_prediksi_kota_waktu (kota, waktu_prediksi)
) ENGINE=InnoDB;
