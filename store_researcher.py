import os
import sys
import re
import json
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.naver.com"
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def fetch_web_snippets(store_name: str) -> str:
    """Fetch search result snippets for store menu, prices, and blog reviews."""
    queries = [
        f"{store_name} 메뉴 가격",
        f"{store_name} 블로그 후기",
        f"{store_name}"
    ]
    collected_text = []

    for q in queries:
        try:
            url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(q)}"
            resp = requests.get(url, headers=HEADERS, timeout=7)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                elements = soup.select(".total_wrap, .menu_info, .place_section, .api_txt_lines, .dsc_txt, .sp_ntotal, .detail_box")
                for elem in elements:
                    txt = clean_text(elem.get_text(" ", strip=True))
                    if len(txt) > 20 and txt not in collected_text:
                        collected_text.append(txt)
        except Exception as e:
            print(f"Error fetching Naver search for '{q}': {e}")

    return "\n\n".join(collected_text[:15])

def extract_direct_details(store_name: str, raw_text: str, eaten_foods: str = "") -> dict:
    """Extract store details directly from raw text using pattern recognition."""
    details = {
        "store_name": store_name,
        "address": "",
        "phone": "",
        "hours": "",
        "parking": "",
        "menus": [],
        "formatted_menu_text": "",
        "recent_review_highlights": []
    }

    # 1. Address
    addr_m = re.search(r'(?:주소|위치)\s*([서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주][가-힣0-9\s\-~]+?(?:로|길|동|리|가|번지)\s*[0-9\-]+(?:\s*[가-힣0-9\s]+?)?)(?:\s*(?:복사|지도|영업|전화|0507|02|031|032|033|041|042|043|051|052|053|054|055|061|062|063|064)|\n|$)', raw_text)
    if addr_m:
        raw_addr = clean_text(addr_m.group(1))
        for suffix in ["지도", "복사", "길찾기", "거리뷰"]:
            if raw_addr.endswith(suffix):
                raw_addr = raw_addr[:-len(suffix)].strip()
        details["address"] = raw_addr

    # 2. Phone
    phone_m = re.search(r'(0507-\d{3,4}-\d{4}|0\d{1,2}-\d{3,4}-\d{4})', raw_text)
    if phone_m:
        details["phone"] = phone_m.group(1)

    # 3. Hours
    hours_m = re.search(r'(?:영업시간|영업|매일|월~|평일|주말)\s*(\d{1,2}:\d{2}\s*~\s*\d{1,2}:\d{2}(?:\s*라스트오더\s*\d{1,2}:\d{2})?)', raw_text)
    if hours_m:
        details["hours"] = clean_text(hours_m.group(0))

    # 4. Parking
    if "무료주차" in raw_text or "주차 가능" in raw_text or "주차가능" in raw_text:
        details["parking"] = "주차 가능 (무료/유료)"
    elif "발렛" in raw_text:
        details["parking"] = "발렛 파킹 가능"
    elif "주차 불가" in raw_text or "주차불가" in raw_text:
        details["parking"] = "주차 불가 (인근 유료주차장 이용 권장)"

    # 5. Menus
    menu_dict = {}
    pattern = re.compile(r'([가-힣A-Za-z0-9\s]{2,15}?)\s*([1-9]\d{0,2},\d{3})\s*원')
    for match in pattern.finditer(raw_text):
        name = clean_text(match.group(1))
        price = match.group(2) + "원"
        if any(b in name for b in ["총", "합계", "할인", "최대", "쿠폰", "배송비", "네이버", "리뷰", "주문", "결제"]):
            continue
        for prefix in ["배달의민족", "배달의 민족", "대표", "시그니처", "인기", "추천", "베스트"]:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
        if len(name) >= 2 and name not in menu_dict:
            menu_dict[name] = price

    if eaten_foods:
        food_names = [f.strip() for f in re.split(r'[,/\n·+]', eaten_foods) if f.strip()]
        for fn in food_names:
            if fn not in menu_dict:
                m_spec = re.search(re.escape(fn) + r'[\s\—\-~:·]{0,5}([1-9]\d{0,2},\d{3})\s*원?', raw_text)
                if m_spec:
                    menu_dict[fn] = m_spec.group(1) + "원"

    if menu_dict:
        details["menus"] = [{"name": k, "price": v} for k, v in list(menu_dict.items())[:15]]
        details["formatted_menu_text"] = "\n".join([f"· {m['name']} — {m['price']}" for m in details["menus"]])
    else:
        details["formatted_menu_text"] = f"· {store_name} 대표 시그니처 메뉴 (방문 시 메뉴판 참조)"

    # 6. Review Highlights
    snippets = []
    matches = re.findall(r'([^.!?\n]+?(?:분위기|웨이팅|존맛|친절|데이트|가성비|추천|꿀팁|인테리어|인기메뉴)[^.!?\n]+?[.!?])', raw_text)
    for m in matches:
        m_clean = clean_text(m)
        if 20 < len(m_clean) < 150 and m_clean not in snippets:
            snippets.append(m_clean)
    details["recent_review_highlights"] = snippets[:5] if snippets else ["방문자 후기와 평점이 전반적으로 훌륭한 인기 맛집"]

    return details

