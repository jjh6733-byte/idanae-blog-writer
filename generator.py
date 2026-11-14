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
    images: list = None,
    **kwargs
) -> dict:
    """Generate a complete Naver blog draft mimicking idanae's latest 5 posts format, researched store info, and attached images."""
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

    # 1. Store research only if explicitly requested or food/cafe category with no data passed
    if store_research_data is None:
        if "맛집" in category or "카페" in category:
            print(f"Auto-researching store '{subject_name}' on the web...")
            try:
                store_research_data = research_store(subject_name, eaten_foods=eaten_foods, api_key=key)
            except Exception as e:
                print(f"Store research error (continuing with fallback): {e}")
                store_research_data = {}
        else:
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

3. 매장/장소 기본 정보 블록 (장소/맛집/오프라인 매장인 경우에만 작성):
   - 오프라인 매장, 맛집, 카페, 여행지 등 위치 정보가 있는 주제일 때만 최신 양식인 **🔗, 🕔, 📞, 🚗** 이모지를 사용해 작성하세요:
     [장소/상호명] 영업시간
     🔗 주소 : [실제 주소]
     🕔 영업시간 : [실제 영업시간]
     📞 전화번호 : [실제 전화번호]
     🚗 주차 : [주차 가능 여부]
   - 온라인 제품, 꿀템, 일반 일상 등 장소가 불필요한 주제라면 위 주소 블록은 과감히 생략하고 바로 본론으로 들어가세요!

4. 외관 및 포인트 소제목 양식 (`✧ ... ✧`):
   - 포인트 전환 시 글자 사이에 띄어쓰기를 넣고 양옆에 `✧`를 붙이세요:
     예: `✧ 가 게 외 관 ✧`, `✧ 메 뉴 명 ✧`, `✧ 실 사 용 후 기 ✧`, `✧ 추 천 포 인 트 ✧`

5. 본문 핵심 섹션 구분 (`Episode.1`, `Episode.2`, `Episode.3` 양식 — 주제에 맞게 유연하게 적용!):
   - 각 대주제 섹션은 반드시 아래와 같은 3줄 헤더 구조(`Episode.N` + 한글 소제목 + 한 줄 부제)로 시작하세요:
   - **맛집/카페 주제인 경우**:
     · `Episode.1  M E N U` (가운뎃점 `· 메뉴명 가격` 리스트 정리 + 추천 코멘트)
     · `Episode.2  I N T E R I O R` (내부 좌석 및 분위기, 방문 팁)
     · `Episode.3  R E V I E W` (실제 먹은 메뉴 상세 후기)
     · (필요 시) `Episode.4  R I C E` / `D E S S E R T`
   - **제품/쇼핑/꿀템/여행/일상 주제인 경우** (주제에 맞춰 자연스럽게 변형):
     · `Episode.1  S H O P P I N G` 또는 `Episode.1  [핵심 제품/주제 키워드]` (제품/아이템 소개, 가격, 스펙 등)
     · `Episode.2  R E V I E W` 또는 `Episode.2  [사용기/특징 키워드]` (실제 사용감, 장단점, 꿀팁)
     · (필요 시) `Episode.3  T I P` 또는 `Episode.3  [추천 포인트]`

6. 마무리 아웃트로:
   - 마지막 총평 문단 위에 한 줄 요약 소제목 작성
   - 전체 추천 포인트 요약 후 `"완전 강추추 드려요 ㅎㅎ ... 그럼 다들 오늘도 맛있는 하루~!!🤍"` (맛집) 또는 `"그럼 다들 즐거운 하루(여행) 되세요~!🤍"` / `"내돈내산 추천템 후기 이상~!"` (일반/쇼핑/일상)으로 자연스럽게 마무리하세요.

★ [핵심 2: 이다내 시그니처 말투 및 자연스러운 대중적 표현 수칙] ★
1. 문장 종결 및 호흡:
   - 말줄임표(...) 대신 쉼표 두 개(`,,`)나 마침표 두 개(`..`, `..!`)를 자연스럽게 사용하세요. (예: `"가격이 저렴해서 합리적입니다 ,,"`, `"정말 좋거든요 이게 ..!"`)
   - 종결어미: `~소개해드릴게요 !`, `~정리해드릴게요~!`, `~라는거!`, `~라는거 ,,`, `~추천드립니다`, `~완전 강추추 드려요 ㅎㅎ`, `~참고하세요~!`, `~참고하세용`, `~좋습니당`
