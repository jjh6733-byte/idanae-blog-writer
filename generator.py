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
    eaten_foods: str,
    user_notes: dict,
    store_research_data: dict = None,
    api_key: str = None
) -> dict:
    """Generate a complete Naver blog draft mimicking idanae's voice with fresh phrasing and researched store info."""
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

★ [매우 중요: 참신한 어휘 및 신규 문구 생성 지침 (Novelty Directive)] ★
- 기존 블로그 참고글에 나온 특정 문장이나 관용구(예: "이런 다이어트면 맨날하지 ㅋ", "멋지다고 해줘.", "콧구멍으로 얼그레이 자라는 줄", "생선에 정붙일 틈 없이" 등)를 기계적으로 똑같이 베껴 쓰지 마세요!
- 이다내의 발랄한 성격, 호들갑과 진솔함, 직장인 공감대의 '말투 DNA'는 완벽하게 살리되,
- 이번 글의 음식과 장소에 맞게 **이전에 사용하지 않았던 참신하고 생생한 음식 묘사, 새로운 유쾌한 비유, 신선한 직장인 갓생식 감탄사/주접**을 독창적으로 창작하여 최소 2~3개 이상 포함하세요!
- (예: "한 입 먹자마자 진실의 미간 발동됨 ,,", "이건 법적으로 매일 먹을 수 있게 해줘야 함", "다이어트는 다음 주 월요일부터 다시 시작하기로 뇌랑 합의 봄 ^^", "탄수화물은 날 배신하지 않아 🤍", "사장님한테 비밀 레시피 물어볼 뻔했잖아 ,," 등 매번 새로운 주접 표현 생성)
- 불필요한 '공지'나 '택배 공지' 같은 문단은 절대 포함하지 마세요.

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
    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.5-flash"
    ]

    last_error = None
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[system_instruction, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.75
                    )
                )
                result = json.loads(response.text)
                # Attach researched store data for caller reference
                result["store_research_data"] = store_research_data
                return result
            except Exception as e:
                last_error = e
                err_str = str(e)
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
