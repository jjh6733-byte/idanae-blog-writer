import os
import sys
import json
import re
import time
import urllib.parse
import html
import requests
from bs4 import BeautifulSoup

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

EXCLUDE_KEYWORDS = ["꼬맨틀", "꼬멘틀", "정답", "힌트", "유사도", "스포방지", "문제풀이", "월루게임", "단어맞추기"]

def clean_text(text: str) -> str:
    """Remove invisible characters and excessive whitespace."""
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
            return {"content": "", "tags": []}

        soup = BeautifulSoup(resp.text, "html.parser")
        main_container = soup.select_one(".se-main-container, div#postViewArea")
        if not main_container:
            main_container = soup.body

        content_lines = []
        if main_container:
            paragraphs = main_container.select(".se-text-paragraph, p.se_textarea")
            if paragraphs:
                for p in paragraphs:
                    text = p.get_text(" ", strip=True).replace('\u200b', '').strip()
                    if text and text not in content_lines[-1:]:
                        content_lines.append(text)
            else:
                for p in main_container.find_all(["p", "div"]):
                    text = p.get_text(" ", strip=True).replace('\u200b', '').strip()
                    if text and len(text) > 1 and text not in content_lines[-1:]:
                        content_lines.append(text)

        tags = []
        for tag_el in soup.select(".item_tag, .post_tag a, a.tag"):
            t = tag_el.get_text(strip=True).lstrip("#")
            if t and t not in tags:
                tags.append(t)

        full_content = "\n\n".join(content_lines)
        return {"content": clean_text(full_content), "tags": tags}
    except Exception as e:
        print(f"Error fetching log_no {log_no}: {e}")
        return {"content": "", "tags": []}

def crawl_and_cache(max_posts: int = 5, force_refresh: bool = False) -> list:
    """
    Crawl the 5 LATEST restaurant/cafe review posts from Category 7 ('살이되고 살이찐(맛집/카페)')
    or all categories excluding quiz/puzzle posts, in newest-first order.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                posts = json.load(f)
                if posts and len(posts) == max_posts:
                    return posts
        except Exception as e:
            print(f"Failed to read cache: {e}")

    print(f"Fetching latest {max_posts} review posts from blog '{BLOG_ID}'...")
    page = 1
    latest_posts = []

    while len(latest_posts) < max_posts and page <= 5:
        api_url = f"https://blog.naver.com/PostTitleListAsync.naver?blogId={BLOG_ID}&viewdate=&currentPage={page}&categoryNo=0&parentCategoryNo=&countPerPage=30"
        resp = requests.get(api_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            break
        txt = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', resp.text)
        try:
            data = json.loads(txt)
        except Exception as e:
            print(f"Error parsing page {page}: {e}")
            break
        
        post_list = data.get("postList", [])
        if not post_list:
            break
        for p in post_list:
            raw_title = p.get("title", "")
            title = html.unescape(urllib.parse.unquote_plus(raw_title))
            
            if any(kw in title for kw in EXCLUDE_KEYWORDS):
                continue

            latest_posts.append({
                "log_no": str(p.get("logNo")),
                "title": title,
                "pub_date": p.get("addDate", ""),
                "category": "살이되고 살이찐(맛집/카페)",
                "url": f"https://blog.naver.com/{BLOG_ID}/{p.get('logNo')}"
            })
            if len(latest_posts) >= max_posts:
                break
        page += 1

    collected = []
    for idx, p in enumerate(latest_posts[:max_posts], 1):
        log_no = p["log_no"]
        print(f"[{idx}/{max_posts}] Crawling latest review post ({p['pub_date']}): {p['title'][:40]}...")
        details = fetch_post_content(log_no)
        time.sleep(0.15)
        p["content"] = details.get("content", "")
        p["tags"] = details.get("tags", [])
        collected.append(p)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)

    print(f"Successfully cached {len(collected)} LATEST review posts to {CACHE_FILE}")
    return collected

if __name__ == "__main__":
    posts = crawl_and_cache(max_posts=5, force_refresh=True)
    print(f"Total cached: {len(posts)} latest review posts.")
