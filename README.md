# Tugas 1 Pengelolaan Big Data — NoSQL MongoDB

## Tujuan
Mengumpulkan data dari dua jenis sumber (API dan website), menyimpan raw data ke Bronze Layer, lalu menormalisasi data ke Silver Layer.

## Arsitektur
- MongoDB dijalankan menggunakan Docker Compose.
- `bronze_raw`: menyimpan respons JSON API atau HTML website pada field `payload`.
- `silver_articles`: menyimpan dokumen artikel dengan struktur seragam.
- Docker named volume `mongodb_data` menjaga data tetap ada setelah container direstart/dibuat ulang tanpa menghapus volume.

## Sumber
1. Hacker News API: https://github.com/HackerNews/API
2. Website Real Python: https://realpython.com/

Program memeriksa `robots.txt` sebelum mengambil halaman website. Akses bisa dilewati bila aturan tidak mengizinkan atau pemeriksaan gagal. Periksa juga ketentuan situs sebelum menjalankan tugas.

## Persyaratan
- Docker Desktop
- Python 3.10 atau lebih baru
- Koneksi internet

## Instalasi di Windows CMD
```bat
cd C:\Users\Asus\tugas-nosql-mongodb
copy .env.example .env
docker compose up -d
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python collector.py
```

Jika folder disimpan di lokasi lain, ganti path `cd` dengan lokasi folder sebenarnya.

## Verifikasi MongoDB
```bat
docker exec -it mongodb-nosql mongosh
```

Di dalam `mongosh`:
```javascript
use bigdata_nosql
show collections
db.bronze_raw.countDocuments({})
db.silver_articles.countDocuments({})
db.bronze_raw.findOne()
db.silver_articles.findOne()
db.silver_articles.distinct("source")
db.silver_articles.find({title: {$regex: "python", $options: "i"}}).limit(5)
```

## Struktur Bronze
```json
{
  "_id": "sha256-id",
  "_src": "hacker_news_api",
  "_fmt": "json",
  "ts": "UTC datetime",
  "source_url": "endpoint URL",
  "payload": "raw JSON object or raw HTML string"
}
```

## Struktur Silver
```json
{
  "_id": "sha256-id",
  "source": "hacker_news_api",
  "url": "source article URL",
  "title": "normalized title",
  "text": "normalized text",
  "published_at": "datetime/string/null",
  "author": "string/null",
  "score": 100,
  "entities": ["technology"],
  "processed_at": "UTC datetime"
}
```

Nilai pada contoh di atas bersifat ilustratif. Gunakan hasil aktual dari program untuk laporan.

## Catatan
- Program membatasi jumlah item untuk mengurangi beban permintaan.
- Bronze menggunakan `$setOnInsert`, sehingga raw pertama tidak tertimpa ketika program dijalankan kembali.
- Silver menggunakan upsert dengan ID deterministik untuk menghindari dokumen duplikat berdasarkan sumber dan URL.
- Website dapat mengubah struktur HTML atau aturan akses. Periksa output aktual dan sesuaikan parser jika diperlukan.
- Jangan menjalankan `docker compose down -v` jika ingin mempertahankan data, karena opsi tersebut menghapus volume yang dikelola Compose.
