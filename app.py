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
        margin-bottom: 1.8rem;
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
    .research-box {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 0.9rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

from crawler import crawl_and_cache
from analyzer import analyze_persona
from generator import generate_blog_draft, load_persona, load_few_shots
from store_researcher import research_store

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
        st.markdown('<div class="badge-ready">✔ 20개 리뷰글 학습 완료</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-warn">▲ 말투 프로필 생성 필요</div>', unsafe_allow_html=True)

    st.caption("기준 블로그: [blog.naver.com/idanae](https://blog.naver.com/idanae)")
    st.caption("※ 꼬맨틀 등 단순 퀴즈 풀이 포스팅 100% 배제 완료 (초반 20개 리뷰글 학습)")

    if st.button("🔄 최신 20개 글 재수집 & 말투 재분석"):
        if not api_key:
            st.error("말투를 재분석하려면 Gemini API Key를 입력해주세요.")
        else:
            with st.spinner("이다내 블로그의 20개 리뷰 글을 수집하고 문체를 정밀 재분석 중입니다..."):
                try:
                    crawl_and_cache(max_posts=20, force_refresh=True)
                    analyze_persona(api_key)
                    st.success("20개 리뷰글을 바탕으로 말투 프로필이 갱신되었습니다! 🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"분석 실패: {e}")

    st.markdown("---")
    st.markdown("💡 **스마트에디터 ONE 팁**\n우측 상단의 복사(📋) 아이콘을 누르면 서식 깨짐 없이 원클릭으로 복사됩니다.")

# --- HEADER ---
st.markdown("""
<div class="main-header">
    <h1>✨ 이다내(idanae) 블로그 말투 초안 생성기</h1>
    <p>4년차 직장인 이다내 블로거의 유쾌하고 생생한 문체 + 실시간 가게 메뉴/가격 자동 조회가 결합된 네이버 블로그 맞춤 초안기</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["✍️ 신규 초안 작성", "🧠 학습된 말투 프로필", "📚 수집된 블로그 글 (20개 참고자료)"])

def fill_sample():
    st.session_state["category_input"] = "살이되고 살이찐(맛집/카페)"
    st.session_state["subject_input"] = "성수 호호식당"
    st.session_state["eaten_input"] = "사케동, 로스가츠정식, 우니 오일 파스타, 레몬 하이볼"
    st.session_state["context_input"] = "주말에 친구랑 성수동 나들이 겸 분위기 좋은 일본 가정식 먹으러 방문!"
    st.session_state["taste_input"] = "연어가 두툼하고 신선해서 비린내 1도 없고 밥 간이 기가 막힘. 와사비 올려 먹으면 입에서 사르르 녹아내림,, 로스가츠는 겉이 진짜 파삭파삭 바삭함의 극치인데 속은 육즙 팡팡 촉촉함. 우니 파스타는 우니를 아낌없이 넣어주셔서 감칠맛 폭발! 친구랑 한 톨도 안 남기고 싹 비움 ㅋ"
    st.session_state["tip_input"] = "주말엔 웨이팅 필수라 테이블링 앱으로 원격 줄서기 꼭 하셔! 화장실에 이솝 핸드워시 구비해두신 사장님 센스 최고,,"

with tab1:
    col_in, col_out = st.columns([1.05, 1.15], gap="large")
    
    with col_in:
        c_title, c_btn = st.columns([2.2, 1.8])
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
        
        c_sub1, c_sub2 = st.columns([2.5, 1.5])
        with c_sub1:
            subject_name = st.text_input(
                "상호명 또는 제품명*",
                placeholder="예: 성수 호호식당, 한남물터, 올라포케 문정",
                key="subject_input"
            )
        with c_sub2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            search_menu_btn = st.button("🔍 메뉴/정보 조회", use_container_width=True)

        # Handle explicit store search
        active_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        current_eaten_foods = st.session_state.get("eaten_input", "")
        if search_menu_btn:
            if not subject_name:
                st.warning("상호명을 먼저 입력해 주세요!")
            else:
                with st.spinner(f"'{subject_name}'의 메뉴/가격 및 최근 블로그 후기를 검색 중입니다..."):
                    researched = research_store(subject_name, eaten_foods=current_eaten_foods, api_key=active_key)
                    st.session_state[f"research_{subject_name}"] = researched
                    st.success(f"'{subject_name}'의 메뉴 정보와 최근 후기 정보를 가져왔습니다! 👏")

        cached_research = st.session_state.get(f"research_{subject_name}")
        if cached_research and cached_research.get("formatted_menu_text"):
            with st.expander("🔎 자동 검색된 가게 정보 및 메뉴판 확인", expanded=True):
                if cached_research.get("address"):
                    st.markdown(f"**📍 주소:** {cached_research.get('address')}")
                if cached_research.get("hours"):
                    st.markdown(f"**⏰ 영업시간:** {cached_research.get('hours')}")
                st.markdown("**📋 확인된 메뉴 및 가격표:**")
                st.text(cached_research.get("formatted_menu_text"))
                if cached_research.get("recent_review_highlights"):
                    st.markdown("**💬 최근 블로그 후기 요약:**")
                    for h in cached_research.get("recent_review_highlights"):
                        st.markdown(f"- {h}")

        eaten_foods = st.text_input(
            "🍽️ 내가 실제로 먹은 음식*",
            placeholder="예: 사케동, 로스가츠정식, 우니 오일 파스타 (가격은 몰라도 OK!)",
            help="가격은 비워두시고 드신 음식 이름만 콤마로 간단히 적어주세요. 가게 전체 메뉴 및 가격은 검색을 통해 초안에 자동 반영됩니다.",
            key="eaten_input"
        )
        
        context = st.text_input(
            "방문/구매 계기",
            placeholder="예: 주말 데이트, 퇴근 후 한잔할 곳 찾다가 발견, 점심 혼밥",
            key="context_input"
        )
        
        taste_impressions = st.text_area(
            "솔직한 맛/식감 후기 & 킥포인트*",
            placeholder="예: 연어가 엄청 두툼하고 신선함. 와사비 올려 먹으면 최고! 로스가츠는 겉은 파삭 속은 촉촉 육즙 가득. 우니 파스타는 우니 풍미가 대박이라 완전 킥 포인트였음.",
            height=120,
            key="taste_input"
        )
        
        extra_tips = st.text_input(
            "디테일 센스 및 꿀팁 (선택)",
            placeholder="예: 화장실에 가글 구비된 사장님 센스 최고,, 면 추가는 꼭 하셔!",
            key="tip_input"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("🚀 이다내 말투로 초안 생성하기", type="primary", use_container_width=True)

    with col_out:
        st.markdown("### 📄 생성된 네이버 블로그 초안")
        
        if generate_btn:
            if not subject_name:
                st.error("상호명 또는 제품명을 입력해 주세요!")
            elif not eaten_foods:
                st.error("실제로 드신 음식(메뉴명)을 입력해 주세요!")
            elif not taste_impressions:
                st.error("솔직한 맛/후기 내용을 간단히 적어주세요!")
            elif not active_key:
                st.warning("⚠️ 사이드바에 Google Gemini API Key를 입력해 주세요. (무료 발급: aistudio.google.com)")
            else:
                user_notes = {
                    "context": context,
                    "taste_impressions": taste_impressions,
                    "extra_tips": extra_tips,
                    "eaten_foods": eaten_foods
                }
                
                # Check if store already researched
                store_data = st.session_state.get(f"research_{subject_name}")
                if not store_data:
                    with st.spinner(f"'{subject_name}'의 메뉴/가격 및 최근 후기 정보를 실시간 검색 중입니다... 🔎"):
                        store_data = research_store(subject_name, eaten_foods=eaten_foods, api_key=active_key)
                        st.session_state[f"research_{subject_name}"] = store_data

                with st.spinner("이다내 페르소나로 참신하고 생생한 초안을 작성 중입니다... ✨"):
                    try:
                        try:
                            result = generate_blog_draft(
                                category=category,
                                subject_name=subject_name,
                                eaten_foods=eaten_foods,
                                user_notes=user_notes,
                                store_research_data=store_data,
                                api_key=active_key
                            )
                        except TypeError as te:
                            if "eaten_foods" in str(te):
                                result = generate_blog_draft(
                                    category=category,
                                    subject_name=subject_name,
                                    user_notes=user_notes,
                                    api_key=active_key
                                )
                            else:
                                raise te
                        st.session_state["last_draft"] = result
                        st.session_state["last_store_data"] = store_data
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
            st.markdown("#### 📝 2. 본문 초안 (`[사진: ...]` 위치 가이드 및 실제 메뉴/가격 포함)")
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
        st.success("✨ **업데이트 반영: 참신한 어휘 생성 지침(Novelty Directive)**\n기존 글의 상투적 문구를 복제하지 않고, 이다내 특유의 갓생 직장인 텐션과 쉼표 호흡(,,)을 바탕으로 새롭고 독창적인 맛 표현과 감탄사를 창작하도록 프롬프트가 개편되었습니다.")
        
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
    st.markdown("### 📚 학습에 활용된 실제 블로그 포스팅 목록 (20건)")
    st.caption("블로그 `idanae`의 실제 맛집/카페 카테고리 초창기 리뷰 포스팅 20건입니다. (가장 오래된 순, 꼬맨틀 등 단순 퀴즈 배제 완료)")
    
    posts = load_few_shots(20)
    if posts:
        st.write(f"총 **{len(posts)}개**의 순수 리뷰 포스팅이 학습 및 참고 데이터로 등록되어 있습니다.")
        for idx, p in enumerate(posts, 1):
            with st.expander(f"{idx}. [{p.get('category')}] {p.get('title')} ({p.get('pub_date')})"):
                st.markdown(f"🔗 [네이버 블로그 원문 보기]({p.get('url')})")
                st.markdown(f"**태그:** `{', '.join(p.get('tags', []))}`")
                st.markdown("**본문 발췌:**")
                st.text(p.get("content", "")[:1000] + "...")
    else:
        st.info("수집된 포스팅 데이터가 없습니다.")
