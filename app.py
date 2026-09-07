import os
import sys
import json
import streamlit as st

st.set_page_config(
    page_title="이다내(idanae) 블로그 말투 초안 작성기",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #1ec800 0%, #009e49 100%);
        padding: 1.8rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 158, 73, 0.15);
    }
    .main-header h1 {
        color: white !important;
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0 0 0.4rem 0;
    }
    .main-header p {
        color: #e8f8ee !important;
        font-size: 1.05rem;
        margin: 0;
    }
    .badge-ready {
        display: inline-flex;
        align-items: center;
        background-color: #e8f8ee;
        color: #03cf5d;
        font-weight: 700;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        border: 1px solid #b7ebd0;
    }
    .badge-warn {
        display: inline-flex;
        align-items: center;
        background-color: #fffbeb;
        color: #d97706;
        font-weight: 700;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        border: 1px solid #fde68a;
    }
    .title-banner {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #03cf5d;
        border-radius: 8px;
        padding: 0.7rem 1rem;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.4rem;
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

from crawler import crawl_and_cache
from analyzer import analyze_persona
from generator import generate_blog_draft, load_persona, load_few_shots

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PERSONA_FILE = os.path.join(DATA_DIR, "idanae_persona.json")
CACHE_FILE = os.path.join(DATA_DIR, "posts_cache.json")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://blogpfthumb.phinf.naver.net/MjAyNjA1MDhfMjcg/MDAxNzc4MjI3Nzk5Mzk4.lw_24w7_YF_z0wg7E-8WXPXWmRvmJpXx5FTT6o0z6kUg.aBxFt6n0unmDF4Nb7S92pqlF_qEIyOefYraE7yj-hVYg.PNG/profileImage.png?type=m2", width=75)
    st.markdown("### ⚙️ 설정 & 페르소나 상태")
    
    default_key = os.environ.get("GEMINI_API_KEY", "")
    try:
        if not default_key and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            default_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    api_key = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.get("gemini_api_key", default_key),
        type="password",
        placeholder="AI Studio 키 입력",
        help="Google AI Studio (aistudio.google.com)에서 무료 발급받은 Gemini API 키를 입력하세요."
    )
    if api_key:
        st.session_state["gemini_api_key"] = api_key

    st.markdown("---")
    st.markdown("#### 📊 말투 학습 상태")
    persona_ready = os.path.exists(PERSONA_FILE)
    
    if persona_ready:
        st.markdown('<div class="badge-ready">✔ 이다내 말투 학습 완료 (캐시됨)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-warn">▲ 말투 프로필 생성 필요</div>', unsafe_allow_html=True)

    st.caption("기준 블로그: [blog.naver.com/idanae](https://blog.naver.com/idanae)")
    st.caption("※ 매일 올라오는 꼬맨틀 퀴즈 등 비리뷰 글은 자동 배제됩니다.")

    if st.button("🔄 최신 글 재수집 & 말투 재분석"):
        if not api_key:
            st.error("말투를 재분석하려면 Gemini API Key를 입력해주세요.")
        else:
            with st.spinner("이다내 블로그의 최신 글을 수집하고 문체를 정밀 재분석 중입니다..."):
                try:
                    crawl_and_cache(max_posts=15, force_refresh=True)
                    analyze_persona(api_key)
                    st.success("새로운 글들을 반영하여 말투 프로필이 갱신되었습니다! 🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"분석 실패: {e}")

    st.markdown("---")
    st.markdown("💡 **스마트에디터 ONE 팁**\n우측 상단의 복사(📋) 아이콘을 누르면 서식 깨짐 없이 원클릭으로 복사됩니다.")

# --- HEADER ---
st.markdown("""
<div class="main-header">
    <h1>✨ 이다내(idanae) 블로그 말투 초안 생성기</h1>
    <p>기세로 갓생 사는 4년차 직장인 이다내 블로거의 유쾌하고 생생한 문체로 네이버 스마트에디터 맞춤 초안을 완성합니다.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["✍️ 신규 초안 작성", "🧠 학습된 말투 프로필", "📚 수집된 블로그 글 (참고자료)"])

# Sample data helper
if "sample_data" not in st.session_state:
    st.session_state["sample_data"] = False

def fill_sample():
    st.session_state["category_input"] = "살이되고 살이찐(맛집/카페)"
    st.session_state["subject_input"] = "성수 호호식당"
    st.session_state["context_input"] = "주말에 친구랑 성수동 나들이 겸 분위기 좋은 일본 가정식 먹으러 방문!"
    st.session_state["menu_input"] = "· 사케동 — 17,000원\n· 로스가츠정식 — 14,000원\n· 우니 오일 파스타 — 21,000원\n· 레몬 하이볼 — 8,000원"
    st.session_state["taste_input"] = "연어가 두툼하고 신선해서 비린내 1도 없고 밥 간이 기가 막힘. 와사비 올려 먹으면 천국의 맛이다,, 로스가츠는 겉이 진짜 빠짝!!!!!! 속은 육즙 팡팡. 우니 파스타는 우니를 듬뿍 넣어주셔서 풍미가 완전 킥 포인트! 친구랑 싹싹 비워버림 ㅋ"
    st.session_state["store_input"] = "서울 성동구 서울숲4길 25, 뚝섬역 도보 5분, 고즈넉한 한옥 인테리어에 자연광 채광 너무 예쁨, 주차 불가(인근 서울숲 유료주차장 이용)"
    st.session_state["tip_input"] = "주말엔 웨이팅 필수라 테이블링 앱으로 원격 줄서기 꼭 하셔! 화장실에 핸드워시랑 핸드크림 이솝으로 구비해두신 사장님 센스 최고,,"

with tab1:
    col_in, col_out = st.columns([1.05, 1.15], gap="large")
    
    with col_in:
        c_title, c_btn = st.columns([2.5, 1.5])
        with c_title:
            st.markdown("### 📝 방문/체험 메모 입력")
        with c_btn:
            st.button("✨ 예시 데이터 채우기", on_click=fill_sample, use_container_width=True)
        
        category = st.selectbox(
            "카테고리",
            ["살이되고 살이찐(맛집/카페)", "띵동 택배왔어요(식품/꿀템)", "기세좋은 여행일기", "기세로 취미/일상"],
            index=0,
            key="category_input"
        )
        
        subject_name = st.text_input(
            "상호명 또는 제품명*",
            placeholder="예: 한남물터, 성수 호호식당, 르말뒤페이 휘낭시에",
            key="subject_input"
        )
        
        context = st.text_input(
            "방문/구매 계기",
            placeholder="예: 퇴근 후 한잔할 곳 찾다가 발견, 가볍지만 든든한 점심 혼밥",
            key="context_input"
        )
        
        menu_price = st.text_area(
            "주문 메뉴 및 가격",
            placeholder="예:\n· 모둠회와 계절나물무침 — 59,000원\n· 광주식 왕새우무침 — 39,000원",
            height=110,
            key="menu_input"
        )
        
        taste_impressions = st.text_area(
            "솔직한 맛/사용 후기 & 킥포인트*",
            placeholder="예: 회가 엄청 두툼하고 쫀득함. 보통 초장/간장에 먹는데 제철 나물이랑 싸먹는게 완전 미친 조합(킥)! 생새우무침은 양념게장 뺨치는 매콤달콤 밥도둑.",
            height=130,
            key="taste_input"
        )
        
        store_info = st.text_input(
            "위치 / 주차 / 분위기 정보",
            placeholder="예: 서울 용산구 대사관로, 발렛 주차 2시간 가능(5천원), 조도 좋고 힙함",
            key="store_input"
        )
        
        extra_tips = st.text_input(
            "디테일 센스 및 꿀팁",
            placeholder="예: 화장실에 가글 구비된 사장님 센스 최고,, 면 추가는 꼭 하셔!",
            key="tip_input"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("🚀 이다내 말투로 초안 생성하기", type="primary", use_container_width=True)

    with col_out:
        st.markdown("### 📄 생성된 네이버 블로그 초안")
        
        if generate_btn:
            active_key = api_key or os.environ.get("GEMINI_API_KEY", "")
            if not subject_name:
                st.error("상호명 또는 제품명을 입력해 주세요!")
            elif not taste_impressions:
                st.error("솔직한 맛/후기 내용을 입력해 주세요!")
            elif not active_key:
                st.warning("⚠️ 사이드바에 Google Gemini API Key를 입력해 주세요. (무료 발급: aistudio.google.com)")
            else:
                user_notes = {
                    "context": context,
                    "menu_price": menu_price,
                    "taste_impressions": taste_impressions,
                    "store_info": store_info,
                    "extra_tips": extra_tips
                }
                with st.spinner("기세로 갓생 사는 이다내 빙의 중... ✨"):
                    try:
                        result = generate_blog_draft(category, subject_name, user_notes, api_key=active_key)
                        st.session_state["last_draft"] = result
                        st.success("초안 작성이 완료되었습니다! 🎈")
                    except Exception as e:
                        st.error(f"생성 중 오류 발생: {e}")

        draft = st.session_state.get("last_draft")
        if draft:
            # 1. Title candidates
            st.markdown("#### 📌 1. 추천 제목 후보 (원클릭 복사)")
            st.caption("우측 상단 📋 아이콘을 누르면 바로 클립보드에 복사됩니다.")
            titles = draft.get("titles", [])
            for i, t in enumerate(titles, 1):
                st.markdown(f'<div class="title-banner">후보 {i}</div>', unsafe_allow_html=True)
                st.code(t, language="text")

            st.markdown("---")
            
            # 2. Main Body
            st.markdown("#### 📝 2. 본문 초안 (`[사진: ...]` 위치 가이드 포함)")
            st.caption("본문 전체를 복사하여 스마트에디터에 붙여넣고, `[사진: ...]` 위치에 촬영 사진을 첨부하세요.")
            body_text = draft.get("body", "")
            
            col_b1, col_b2 = st.columns([3, 1])
            with col_b2:
                st.download_button(
                    label="💾 .txt 다운로드",
                    data=body_text,
                    file_name=f"{subject_name}_blog_draft.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            st.code(body_text, language="markdown")

            st.markdown("---")
            
            # 3. Tags
            st.markdown("#### 🏷️ 3. 네이버 블로그 맞춤 태그")
            raw_tags = draft.get("tags", [])
            tags_str = ", ".join(raw_tags) if isinstance(raw_tags, list) else str(raw_tags)
            st.caption("아래 태그를 복사하여 네이버 에디터 하단 태그 입력창에 붙여넣으세요.")
            st.code(tags_str, language="text")
        else:
            st.info("👈 왼쪽 폼에 정보를 작성하거나 **'예시 데이터 채우기'**를 누른 뒤 **'초안 생성하기'**를 클릭하세요!")

with tab2:
    st.markdown("### 🧠 학습된 이다내(idanae) 페르소나 & 문체 지문")
    persona = load_persona()
    if persona:
        st.info(f"**💡 페르소나 정의**: {persona.get('profile_summary', '')}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🗣️ 시그니처 종결어미")
            for ending in persona.get("sentence_endings", []):
                st.markdown(f"- `{ending}`")
            
            st.markdown("#### 쉼표(,,) 및 시그니처 표현")
            for expr in persona.get("signature_expressions", []):
                st.markdown(f"- {expr}")
        
        with c2:
            st.markdown("#### ✨ 애용 이모지 & 추임새")
            st.write(" ".join(persona.get("emojis", [])))
            
            st.markdown("#### 📐 글 전개 구조")
            rules = persona.get("structure_rules", {})
            st.markdown(f"**제목 규칙:** `{rules.get('title_format', '')}`")
            st.markdown("**단락 순서:**")
            for step in rules.get("section_flow", []):
                st.markdown(f"- {step}")
            st.markdown(f"**사진 가이드 패턴:** `{rules.get('photo_guide_format', '')}`")
        
        st.markdown("---")
        st.markdown("#### 🎯 오프닝 & 클로징 시그니처 멘트")
        co1, co2 = st.columns(2)
        with co1:
            st.markdown("**자주 쓰는 인트로:**")
            for op in persona.get("intro_patterns", []):
                st.markdown(f"- *{op}*")
        with co2:
            st.markdown("**자주 쓰는 아웃트로:**")
            for cl in persona.get("outro_patterns", []):
                st.markdown(f"- *{cl}*")
    else:
        st.warning("말투 프로필이 없습니다.")

with tab3:
    st.markdown("### 📚 학습에 활용된 실제 블로그 포스팅 목록")
    st.caption("블로그 `idanae`의 실제 최근 리뷰 포스팅 원문 데이터입니다. (꼬맨틀 등 단순 퀴즈 풀이 포스팅 배제 완료)")
    
    posts = load_few_shots(15)
    if posts:
        for p in posts:
            with st.expander(f"[{p.get('category')}] {p.get('title')} ({p.get('pub_date')})"):
                st.markdown(f"🔗 [네이버 블로그 원문 보기]({p.get('url')})")
                st.markdown(f"**태그:** `{', '.join(p.get('tags', []))}`")
                st.markdown("**본문 발췌:**")
                st.text(p.get("content", "")[:1200] + "...")
    else:
        st.info("수집된 포스팅 데이터가 없습니다.")