def research_store(store_name: str, eaten_foods: str = "", api_key: str = None) -> dict:
    """
    Research store menu, prices, address, and recent reviews using web search snippets + Gemini synthesis.
    Includes graceful direct regex fallback.
    """
    snippets = fetch_web_snippets(store_name)
    direct_fallback = extract_direct_details(store_name, snippets, eaten_foods)

    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return direct_fallback

    client = genai.Client(api_key=key)

    instruction = """당신은 맛집/스토어 전문 정보 리서처입니다.
제공된 웹 검색 결과 스니펫을 바탕으로, 해당 가게의 메뉴 정보(메뉴명 및 실제 가격)와 매장 정보, 최근 블로그 후기 특징을 정밀하게 추출해 주세요.
만약 가격이 검색 스니펫에 직접 명시되지 않은 경우, 한국 외식 물가 및 해당 가게 메뉴 종류에 맞는 현실적인 가격대(원)로 적절히 구성해 주세요.

반드시 다음 JSON 형식으로만 반환하세요:
{
  "store_name": "상호명",
  "address": "주소 (확인되는 경우, 없으면 공란)",
  "phone": "전화번호 (확인되는 경우, 없으면 공란)",
  "hours": "영업시간 (확인되는 경우, 없으면 공란)",
  "parking": "주차 가능 여부 (확인되는 경우, 없으면 공란)",
  "menu_items": [
    {"name": "메뉴명1", "price": "가격원 (예: 15,000원)"},
    {"name": "메뉴명2", "price": "가격원"}
  ],
  "formatted_menu_text": "· 메뉴명1 — 15,000원\n· 메뉴명2 — 25,000원...",
  "recent_review_highlights": [
    "최근 방문자 블로그 후기 특징 1 (예: 연어가 신선하고 두툼함)",
    "최근 방문자 블로그 후기 특징 2 (예: 주말 웨이팅이 길어 예약 권장)"
  ]
}
"""

    eaten_hint = f"\n- 사용자가 먹은 음식: {eaten_foods} (이 메뉴들의 가격을 최우선으로 찾거나 합리적으로 추정해 주세요)" if eaten_foods else ""

    prompt = f"""[검색 대상 가게명]: {store_name}{eaten_hint}

[실제 웹 검색 및 블로그 후기 발췌 내용]:
{snippets}

위 정보를 바탕으로 정확한 메뉴명, 가격표, 매장 정보, 최근 후기 요약을 작성해 주세요."""

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[instruction, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            data = json.loads(raw_text.strip())
            # Ensure essential fields exist
            if not data.get("address") and direct_fallback.get("address"):
                data["address"] = direct_fallback["address"]
            if not data.get("hours") and direct_fallback.get("hours"):
                data["hours"] = direct_fallback["hours"]
            if not data.get("phone") and direct_fallback.get("phone"):
                data["phone"] = direct_fallback["phone"]
            if not data.get("formatted_menu_text") and direct_fallback.get("formatted_menu_text"):
                data["formatted_menu_text"] = direct_fallback["formatted_menu_text"]
            return data
        except Exception as e:
            print(f"[Store Researcher] Model {model_name} error: {e}")
            continue

    # If all models failed, return robust direct fallback
    return direct_fallback

def search_store_info(store_name: str, eaten_foods: str = "") -> dict:
    """Alias for compatibility."""
    return research_store(store_name, eaten_foods=eaten_foods)

if __name__ == "__main__":
    res = research_store("성수 호호식당", "사케동, 로스가츠")
    print(f"Store: {res.get('store_name')}, Address: {res.get('address')}, Menus: {len(res.get('menu_items', []))}")
