import os
import sys
import json
import re
import time
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# Set stdout encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

BLOG_ID = "idanae"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_FILE = os.path.join(DATA_DIR, "posts_cache.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": f"https://blog.naver.com/{BLOG_ID}"
}

EXCLUDE_KEYWORDS = ["꼬맨틀", "꼬멘틀", "정답", "힌트", "유사도", "스포방지", "문제풀이", "월루게임"]
EXCLUDE_CATEGORIES = ["매일 문제풀이(맨틀/기타)"]

def is_valid_review_post(title: str, category: str = "") -> bool:
    """Check if post is a genuine review post rather than daily puzzle answer."""
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return False
    for ec in EXCLUDE_CATEGORIES:
        if ec in category:
            return False
    return True

def clean_text(text: str) -> str:
    """Remove invisible zero-width characters and excessive whitespace."""
    if not text:
        return ""
    text = text.replace('\u200b', ' ').replace('\ufeff', ' ').replace('\xa0', ' ')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n\n'.join(lines)

def fetch_post_content(log_no: str) -> dict:
    """Fetch full content for a specific Naver blog post."""
    url = f"https://blog.naver.com/PostView.naver?blogId={BLOG_ID}&logNo={log_no}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        if resp.status_code != 200:
            return {"content": ""}

        soup = BeautifulSoup(resp.text, "html.parser")
        main_container = soup.select_one(".se-main-container, div#postViewArea")
        if not main_container:
            main_container = soup.body

        content_lines = []
        if main_container:
            paragraphs = main_container.select(".se-text-paragraph, p.se_textarea, div.se-component-content")
            if paragraphs:
                for p in paragraphs:
                    text = p.get_text(" ", strip=True)
                    text = text.replace('\u200b', '').strip()
                    if text and text not in content_lines[-1:]:
                        content_lines.append(text)
            else:
                for p in main_container.find_all(["p", "div"]):
                    text = p.get_text(" ", strip=True).replace('\u200b', '').strip()
                    if text and len(text) > 1 and text not in content_lines[-1:]:
                        content_lines.append(text)

        full_content = "\n\n".join(content_lines)
        return {"content": clean_text(full_content)}
    except Exception as e:
        print(f"Error fetching log_no {log_no}: {e}")
        return {"content": ""}

def get_posts_from_rss(max_posts: int = 15) -> list:
    """Extract posts from Naver Blog RSS feed."""
    rss_url = f"https://rss.blog.naver.com/{BLOG_ID}.xml"
    try:
        resp = requests.get(rss_url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return []

    collected_posts = []
    items = root.findall("./channel/item")

    for item in items:
        title = item.findtext("title", "")
        category = item.findtext("category", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        guid = item.findtext("guid", "")
        tags_raw = item.findtext("tag", "")

        log_no_match = re.search(r"/(\d+)", guid) or re.search(r"/(\d+)", link)
        if not log_no_match:
            continue
        log_no = log_no_match.group(1)

        if not is_valid_review_post(title, category):
            continue

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        print(f"Crawling review post [{category}] {title} ({log_no})...")
        details = fetch_post_content(log_no)
        time.sleep(0.2)

        post_data = {
            "log_no": log_no,
            "title": title,
            "category": category,
            "pub_date": pub_date,
            "tags": tags,
            "content": details.get("content", ""),
            "url": f"https://blog.naver.com/{BLOG_ID}/{log_no}"
        }

        if post_data["content"] and len(post_data["content"]) > 100:
            collected_posts.append(post_data)
            if len(collected_posts) >= max_posts:
                break

    return collected_posts

def crawl_and_cache(max_posts: int = 15, force_refresh: bool = False) -> list:
    """Crawl posts and save to cache file."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                posts = json.load(f)
                if posts and len(posts) >= 5:
                    return posts
        except Exception as e:
            print(f"Failed to read cache: {e}")

    posts = get_posts_from_rss(max_posts=max_posts)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    return posts

if __name__ == "__main__":
    posts = crawl_and_cache(max_posts=15, force_refresh=True)
    print(f"Successfully cached {len(posts)} posts.")
