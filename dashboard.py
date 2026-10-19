
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = st.secrets["ATLAS_URI"]
MONGO_DB = st.secrets.get("MONGO_DB", "bigdata_nosql")

st.title("📊 Dashboard Crawling Data — MongoDB")
st.caption("Visualisasi data Bronze Layer dan Silver Layer")

@st.cache_resource
def get_client():
    return MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

try:
    client = get_client()
    client.admin.command("ping")
    db = client[MONGO_DB]

    bronze = db["bronze_raw"]
    silver = db["silver_articles"]

    bronze_count = bronze.count_documents({})
    silver_count = silver.count_documents({})

    api_count = silver.count_documents(
        {"source": "hacker_news_api"}
    )
    website_count = silver.count_documents(
        {"source": "realpython_website"}
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Bronze Documents", bronze_count)
    col2.metric("Silver Documents", silver_count)
    col3.metric("Data API", api_count)
    col4.metric("Data Website", website_count)

    st.subheader("Distribusi Data Berdasarkan Sumber")

    source_df = pd.DataFrame({
        "Sumber": ["Hacker News API", "Real Python"],
        "Jumlah": [api_count, website_count]
    })

    st.bar_chart(
        source_df.set_index("Sumber"),
        y="Jumlah"
    )

    st.subheader("Cari dan Filter Artikel")

    source_options = [
        "Semua sumber",
        "hacker_news_api",
        "realpython_website"
    ]

    selected_source = st.selectbox(
        "Pilih sumber data",
        source_options
    )

    keyword = st.text_input(
        "Cari berdasarkan judul",
        placeholder="Masukkan kata kunci..."
    )

    query = {}

    if selected_source != "Semua sumber":
        query["source"] = selected_source

    if keyword.strip():
        query["title"] = {
            "$regex": keyword.strip(),
            "$options": "i"
        }

    documents = list(
        silver.find(
            query,
            {
                "_id": 0,
                "source": 1,
                "title": 1,
                "url": 1,
                "author": 1,
                "score": 1,
                "published_at": 1
            }
        ).limit(500)
    )

    if documents:
        df = pd.DataFrame(documents)

        st.write(f"Jumlah artikel yang ditampilkan: {len(df)}")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Tidak ada artikel yang cocok dengan pencarian.")

    st.subheader("Contoh Raw Data — Bronze Layer")

    if st.checkbox("Tampilkan satu dokumen raw"):
        raw = bronze.find_one(
            {},
            {"_id": 0, "payload": 0}
        )

        if raw:
            st.json(raw)
        else:
            st.info("Bronze Layer belum memiliki data.")

    st.caption(
        "Sumber data: Hacker News API dan website Real Python. "
        "Dashboard membaca data langsung dari MongoDB."
    )

except Exception as exc:
    st.error("Tidak dapat terhubung ke MongoDB.")
    st.code(str(exc))
    st.info(
        "Pastikan container mongodb-nosql berjalan "
        "dan konfigurasi koneksi sudah benar."
    )
