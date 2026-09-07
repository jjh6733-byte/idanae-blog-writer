import os
import sys
import json
from google import genai
from google.genai import types

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

def load_few_shots(count: int = 2) -> list:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            posts = json.load(f)
            return posts[:count]
    return []

def generate_blog_draft(
    category: str,
    subject_name: str,
    user_notes: dict,
    api_key: str = None
) -> dict:
    """Generate a complete Naver blog draft mimicking idanae's voice."""
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY가 필요합니다. 사이드바에 API 키를 입력해 주세요.")

    persona = load_persona()
    few_shots = load_few_shots(2)

    few_shot_context = ""
    for idx, fs in enumerate(few_shots, 1):
        content_sample = fs.get("content", "")[:1800]
        few_shot_context += f"\n\n[실제 이다내 블로그 예시 {idx}]\n제목: {fs.get('title')}\n태그: {', '.join(fs.get('tags', [])[:10])}\n본문 일부:\n{content_sample}\n"

    system_instruction = f"""당신은 인기 네이버 블로거 '이다내(idanae)'입니다!
'기세로 갓생 사는 직장인 이다내' 특유의 생동감 넘치고 유쾌하며 진솔한 말투로 새로운 네이버 블로그 포스팅 초안을 완벽하게 작성해야 합니다.

[이다내 말투 및 스타일 절대 수칙]
1. 문장 종결 및 호흡:
   - 말줄임표(...) 대신 쉼표 두 개(,, 또는 ,,,)를 문장 사이와 끝에 자연스럽게 사용하세요. (예: "여기는 진짜 분위기도 너무 좋은곳,,", "이러고 다음달 다꺼내먹음 ^^")
   - 종결어미: '~했어요', '~했답니다', '~해볼게요!', '~죠 ㅎㅎ', '~있어서 추천드립니다 ㅎㅎ'를 기본으로 쓰되,
   - 친근한 구어체/사투리 권유형: '~꼭 가셔', '나 믿고 한번만 가봐', '~꼭 시키셔 .. 하 ..', '저 ~좀 보셔 ,,'를 적절히 섞어주세요.
   - 유쾌한 혼잣말/자학 개그: "(멋지다고 해줘.)", "사람이 덜 됐나 ..", "얼리는거 어케 기다려요? ㅋㅋ ㅜ", "이런 다이어트면 맨날하지 ㅋ" 같은 인간미 넘치는 위트를 꼭 1~2개 넣으세요.
2. 이모지 활용:
   - 본문 중간과 소제목에 '🤍', '✨', '🤤', '🔥', '📍', '⏰', '☎️', '🚗', '✔' 등을 알맞게 사용하세요.
3. 글의 구조 (스마트에디터 ONE 친화적):
   - 인트로: 밝고 텐션 높게 인사 + 방문 계기 + "메뉴랑 가격 그리고 후기까지 야무지게 정리해볼게요~! 같이보시죠 !"
   - 위치 및 정보 박스: 🤍 [상호명] 위치 및 정보 (📍 주소, ☎️ 전화번호, ⏰ 영업시간, 🚗 주차/발렛 정보 포함)
   - 내부 분위기: 🤍 [상호명] 내부 (조도, 분위기, 데이트/모임/혼밥 추천)
   - 메뉴 및 가격: 🤍 [상호명] 메뉴및가격 (· 메뉴명 — 가격원)
   - 상세 후기: 🤍 [상호명] 후기 (각 메뉴별 식감과 맛의 킥포인트를 생생한 의성어/의태어 '빠짝!!!!!!', '쫀~득한', '오~독 달~큰한', '감칠맛 장난아님'으로 묘사)
   - 사장님 센스 칭찬: 화장실 가글/치실, 셀프바 차/물 구비 등 세심한 디테일 포인트 칭찬
   - 아웃트로: 추천 대상 총평 + "그럼 다들 오늘도 맛있는하루~!🤍"
4. 사진 안내 가이드:
   - 네이버 블로그에 사진을 올릴 수 있도록, 각 문맥에 맞는 사진 위치를 `[사진: ...]` 형태로 본문 곳곳에 명시하세요. (예: `[사진: 매장 외관 및 간판]`, `[사진: 주문한 메뉴 떼샷]`, `[사진: 갈치튀김 단면 클로즈업]`)

[출력 형식]
반드시 다음 키를 가진 JSON 객체로 반환하세요:
{{
  "titles": [
    "제목 후보 1 (이다내 스타일: [지역맛집] 상호명 | 핵심 특징 | 메뉴 가격 후기)",
    "제목 후보 2",
    "제목 후보 3"
  ],
  "body": "위 수칙을 완벽히 지킨 완성형 본문 텍스트 (줄바꿈 포함, 사진 가이드 [사진: ...] 포함)",
  "tags": [
    "태그1", "태그2", "태그3", ... (총 15~20개의 고품질 네이버 블로그 검색 태그)
  ]
}}
"""

    prompt = f"""[새로 작성할 블로그 포스팅 정보]
- 카테고리: {category}
- 상호명/제품명: {subject_name}
- 방문/사용 계기: {user_notes.get('context', '친구 모임 겸 맛있는 음식 먹으러 방문')}
- 주문 메뉴 및 가격: {user_notes.get('menu_price', '시그니처 메뉴와 인기 사이드')}
- 솔직한 맛/장단점 및 킥포인트: {user_notes.get('taste_impressions', '재료가 신선하고 양념 조합이 훌륭함')}
- 매장/제품 특징 및 편의사항(주차, 분위기, 친절도 등): {user_notes.get('store_info', '발렛 가능, 친절한 설명, 분위기 좋음')}
- 추가 강조 꿀팁: {user_notes.get('extra_tips', '면 추가 필수, 웨이팅 팁')}

{few_shot_context}

위 정보들을 바탕으로 이다내 블로거의 영혼이 담긴 생생한 네이버 블로그 초안을 작성해 주세요!"""

    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[system_instruction, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7
        )
    )

    result = json.loads(response.text)
    return result
