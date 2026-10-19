
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB lokal yang sedang berjalan di Docker
local_client = MongoClient("mongodb://localhost:27017/")
local_db = local_client["bigdata_nosql"]

# Connection string Atlas disimpan di environment variable
atlas_uri = os.getenv("ATLAS_URI")
if not atlas_uri:
    raise ValueError("ATLAS_URI belum diatur di file .env")

atlas_client = MongoClient(atlas_uri, serverSelectionTimeoutMS=10000)

# Tes koneksi sebelum menyalin data
atlas_client.admin.command("ping")
atlas_db = atlas_client["bigdata_nosql"]

for collection_name in ["bronze_raw", "silver_articles"]:
    local_collection = local_db[collection_name]
    atlas_collection = atlas_db[collection_name]

    documents = list(local_collection.find({}))

    if documents:
        # Hindari duplikasi _id jika script dijalankan ulang
        atlas_collection.delete_many({})
        atlas_collection.insert_many(documents)

    print(
        f"{collection_name}: "
        f"{local_collection.count_documents({})} lokal, "
        f"{atlas_collection.count_documents({})} di Atlas"
    )

local_client.close()
atlas_client.close()
print("Pemindahan data selesai.")