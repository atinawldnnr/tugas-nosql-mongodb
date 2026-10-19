import os
import re
import time
import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "bigdata_nosql")
MAX_API_ITEMS = int(os.getenv("MAX_API_ITEMS", "20"))
MAX_WEB_ARTICLES = int(os.getenv("MAX_WEB_ARTICLES", "10"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", "1"))

API_BASE = "https://hacker-news.firebaseio.com/v0"
WEBSITE = "https://realpython.com/"
USER_AGENT = "AcademicNoSQLProject/1.0 (educational data collection)"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def utc_now():
    return datetime.now(timezone.utc)


def stable_id(source, url):
    return hashlib.sha256(f"{source}|{url}".encode("utf-8")).hexdigest()


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def get_page(url):
    response = session.get(url, timeout=20)
    response.raise_for_status()
    return response


def allowed_by_robots(url):
    """Fail closed if robots.txt cannot be checked."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = session.get(robots_url, timeout=10)
        if response.status_code == 404:
            return True
        response.raise_for_status()
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except requests.RequestException:
        print(f"[SKIP] Tidak bisa memeriksa robots.txt: {robots_url}")
        return False


def save_bronze(collection, source, fmt, source_url, payload):
    """
    Simpan hasil sumber apa adanya pada field payload.
    JSON API disimpan sebagai object JSON; HTML disimpan sebagai string.
    $setOnInsert menjaga salinan raw pertama agar tidak tertimpa saat rerun.
    """
    doc = {
        "_id": stable_id(source, source_url),
        "_src": source,
        "_fmt": fmt,
        "ts": utc_now(),
        "source_url": source_url,
        "payload": payload,
    }
    collection.update_one({"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True)


def save_silver(collection, source, url, title, text,
                published_at=None, author=None, score=None, entities=None):
    title = clean_text(title)
    if not title:
        return False

    doc = {
        "_id": stable_id(source, url),
        "source": source,
        "url": url,
        "title": title,
        "text": clean_text(text),
        "published_at": published_at,
        "author": author,
        "score": score,
        "entities": entities or [],
        "processed_at": utc_now(),
    }
    collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
    return True


def collect_hacker_news(bronze, silver):
    print("\n[1/2] Mengambil data dari Hacker News API")
    endpoint = f"{API_BASE}/topstories.json"
    try:
        response = get_page(endpoint)
        ids = response.json()[:MAX_API_ITEMS]
        # Simpan respons daftar ID asli juga ke Bronze.
        save_bronze(bronze, "hacker_news_api", "json", endpoint, ids)
    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] Gagal mengambil daftar ID API: {exc}")
        return

    processed = 0
    for item_id in ids:
        item_url = f"{API_BASE}/item/{item_id}.json"
        try:
            response = get_page(item_url)
            raw = response.json()
            if not raw or raw.get("type") != "story":
                continue

            save_bronze(bronze, "hacker_news_api", "json", item_url, raw)

            story_url = raw.get("url") or (
                f"https://news.ycombinator.com/item?id={item_id}"
            )
            published = None
            if raw.get("time"):
                published = datetime.fromtimestamp(raw["time"], tz=timezone.utc)

            if save_silver(
                silver,
                source="hacker_news_api",
                url=story_url,
                title=raw.get("title"),
                text=raw.get("text", ""),
                published_at=published,
                author=raw.get("by"),
                score=raw.get("score"),
                entities=["technology", "hacker-news"],
            ):
                processed += 1

            time.sleep(REQUEST_DELAY)
        except (requests.RequestException, ValueError) as exc:
            print(f"[WARN] Item API {item_id} dilewati: {exc}")

    print(f"[OK] Cerita API yang diproses: {processed}")


def extract_article_links(homepage_html):
    soup = BeautifulSoup(homepage_html, "html.parser")
    found = []
    host = urlparse(WEBSITE).netloc

    for anchor in soup.select("a[href]"):
        url = urljoin(WEBSITE, anchor["href"])
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != host:
            continue
        if not parsed.path.strip("/"):
            continue
        if parsed.query or parsed.fragment:
            continue
        if url not in found:
            found.append(url)
        if len(found) >= MAX_WEB_ARTICLES:
            break

    return found


def collect_website(bronze, silver):
    print("\n[2/2] Mengambil data dari website Real Python")
    if not allowed_by_robots(WEBSITE):
        print("[SKIP] Akses homepage tidak dapat dipastikan diizinkan.")
        return

    try:
        response = get_page(WEBSITE)
        homepage_html = response.text
        save_bronze(bronze, "realpython_website", "html", WEBSITE, homepage_html)
        links = extract_article_links(homepage_html)
    except requests.RequestException as exc:
        print(f"[ERROR] Gagal mengambil homepage: {exc}")
        return

    processed = 0
    for url in links:
        if not allowed_by_robots(url):
            print(f"[SKIP] Dilewati berdasarkan robots.txt: {url}")
            continue

        try:
            time.sleep(REQUEST_DELAY)
            response = get_page(url)
            raw_html = response.text

            # Bronze berisi HTML respons halaman asli, bukan hasil parsing.
            save_bronze(bronze, "realpython_website", "html", url, raw_html)

            soup = BeautifulSoup(raw_html, "html.parser")
            h1 = soup.find("h1")
            title = h1.get_text(" ", strip=True) if h1 else None
            main = soup.find("main") or soup
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in main.find_all("p")
                if p.get_text(" ", strip=True)
            ]
            article_text = " ".join(paragraphs)

            published = None
            for selector, attr in [
                ({"property": "article:published_time"}, "content"),
                ({"name": "date"}, "content"),
                ({"itemprop": "datePublished"}, "content"),
            ]:
                tag = soup.find("meta", attrs=selector)
                if tag and tag.get(attr):
                    published = tag.get(attr)
                    break

            if save_silver(
                silver,
                source="realpython_website",
                url=url,
                title=title,
                text=article_text,
                published_at=published,
                author=None,
                score=None,
                entities=["programming", "technology"],
            ):
                processed += 1

        except requests.RequestException as exc:
            print(f"[WARN] Halaman website dilewati {url}: {exc}")

    print(f"[OK] Artikel website yang diproses: {processed}")


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        db = client[MONGO_DB]
        bronze = db["bronze_raw"]
        silver = db["silver_articles"]

        silver.create_index("source")
        silver.create_index("title")
        silver.create_index("published_at")
        silver.create_index([("title", "text"), ("text", "text")])

        collect_hacker_news(bronze, silver)
        collect_website(bronze, silver)

        print("\n=== RINGKASAN HASIL AKTUAL ===")
        print("Database:", MONGO_DB)
        print("Bronze total:", bronze.count_documents({}))
        print("Silver total:", silver.count_documents({}))
        print("Silver dari API:", silver.count_documents({"source": "hacker_news_api"}))
        print("Silver dari website:", silver.count_documents({"source": "realpython_website"}))
        print("\nContoh Silver:")
        for doc in silver.find({}, {"title": 1, "source": 1, "url": 1}).limit(3):
            print(doc)
    except PyMongoError as exc:
        print(f"[ERROR] Masalah MongoDB: {exc}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