2. 자연스럽고 대중적인 표현 사용 (어색한 AI식 비유 금지!):
   - 현실에서 쓰지 않는 작위적인 AI 은유는 절대 금지합니다.
   - 실제 2030 블로거들이 즐겨 쓰는 자연스럽고 공감 가는 표현을 주제에 맞게 활용하세요.
3. 사진 안내 가이드 및 첨부 이미지 활용:
   - 사용자가 사진을 첨부한 경우, 각 사진(사진 1, 사진 2, ...)의 내용을 직접 눈으로 보고 파악해 본문에 생생하게 반영하세요!
     · 메뉴판/가격표/영수증 사진이 있다면 사진 속 품목과 가격을 정확히 읽어 본문에 반영하세요.
     · 음식/제품/풍경 사진이 있다면 실제 비주얼(색감, 구성, 디자인, 분위기, 디테일 등)을 자연스럽게 묘사하세요.
     · 매장 외관/내부 사진이 있다면 인테리어 분위기, 좌석 형태, 간판 느낌 등을 녹여 쓰세요.
     · 본문 내 사진 배치 위치에는 첨부된 사진 번호와 맞춰 `[사진 1: 설명]`, `[사진 2: 설명]` 형태로 모두 알맞은 위치에 넣어주세요.
   - 첨부된 사진이 없는 경우에는 주제에 맞게 `[사진: ...] ` 가이드를 자연스럽게 배치하세요.

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

    store_info_section = ""
    if any([researched_addr, researched_hours, researched_phone, researched_parking, researched_menu, researched_reviews]):
        store_info_section = f"""
[웹 검색으로 확인된 실제 가게/정보 및 메뉴/가격]
- 주소: {researched_addr}
- 영업시간: {researched_hours}
- 전화번호: {researched_phone}
- 주차 정보: {researched_parking}
- 확인된 메뉴/품목 및 가격:
{researched_menu}
- 최근 방문자/사용자 블로그 후기 핵심 포인트:
{researched_reviews}
"""

    general_notes = user_notes.get("general_notes", "").strip()
    if not general_notes:
        parts = []
        if eaten_foods:
            parts.append(f"- 주요 품목/메뉴: {eaten_foods}")
        if user_notes.get("context"):
            parts.append(f"- 방문/구매/작성 계기: {user_notes.get('context')}")
        if user_notes.get("taste_impressions"):
            parts.append(f"- 솔직한 후기/느낀 점: {user_notes.get('taste_impressions')}")
        if user_notes.get("extra_tips"):
            parts.append(f"- 추가 메모 및 꿀팁: {user_notes.get('extra_tips')}")
        general_notes = "\n".join(parts)

    image_notice = ""
    if images:
        image_names = ", ".join([f"사진 {i}: {img.get('name', f'image_{i}')}" for i, img in enumerate(images, 1)])
        image_notice = f"\n[첨부된 사진 목록 (총 {len(images)}장)]\n- {image_names}\n- 아래 함께 전달된 사진들을 직접 분석하여 내용, 가격, 분위기, 비주얼을 본문에 반영하고, 각 사진이 들어갈 가장 자연스러운 위치에 `[사진 1: ...]`, `[사진 2: ...]` 형식으로 전부 배치해 주세요!\n"

    prompt = f"""[새로 작성할 블로그 포스팅 정보]
- 카테고리: {category}
- 주제 / 상호명 / 제품명: {subject_name}
- 사용자 참고사항 & 메모:
{general_notes if general_notes else "(별도 텍스트 메모 없음 — 첨부된 사진과 주제/웹 검색 정보를 바탕으로 자연스럽게 작성해 주세요)"}
{image_notice}{store_info_section}
[최신 이다내 블로그 최근 5개 게시글 실제 양식 레퍼런스]
{few_shot_context}

위 최신 글 5개의 작성 양식(최상단 3줄 타이틀 헤더, 장소인 경우 🔗주소/🕔영업시간/📞전화번호/🚗주차 포맷, `✧ 소 제 목 ✧`, `Episode.1 / Episode.2 / Episode.3` 포맷, 가운뎃점 `·` 리스트, 모바일용 짧은 호흡 줄바꿈)을 주제({category} / {subject_name})에 맞게 자연스럽게 적용하여, 참고사항과 첨부 사진을 중심으로 생생한 이다내 스타일의 네이버 블로그 초안을 작성해 주세요!"""

    contents_payload = [system_instruction, prompt]
    _append_image_parts(contents_payload, images)
    result = _call_gemini_json(key, contents_payload, temperature=0.75)
    result["store_research_data"] = store_research_data
    return result

