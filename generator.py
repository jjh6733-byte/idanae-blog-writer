import os
import sys
import json
import time
from google import genai
from google.genai import types

from store_researcher import research_store

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PERSONA_FILE = os.path.join(DATA_DIR, "idanae_persona.json")
CACHE_FILE = os.path.join(DATA_DIR, "posts_cache.json")

def load_persona() -> dict:
    if os.path.exists(PERSONA_FILE):
        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_few_shots(count: int = 3) -> list:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            posts = json.load(f)
            return posts[:count]
    return []

def generate_blog_draft(
    category: str,
    subject_name: str,
    eaten_foods: str = "",
    user_notes: dict = None,
    store_research_data: dict = None,
    api_key: str = None,
    **kwargs
) -> dict:
    """Generate a complete Naver blog draft mimicking idanae's voice with fresh phrasing and researched store info."""
    # Backward compatibility with older callers
    if isinstance(eaten_foods, dict) and user_notes is None:
        user_notes = eaten_foods
        eaten_foods = user_notes.get("eaten_foods", "")
    
    if user_notes is None:
        user_notes = {}
    if not eaten_foods and "eaten_foods" in user_notes:
        eaten_foods = user_notes["eaten_foods"]

    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY가 필요합니다. 사이드바에 API 키를 입력해 주세요.")

    # 1. Store research if not provided
    if not store_research_data or not store_research_data.get("formatted_menu_text"):
        print(f"Auto-researching store '{subject_name}' on the web...")
        try:
            store_research_data = research_store(subject_name, eaten_foods=eaten_foods, api_key=key)
        except Exception as e:
            print(f"Store research error (continuing with fallback): {e}")
            store_research_data = {}

    persona = load_persona()
    few_shots = load_few_shots(3)

    few_shot_context = ""
    for idx, fs in enumerate(few_shots, 1):
        content_sample = fs.get("content", "")[:1500]
        few_shot_context += f"\n\n[실제 이다내 블로그 참고글 {idx}]\n제목: {fs.get('title')}\n태그: {', '.join(fs.get('tags', [])[:8])}\n본문 일부:\n{content_sample}\n"

    system_instruction = f"""당신은 인기 네이버 블로거 '이다내(idanae)'입니다!
'기세로 갓생 사는 직장인 이다내' 특유의 생동감 넘치고 유쾌하며 진솔한 말투로 새로운 네이버 블로그 포스팅 초안을 작성하세요.

[이다내 시그니처 말투 및 스타일 수칙]
1. 문장 종결 및 호흡:
   - 말줄임표(...) 대신 쉼표 두 개(,, 또는 ,,,)를 문장 사이와 끝에 자연스럽게 사용하세요. (예: "여기는 진짜 분위기도 너무 좋은곳,,", "이러고 다음달 다꺼내먹음 ^^")
   - 종결어미: '~했어요', '~했답니다', '~해볼게요!', '~죠 ㅎㅎ', '~있어서 추천드립니다 ㅎㅎ'
   - 친근한 구어체/사투리 권유형: '~꼭 가셔', '나 믿고 한번만 가봐', '~꼭 시키셔 .. 하 ..', '저 ~좀 보셔 ,,'
2. 이모지 활용:
   - 본문 중간과 소제목에 '🤍', '✨', '🤤', '🔥', '📍', '⏰', '☎️', '🚗', '✔' 등을 알맞게 사용하세요.

★ [매우 중요: 문구 및 표현 스타일 절대 수칙 (자연스럽고 대중적인 맛집 블로거 표현)] ★
1. 부자연스러운 AI식 억지 비유나 어색한 신조어 절대 금지:
   - 현실에서 사람들이 쓰지 않는 작위적인 은유나 어색한 비유는 절대 쓰지 마세요.
2. idanae 블로그 문구의 단순 복붙 금지:
   - 기존 블로그 참고글에 나온 특정 문장("이런 다이어트면 맨날하지 ㅋ", "멋지다고 해줘.", "콧구멍으로 얼그레이 자라는 줄" 등)을 그대로 베껴 쓰지 마세요.
3. ★핵심: 다른 2030 인기 맛집 블로거들이 실제로 가장 많이 쓰는 자연스럽고 대중적인 표현 적극 활용!★
   - 방문 & 웨이팅:
     · "여긴 진짜 또간집 예약이에요 ,," / "재방문의사 200%!"
     · "웨이팅 한 보람이 있는 곳 🤍" / "왜 유명한지 한 입 먹자마자 바로 납득함"
     · "비주얼부터 이미 합격 목걸이 증정 🥇"
     · "데이트나 모임 장소로 데려가면 칭찬받을 곳!"
   - 맛 & 식감 묘사:
     · "호불호 없이 누구나 좋아할 맛"
     · "잡내 1도 없고 깔끔함 그 자체"
     · "느끼할 틈 없이 싹 잡아주는 매콤함"
     · "겉바속촉의 정석"
     · "단짠단짠 조합이 아주 기가 막혀요 ㅎㅎ"
     · "완전 밥도둑이 따로 없음 / 탄수화물 폭풍 흡입"
     · "입에 넣자마자 사르르 녹아내림 ,, 🤤"
     · "국물이 진짜 깊고 진해서 해장하러 갔다가 술 생각나는 맛 ㅋ"
     · "마지막 한 입까지 싹싹 긁어먹고 옴"
   - 직장인 현실 공감:
     · "퇴근하고 맛있는 거 먹는 게 찐 힐링이지 ,, 🤍"
     · "오늘 하루 고생한 나에게 주는 확실한 보상!"
     · "맛있는 거 먹으려고 돈 버는 직장인 여기요 🙋‍♀️"
     · "다이어트는 내일부터 하기로 암묵적 합의 봄 ^^"
4. 이다내 특유의 톤앤매너와 결합:
   - 위와 같은 대중적이고 자연스러운 표현들을, 이다내 특유의 **쉼표 호흡(,,)**, **친근한 종결어미(~했어요, ~해볼게요!, ~죠 ㅎㅎ, ~꼭 가셔, 나 믿고 가봐)**, **최애 이모지(🤍, ✨, 🤤, 🔥)**와 자연스럽게 버무려 작성하세요.
5. 불필요한 '공지'나 '택배 공지' 같은 문단은 절대 포함하지 마세요.

[글의 구성 규칙 (스마트에디터 ONE 최적화)]
1. 인트로: 인사 + 방문 계기 + "메뉴랑 가격 그리고 후기까지 야무지게 정리해볼게요~! 같이보시죠 !"
2. 위치 및 정보 박스: 🤍 [상호명] 위치 및 정보 (실제 검색된 주소, 영업시간, 전화번호, 주차 정보 반영)
3. 내부 분위기: 🤍 [상호명] 내부 (조도, 분위기, 데이트/모임/혼밥 추천)
4. 메뉴 및 가격: 🤍 [상호명] 메뉴및가격 (실제 검색된 메뉴명과 가격을 '· 메뉴명 — 가격원' 형식으로 풍성하게 표기)
5. 상세 메뉴 후기: 🤍 [상호명] 후기
   - ★사용자가 실제로 먹은 음식({eaten_foods})을 집중적으로 생생하게 리뷰!
   - 각 메뉴별 식감, 맛의 킥포인트, 참신하고 생생한 의성어/의태어 활용
6. 디테일 센스: 화장실 용품(가글/치실)이나 셀프바, 직원 친절도 등 사장님 센스 칭찬
7. 아웃트로: 총평 요약 + "그럼 다들 오늘도 맛있는하루~!🤍"
8. 사진 안내 가이드: `[사진: ...]` 형태 (외관, 내부, 메뉴판, 주문음식 떼샷, 디테일 클로즈업 등)

[출력 형식]
반드시 다음 키를 가진 JSON 객체로 반환하세요:
{{
  "titles": [
    "제목 후보 1 (이다내 스타일: [지역맛집] 상호명 | 핵심 특징 | 메뉴 가격 후기)",
    "제목 후보 2",
    "제목 후보 3"
  ],
  "body": "완성형 본문 텍스트 (줄바꿈 포함, 사진 가이드 [사진: ...] 포함)",
  "tags": [
    "태그1", "태그2", ... (총 15~20개의 고품질 네이버 블로그 검색 태그)
  ]
}}
"""

    researched_menu = store_research_data.get("formatted_menu_text", "")
    researched_addr = store_research_data.get("address", "")
    researched_hours = store_research_data.get("hours", "")
    researched_phone = store_research_data.get("phone", "")
    researched_parking = store_research_data.get("parking", "")
    researched_reviews = "\n".join([f"- {h}" for h in store_research_data.get("recent_review_highlights", [])])

    prompt = f"""[새로 작성할 블로그 포스팅 정보]
- 카테고리: {category}
- 상호명/제품명: {subject_name}
- 내가 실제로 먹은 음식: {eaten_foods}
- 방문/사용 계기: {user_notes.get('context', '친구 모임 겸 맛있는 음식 먹으러 방문')}
- 솔직한 맛/장단점 및 킥포인트: {user_notes.get('taste_impressions', '')}
- 내가 적은 추가 메모 및 꿀팁: {user_notes.get('extra_tips', '')}

[웹 검색으로 확인된 실제 가게 정보 및 메뉴/가격]
- 주소: {researched_addr}
- 영업시간: {researched_hours}
- 전화번호: {researched_phone}
- 주차 정보: {researched_parking}
- 실제 메뉴 및 가격 리스트:
{researched_menu}
- 최근 방문자 블로그 후기 핵심 포인트:
{researched_reviews}

{few_shot_context}

위 실제 가게 정보와 메뉴/가격을 바탕으로, 내가 먹은 음식({eaten_foods})에 대한 참신하고 생생한 이다내 스타일의 네이버 블로그 초안을 작성해 주세요!"""

    client = genai.Client(api_key=key)

    # Base candidates (Gemini 3.6 Flash and stable fallbacks, excluding discontinued 2.5)
    base_models = [
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    models_to_try = []

    # Try dynamically discovering active Flash models for this API key
    try:
        remote_models = [
            m.name.replace("models/", "")
            for m in client.models.list()
            if "flash" in m.name.lower() and "2.5" not in m.name
        ]
        for bm in base_models:
            if bm in remote_models and bm not in models_to_try:
                models_to_try.append(bm)
        for rm in remote_models:
            if rm not in models_to_try and not rm.endswith("-8b"):
                models_to_try.append(rm)
    except Exception as e:
        print(f"[Gemini API] Could not list models dynamically ({e}), using default list.")

    if not models_to_try:
        models_to_try = base_models

    last_error = None
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                print(f"[Gemini API] Generating draft with model '{model_name}' (attempt {attempt+1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[system_instruction, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.75
                    )
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                result = json.loads(raw_text.strip())
                # Attach researched store data for caller reference
                result["store_research_data"] = store_research_data
                print(f"[Gemini API] Successfully generated draft using '{model_name}'!")
                return result
            except Exception as e:
                last_error = e
                err_str = str(e)
                print(f"[Gemini API] Model '{model_name}' failed: {e}")
                if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                    if attempt == 0:
                        time.sleep(1.5)
                        continue
                    else:
                        break
                elif "404" in err_str or "NOT_FOUND" in err_str or "no longer available" in err_str or "429" in err_str:
                    break
                else:
                    break

    if last_error:
        raise last_error
