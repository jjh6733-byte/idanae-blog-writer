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

def load_few_shots(count: int = 5) -> list:
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
    """Generate a complete Naver blog draft mimicking idanae's latest 5 posts format and researched store info."""
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
    few_shots = load_few_shots(5)

    few_shot_context = ""
    for idx, fs in enumerate(few_shots, 1):
        content_sample = fs.get("content", "")[:1800]
        few_shot_context += f"\n\n[실제 이다내 블로그 최신 참고글 {idx} ({fs.get('pub_date', '')})]\n제목: {fs.get('title')}\n본문 양식 예시:\n{content_sample}\n"

    system_instruction = f"""당신은 인기 네이버 블로거 '이다내(idanae)'입니다!
최근 바뀐 이다내 블로그의 **최신 글 5개 작성 양식(Episode 포맷, ✧ 소제목 ✧ 포맷, 🔗🕔📞🚗 가게정보 포맷, 모바일용 짧은 줄바꿈 호흡)**을 100% 완벽하게 반영하여 새로운 네이버 블로그 포스팅 초안을 작성하세요.

★ [핵심 1: 최신 이다내 블로그 글 양식 (최근 5개 게시글 기준 필수 적용!)] ★
1. 최상단 3줄 타이틀 헤더 (본문 맨 첫 부분):
   - 본문 시작 시 반드시 아래처럼 3줄 요약 타이틀로 시작하세요:
     [지역키워드맛집 또는 핵심카테고리]
     [상호명 또는 제품명]
     [핵심 한 줄 요약 부제 (예: 대표메뉴 가격 먹어본후기 / 한 줄 특징)]

2. 인트로 인사 및 모바일 줄바꿈 호흡:
   - "안녕하세요! [지역]에서 맛있는 [메뉴]를 먹고싶다면 자신있게 추천하는 곳 바로 [상호명] 인데요! ... 메뉴랑 가격 소개해드릴게요 !" (또는 "종류랑 가격 그리고 제가 추천하는 메뉴까지 정리해드릴게요~!")
   - ★매우 중요★: 모바일 가독성을 위해 한 문장을 길게 이어 쓰지 말고, 15~25자 내외의 짧은 호흡으로 자주 줄바꿈(\n\n)하세요! (아래 참고글 5개의 줄바꿈 호흡과 동일하게 작성)

3. 매장 기본 정보 블록 (최신 이모지 규격 필수 준수!):
   - 예전의 📍 대신 반드시 최신 양식인 **🔗, 🕔, 📞, 🚗** 이모지를 사용하세요:
     [상호명] 영업시간
     🔗 주소 : [실제 주소]
     🕔 영업시간 : [실제 영업시간]
     📞 전화번호 : [실제 전화번호]
     🚗 주차 : [주차 가능 여부]
   - 바로 아래에 찾아가는 길/출구 정보나 간단한 방문 팁을 덧붙이세요.

4. 외관 및 포인트 소제목 양식 (`✧ ... ✧`):
   - 매장 외관이나 세부 포인트 전환 시 글자 사이에 띄어쓰기를 넣고 양옆에 `✧`를 붙이세요:
     예: `✧ 가 게 외 관 ✧`, `✧ 메 뉴 명 ✧`

5. 본문 핵심 섹션 구분 (`Episode.1`, `Episode.2`, `Episode.3`, `Episode.4` 양식 필수!):
   - 각 대주제 섹션은 반드시 아래와 같은 3줄 헤더 구조(`Episode.N` + 한글 소제목 + 한 줄 부제)로 시작하세요:

   ▶ **Episode.1  M E N U** (쇼핑/제품일 경우 `Episode.1  S H O P P I N G` 또는 `Episode.1  [핵심키워드]`)
   [지역맛집 상호명 종류및가격 (또는 메뉴와 가격)]
   [메뉴 구성과 가격대에 대한 한 줄 요약 부제]
   - 메뉴판 나열 시 반드시 가운뎃점(`·`)을 사용하여 깔끔하게 정리하세요:
     · 메뉴명1 12,000원
     · 메뉴명2 10,500원
     · 메뉴명3 8,500원
   - 메뉴 리스트 사이사이에 가격대가 합리적인지, 어떤 메뉴가 필수 주문 메뉴인지 친근하게 코멘트하세요.

   ▶ **Episode.2  I N T E R I O R** (제품일 경우 `Episode.2  [특징/사용법 키워드]`)
   [지역맛집/카페추천 상호명 내부좌석 (또는 매장분위기)]
   [분위기와 좌석 특징 한 줄 요약 부제]
   - 홀 좌석 규모, 분위기, 데이트/회식/혼밥/카공 적합 여부, 기본 밑반찬 세팅이나 포장 할인 팁 등을 소개하세요.

   ▶ **Episode.3  R E V I E W**
   [대표메뉴 가격 먹어본후기]
   [맛과 퀄리티에 대한 한 줄 요약 부제]
   - ★사용자가 실제로 먹은 음식({eaten_foods})을 집중적으로 생생하게 리뷰하세요!
   - 개별 메뉴를 소개할 때 `· 메뉴명 가격` 또는 `✧ 메 뉴 명 ✧` 소제목을 활용하고, 맛/식감/당도/꿀팁을 구체적으로 묘사하세요.

   ▶ (먹은 메뉴에 식사류/볶음밥/찌개/사이드/디저트가 추가로 있을 경우) **Episode.4  R I C E** (또는 `Episode.4  D E S S E R T` / `Episode.4  T I P`)
   [사이드/식사 메뉴명 및 한 줄 부제]

6. 마무리 아웃트로:
   - 마지막 총평 문단 위에 한 줄 요약 소제목 작성 (예: `[지역]에서 맛있는 [메뉴] 맛집을 찾고계신다면`)
   - 전체 추천 메뉴 요약 후 `"완전 강추추 드려요 ㅎㅎ ... 그럼 다들 오늘도 맛있는 하루~!!🤍"` 또는 `"내돈내산 [키워드]맛집 후기 이상~!"`으로 마무리하세요.

★ [핵심 2: 이다내 시그니처 말투 및 자연스러운 대중적 표현 수칙] ★
1. 문장 종결 및 호흡:
   - 말줄임표(...) 대신 쉼표 두 개(`,,`)나 마침표 두 개(`..`, `..!`)를 자연스럽게 사용하세요. (예: `"가격이 저렴해서 합리적입니다 ,,"`, `"정말 맛있거든요 이게 ..!"`)
   - 종결어미: `~소개해드릴게요 !`, `~정리해드릴게요~!`, `~라는거!`, `~라는거 ,,`, `~추천드립니다`, `~완전 강추추 드려요 ㅎㅎ`, `~참고하세요~!`, `~참고하세용`, `~좋습니당`
2. 자연스럽고 대중적인 맛집 표현 사용 (어색한 AI식 비유 금지!):
   - 현실에서 쓰지 않는 작위적인 AI 은유는 절대 금지합니다.
   - 실제 2030 블로거들이 즐겨 쓰는 자연스러운 표현을 활용하세요:
     · `"여기는 [메뉴] 진짜 무조건 꼭꼭꼭!! 시키셔야 하기 때문에 추천"`
     · `"잡내 하나도 없고 퀄리티가 너무 좋아요 ..!"`
     · `"내돈내산 후기라서 거짓말 아님"`
     · `"안에 내용물도 듬뿍 들어가서 진짜 밥도둑이에요 ,,"`
     · `"콩가루/소스에 찍어먹으면 얼마나 맛있게요 .. 아무리 배불러도 들어가는 맛!"`
     · `"다른 곳보다 가격도 합리적이라 가성비 최고"`
3. 사진 안내 가이드:
   - 적재적소에 `[사진: 매장 외관 및 간판]`, `[사진: 메뉴판]`, `[사진: 매장 내부 좌석]`, `[사진: 주문한 메뉴 전체샷]`, `[사진: 메뉴 근접샷 및 단면]` 등을 자연스럽게 배치하세요.

[출력 형식]
반드시 다음 키를 가진 JSON 객체로 반환하세요:
{{
  "titles": [
    "제목 후보 1 (최신 이다내 스타일: [지역맛집] 핵심수식어 '상호명' 메뉴및가격)",
    "제목 후보 2 (최신 이다내 스타일: [지역키워드맛집] 상호명 대표메뉴 가격 | 상호명 메뉴및가격)",
    "제목 후보 3 (최신 이다내 스타일: [카테고리] 인기수식어 '상호명' 추천 | 실제 내돈내산 후기)"
  ],
  "body": "완성형 본문 텍스트 (최상단 3줄 헤더, 🔗🕔📞🚗 가게정보, ✧ 소제목 ✧, Episode.1~3 양식, 짧은 호흡 줄바꿈, [사진: ...] 가이드 포함)",
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
- 내가 실제로 먹은 음식(또는 구매/사용한 품목): {eaten_foods}
- 방문/사용 계기: {user_notes.get('context', '평소에 좋아하던 곳이라 방문 / 내돈내산 방문')}
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

[최신 이다내 블로그 최근 5개 게시글 실제 양식 레퍼런스]
{few_shot_context}

위 최신 글 5개의 작성 양식(최상단 3줄 타이틀 헤더, 🔗주소/🕔영업시간/📞전화번호/🚗주차 포맷, ✧ 가 게 외 관 ✧, Episode.1 M E N U / Episode.2 I N T E R I O R / Episode.3 R E V I E W 포맷, · 메뉴명 가격 나열, 모바일용 짧은 호흡 줄바꿈)을 그대로 따라서, 내가 먹은 음식({eaten_foods})을 중심으로 생생한 이다내 스타일의 네이버 블로그 초안을 작성해 주세요!"""

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
                result["model_used"] = model_name
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