def _call_gemini_json(api_key: str, contents_payload: list, temperature: float = 0.75) -> dict:
    """Call Gemini Flash models with fallback and parse JSON output."""
    client = genai.Client(api_key=api_key)

    # Base candidates (Gemini 3.8 / 3.7 / 3.6 Flash and stable fallbacks, excluding discontinued 2.5)
    base_models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    models_to_try = []

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
                print(f"[Gemini API] Calling model '{model_name}' (attempt {attempt+1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents_payload,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=temperature
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
                result["model_used"] = model_name
                print(f"[Gemini API] Success using '{model_name}'!")
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
    raise RuntimeError("No Gemini models succeeded.")


def _append_image_parts(contents_payload: list, images: list | None) -> None:
    if not images:
        return
    for idx, img in enumerate(images, 1):
        img_bytes = img.get("bytes")
        mime_type = img.get("mime_type") or "image/jpeg"
        if img_bytes:
            contents_payload.append(f"\n[첨부 사진 {idx} ({img.get('name', '')})]")
            contents_payload.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))


def revise_blog_draft(
    current_draft: dict,
    feedback: str,
    category: str = "",
    subject_name: str = "",
    api_key: str = None,
    images: list = None,
) -> dict:
    """Revise an existing blog draft based on user feedback while keeping the idanae persona."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API Key가 필요합니다.")
    if not feedback or not feedback.strip():
        raise ValueError("수정 요청할 피드백 내용을 입력해 주세요.")

    persona = load_persona()
    endings = ", ".join(persona.get("sentence_endings", []))
    expressions = ", ".join(persona.get("signature_expressions", []))
    emojis = " ".join(persona.get("emojis", []))

    draft_snapshot = {
        "titles": current_draft.get("titles", []),
        "body": current_draft.get("body", ""),
        "tags": current_draft.get("tags", []),
    }

    system_instruction = f"""당신은 네이버 블로거 '이다내(idanae)' 본인입니다.
방금 작성한 블로그 초안에 대해 사용자가 수정 피드백을 주었습니다.
사용자의 피드백을 정확히 반영해 초안을 수정하되, 아래의 이다내 문체와 포맷 규칙은 반드시 유지하세요:
1. 종결어미({endings}), 시그니처 표현({expressions}), 이모지({emojis}) 유지
2. 모바일 가독성을 위한 짧은 호흡의 줄바꿈(15~25자 내외) 유지
3. 최상단 3줄 타이틀 헤더, `✧ 소 제 목 ✧`, `Episode.1 / 2 / 3`, `[사진 N: ...]` 배치 가이드 등 기존 구조는 피드백에서 변경을 요청한 부분 외에는 일관되게 유지
4. 피드백과 무관한 기존 정보나 사실관계를 임의로 삭제하거나 왜곡하지 말 것
5. 반드시 유효한 JSON 포맷으로만 응답할 것 (마크다운 코드블록 없이 순수 JSON):
   {{"titles": ["제목1", "제목2", "제목3"], "body": "수정된 본문 전체", "tags": ["태그1", "태그2", ...]}}"""

    prompt = f"""[주제 / 카테고리]
카테고리: {category or '미지정'}
주제: {subject_name or '미지정'}

[현재 초안 (JSON)]
{json.dumps(draft_snapshot, ensure_ascii=False, indent=2)}

[사용자 수정 피드백]
{feedback.strip()}

위 피드백을 충실히 반영하여 수정된 전체 초안(titles, body, tags)을 JSON으로 출력해 주세요."""

    contents_payload = [system_instruction, prompt]
    _append_image_parts(contents_payload, images)
    result = _call_gemini_json(key, contents_payload, temperature=0.65)
    if "store_research_data" in current_draft:
        result["store_research_data"] = current_draft["store_research_data"]
    return result
