# Tugas 1 Pengelolaan Big Data — NoSQL MongoDB

Dashboard Crawling Data MongoDB menggunakan Streamlit untuk menampilkan hasil pengumpulan dan pengolahan data dari Hacker News API dan website Real Python.

## Tujuan

Mengumpulkan data dari dua jenis sumber (API dan website), menyimpan raw data ke Bronze Layer, lalu menormalisasi data ke Silver Layer dan menampilkan hasilnya melalui dashboard.

## Fitur Dashboard

- Menampilkan jumlah dokumen pada Bronze Layer dan Silver Layer.
- Menampilkan jumlah data berdasarkan sumber API dan website.
- Memvisualisasikan distribusi data menggunakan grafik.
- Memfilter artikel berdasarkan sumber data.
- Mencari artikel berdasarkan judul.
- Menampilkan tabel artikel dari Silver Layer.
- Menampilkan contoh raw data dari Bronze Layer.

## Arsitektur

- MongoDB digunakan sebagai basis data NoSQL.
- MongoDB lokal dijalankan menggunakan Docker Compose.
- `bronze_raw`: menyimpan respons JSON API atau HTML website pada field `payload`.
- `silver_articles`: menyimpan dokumen artikel dengan struktur seragam.
- Docker named volume `mongodb_data` menjaga data tetap ada setelah container direstart atau dibuat ulang tanpa menghapus volume.
- Streamlit digunakan untuk membangun dashboard visualisasi data.

## Sumber Data

1. Hacker News API: https://github.com/HackerNews/API
2. Website Real Python: https://realpython.com/

Program memeriksa `robots.txt` sebelum mengambil halaman website. Akses dapat dilewati apabila aturan tidak mengizinkan atau pemeriksaan gagal. Periksa juga ketentuan situs sebelum menjalankan tugas.

## Teknologi

- Python
- MongoDB
- Docker Compose
- Streamlit
- Pandas
- PyMongo
- Requests
- BeautifulSoup
- python-dotenv

## Persyaratan

- Docker Desktop
- Python 3.10 atau lebih baru
- Koneksi internet

## Instalasi dan Menjalankan Program

Jalankan perintah berikut pada Windows PowerShell dari folder proyek:

```powershell
copy .env.example .env
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python collector.py
```

Pastikan konfigurasi MongoDB pada file `.env` sesuai dengan lingkungan yang digunakan.

Untuk menjalankan dashboard secara lokal:

```powershell
streamlit run dashboard.py
```

Dashboard akan tersedia pada alamat lokal yang ditampilkan oleh Streamlit, biasanya `http://localhost:8501`.

## Struktur Koleksi MongoDB

### Bronze Layer — `bronze_raw`

Menyimpan data mentah dari sumber API dan website.

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

### Silver Layer — `silver_articles`

Menyimpan artikel yang telah dinormalisasi.

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

## Verifikasi Data MongoDB

Masuk ke MongoDB Shell:

```powershell
docker exec -it mongodb-nosql mongosh
```

Kemudian jalankan:

```javascript
use bigdata_nosql
show collections
db.bronze_raw.countDocuments({})
db.silver_articles.countDocuments({})
db.bronze_raw.findOne()
db.silver_articles.findOne()
db.silver_articles.distinct("source")
db.silver_articles.find({
  title: { $regex: "python", $options: "i" }
}).limit(5)
```

## Catatan

- Program membatasi jumlah item untuk mengurangi beban permintaan.
- Bronze menggunakan `$setOnInsert`, sehingga raw pertama tidak tertimpa ketika program dijalankan kembali.
- Silver menggunakan upsert dengan ID deterministik untuk menghindari dokumen duplikat berdasarkan sumber dan URL.
- Website dapat mengubah struktur HTML atau aturan akses. Periksa output aktual dan sesuaikan parser jika diperlukan.
- Jangan menjalankan `docker compose down -v` jika ingin mempertahankan data, karena opsi tersebut menghapus volume yang dikelola Compose.
- Jangan mengunggah file `.env` atau kredensial MongoDB ke repository publik.

## Repository

Kode sumber proyek tersedia pada repository GitHub ini.

**Dashboard:** tautan dashboard online akan ditambahkan setelah proses deployment selesai.