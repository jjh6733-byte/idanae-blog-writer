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
CACHE_FILE = os.path.join(DATA_DIR, "posts_cache.json")
PERSONA_FILE = os.path.join(DATA_DIR, "idanae_persona.json")

ANALYSIS_PROMPT = """당신은 한국의 네이버 블로그 콘텐츠 및 문체 전문 분석가입니다.
아래 제공된 블로그 포스팅들은 네이버 블로거 '이다내(idanae)'가 직접 작성한 실제 맛집/카페/꿀템 리뷰 글들입니다.
이 글들을 정밀하게 분석하여, 다른 새로운 주제로 글을 쓸 때 완벽하게 동일한 말투와 포맷으로 글을 작성할 수 있도록 문체 지문(Tone & Persona Profile)을 JSON 형식으로 추출해 주세요.

분석해야 할 핵심 항목:
1. blogger_name: 블로거 이름 및 아이디
2. profile_summary: 블로거의 페르소나, 성격, 텐션, 직업적 정체성 (예: 갓생 사는 직장인 등)
3. intro_patterns: 글을 시작할 때 사용하는 고유의 오프닝 패턴 리스트
4. outro_patterns: 글을 맺을 때 사용하는 시그니처 클로징 멘트 리스트
5. sentence_endings: 자주 사용하는 문장 종결어미 리스트 (~했답니다, ~해볼게요!, ~가셔, ~보셔 등)
6. signature_expressions: 특유의 쉼표(,,) 사용, 주접/위트 멘트, 감탄사 등 고유 표현 리스트
7. emojis: 글 전반 및 소제목에 애용하는 이모지 리스트
8. structure_rules: 제목 형식, 단락 구성 순서, 사진 가이드 형식
9. taste_description_style: 맛/식감/후기 묘사 시 사용하는 특유의 수식어 및 표현 방식

반드시 유효한 JSON 형식만을 반환하세요.
"""

def analyze_persona(api_key: str = None) -> dict:
    """Analyze blog posts and update idanae_persona.json using Gemini API."""
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is required to analyze persona.")

    if not os.path.exists(CACHE_FILE):
        from crawler import crawl_and_cache
        crawl_and_cache(max_posts=15)

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    # Prepare excerpts
    sample_texts = []
    for i, p in enumerate(posts[:6], 1):
        content_preview = p.get("content", "")[:2500]
        sample_texts.append(f"=== [포스팅 {i}] 제목: {p.get('title')} ===\n카테고리: {p.get('category')}\n태그: {', '.join(p.get('tags', [])[:10])}\n본문:\n{content_preview}\n")

    corpus = "\n\n".join(sample_texts)

    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[ANALYSIS_PROMPT, corpus],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    try:
        persona = json.loads(response.text)
        with open(PERSONA_FILE, "w", encoding="utf-8") as f:
            json.dump(persona, f, ensure_ascii=False, indent=2)
        print("Successfully analyzed and saved persona to:", PERSONA_FILE)
        return persona
    except Exception as e:
        print("Failed to parse Gemini response as JSON:", e)
        print("Raw response:", response.text)
        raise

if __name__ == "__main__":
    analyze_persona()
