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

import importlib
import crawler
import analyzer
import generator
import store_researcher
try:
    importlib.reload(generator)
    importlib.reload(store_researcher)
    importlib.reload(analyzer)
except Exception:
    pass

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
        st.markdown('<div class="badge-ready">✔ 최신 5개 리뷰글 양식 학습 완료</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-warn">▲ 말투 프로필 생성 필요</div>', unsafe_allow_html=True)

    st.caption("기준 블로그: [blog.naver.com/idanae](https://blog.naver.com/idanae)")
    st.caption("※ 꼬맨틀 등 퀴즈 포스팅 배제 완료 (최신 5개 리뷰글 & Episode 양식 반영)")

    if st.button("🔄 최신 5개 글 재수집 & 양식 재분석"):
        if not api_key:
            st.error("말투를 재분석하려면 Gemini API Key를 입력해주세요.")
        else:
            with st.spinner("이다내 블로그의 최신 5개 리뷰 글을 수집하고 최신 양식을 정밀 재분석 중입니다..."):
                try:
                    crawl_and_cache(max_posts=5, force_refresh=True)
                    analyze_persona(api_key)
                    st.success("최신 5개 리뷰글을 바탕으로 말투/양식 프로필이 갱신되었습니다! 🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"분석 실패: {e}")

    st.markdown("---")
    st.markdown("💡 **스마트에디터 ONE 팁**\n우측 상단의 복사(📋) 아이콘을 누르면 서식 깨짐 없이 원클릭으로 복사됩니다.")

# --- HEADER ---
st.markdown("""
<div class="main-header">
    <h1>✨ 이다내(idanae) 블로그 말투 초안 생성기</h1>
    <p>최신 5개 게시글 양식(Episode.1~3 포맷, ✧ 소제목 ✧, 🔗🕔📞🚗 가게정보) + 실시간 메뉴/가격 조회가 결합된 맞춤 초안기</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["✍️ 신규 초안 작성", "🧠 학습된 최신 양식 & 말투", "📚 수집된 최신 글 (5개 참고자료)"])

def fill_sample():
    st.session_state["category_input"] = "살이되고 살이찐(맛집/카페)"
    st.session_state["subject_input"] = "성수 호호식당"
    st.session_state["notes_input"] = (
        "- 주문 메뉴: 사케동, 로스가츠정식, 우니 오일 파스타, 레몬 하이볼\n"
        "- 방문 계기: 주말에 친구랑 성수동 나들이 겸 분위기 좋은 일본 가정식 먹으러 방문\n"
        "- 후기: 연어가 두툼하고 신선해서 비린내 1도 없고 밥 간이 기가 막힘. 로스가츠는 겉바속촉 육즙 가득! 우니 파스타는 감칠맛 폭발해서 킥 포인트였음\n"
        "- 꿀팁: 주말엔 웨이팅 필수라 테이블링 앱 원격 줄서기 추천! 화장실에 이솝 핸드워시 구비돼 있음"
    )

with tab1:
    col_in, col_out = st.columns([1.05, 1.15], gap="large")
    
    with col_in:
        c_title, c_btn = st.columns([2.2, 1.8])
        with c_title:
            st.markdown("### 📝 포스팅 정보 & 메모")
        with c_btn:
            st.button("✨ 예시 데이터 채우기", on_click=fill_sample, use_container_width=True)
        
        category = st.selectbox(
            "카테고리",
            ["살이되고 살이찐(맛집/카페)", "띵동 택배왔어요(식품/꿀템)", "기세좋은 여행일기", "기세로 취미/일상", "자유 주제 / 기타"],
            index=0,
            key="category_input"
        )
        
        c_sub1, c_sub2 = st.columns([2.5, 1.5])
        with c_sub1:
            subject_name = st.text_input(
                "주제 / 상호명 / 제품명*",
                placeholder="예: 성수 호호식당, 다이소 어퓨 헤어식초, 오사카 쇼핑리스트",
                key="subject_input"
            )
        with c_sub2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            search_menu_btn = st.button("🔍 정보/메뉴 조회", use_container_width=True)

        # Handle explicit store/subject search
        active_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        current_notes = st.session_state.get("notes_input", "")
        if search_menu_btn:
            if not subject_name:
                st.warning("주제나 상호명/제품명을 먼저 입력해 주세요!")
            else:
                with st.spinner(f"'{subject_name}'의 기본 정보 및 최근 블로그 후기를 검색 중입니다..."):
                    researched = research_store(subject_name, eaten_foods="", api_key=active_key)
                    st.session_state[f"research_{subject_name}"] = researched
                    st.success(f"'{subject_name}'의 정보와 최근 후기 요약을 가져왔습니다! 👏")

        cached_research = st.session_state.get(f"research_{subject_name}")
        if cached_research and (cached_research.get("formatted_menu_text") or cached_research.get("address")):
            with st.expander("🔎 자동 검색된 정보 및 가격/메뉴 확인", expanded=True):
                if cached_research.get("address"):
                    st.markdown(f"**🔗 주소:** {cached_research.get('address')}")
                if cached_research.get("hours"):
                    st.markdown(f"**🕔 영업시간:** {cached_research.get('hours')}")
                if cached_research.get("formatted_menu_text"):
                    st.markdown("**📋 확인된 메뉴/품목 및 가격표:**")
                    st.text(cached_research.get("formatted_menu_text"))
                if cached_research.get("recent_review_highlights"):
                    st.markdown("**💬 최근 블로그 후기 요약:**")
                    for h in cached_research.get("recent_review_highlights"):
                        st.markdown(f"- {h}")

        general_notes = st.text_area(
            "📌 참고사항 / 메모 (자유롭게 작성, 사진만 올려도 OK)",
            placeholder=(
                "글에 들어가길 원하는 내용을 편하게 적어주세요! (음식, 제품, 여행, 일상 모두 가능)\n"
                "예:\n"
                "- 주문한 메뉴 / 구매한 제품명 및 가격\n"
                "- 방문·구매 계기, 좋았던 점, 아쉬운 점, 꿀팁 등"
            ),
            height=180,
            key="notes_input"
        )

        uploaded_images = st.file_uploader(
            "📸 블로그에 첨부할 사진 업로드 (여러 장 가능)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            help="사진을 올리면 AI가 사진 속 내용(메뉴/가격, 제품 디테일, 분위기, 비주얼 등)을 직접 보고 참고사항과 함께 본문을 작성하며 [사진 1], [사진 2] 위치를 잡아줍니다.",
            key="image_uploader"
        )
        if uploaded_images:
            st.caption(f"총 **{len(uploaded_images)}장**의 사진이 첨부되었습니다. 순서대로 본문에 `[사진 1]`, `[사진 2]`... 로 배치됩니다.")
            cols = st.columns(min(4, len(uploaded_images)))
            for idx, img_file in enumerate(uploaded_images):
                with cols[idx % len(cols)]:
                    st.image(img_file, caption=f"사진 {idx + 1}", use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("🚀 이다내 말투로 초안 생성하기", type="primary", use_container_width=True)

    with col_out:
        st.markdown("### 📄 생성된 네이버 블로그 초안")
        
        if generate_btn:
            if not subject_name and not uploaded_images and not general_notes.strip():
                st.error("주제(상호명/제품명)를 입력하거나 참고사항/사진을 첨부해 주세요!")
            elif not general_notes.strip() and not uploaded_images:
                st.error("참고사항을 간단히 적거나 사진을 첨부해 주세요!")
            elif not active_key:
                st.warning("⚠️ 사이드바에 Google Gemini API Key를 입력해 주세요. (무료 발급: aistudio.google.com)")
            else:
                effective_subject = subject_name.strip() if subject_name else "첨부 사진 기반 블로그 포스팅"
                user_notes = {
                    "general_notes": general_notes.strip()
                }
                
                image_payloads = []
                if uploaded_images:
                    for img_file in uploaded_images:
                        image_payloads.append({
                            "name": img_file.name,
                            "mime_type": img_file.type or "image/jpeg",
                            "bytes": img_file.getvalue()
                        })

                # Use cached research if user clicked search, or auto-research only for 맛집/카페
                store_data = st.session_state.get(f"research_{effective_subject}")
                if not store_data:
                    if ("맛집" in category or "카페" in category) and subject_name.strip():
                        with st.spinner(f"'{effective_subject}'의 장소/메뉴 및 최근 후기 정보를 검색 중입니다... 🔎"):
                            store_data = research_store(effective_subject, eaten_foods="", api_key=active_key)
                            st.session_state[f"research_{effective_subject}"] = store_data
                    else:
                        store_data = {}

                spinner_msg = (
                    f"첨부된 사진 {len(image_payloads)}장과 참고사항을 반영해 이다내 말투로 초안을 작성 중입니다... ✨"
                    if image_payloads
                    else "이다내 페르소나로 생생한 초안을 작성 중입니다... ✨"
                )
                with st.spinner(spinner_msg):
                    try:
                        result = generate_blog_draft(
                            category=category,
                            subject_name=effective_subject,
                            eaten_foods="",
                            user_notes=user_notes,
                            store_research_data=store_data,
                            api_key=active_key,
                            images=image_payloads
                        )
                        st.session_state["last_draft"] = result
                        st.session_state["last_store_data"] = store_data
                        model_used = result.get("model_used", "gemini-3.8-flash")
                        st.success(f"초안 작성이 완료되었습니다! (사용 모델: {model_used}) 🎈")
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
                    file_name=f"{(subject_name or '').strip() or 'blog'}_draft.txt",
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
    st.markdown("### 🧠 학습된 이다내(idanae) 최신 양식 & 문체 지문")
    persona = load_persona()
    if persona:
        st.success("✨ **최신 5개 게시글 양식 완벽 반영!**\n최근 변경된 블로그 작성 양식(`최상단 3줄 타이틀 헤더`, `🔗주소 / 🕔영업시간 / 📞전화번호 / 🚗주차`, `✧ 가 게 외 관 ✧`, `Episode.1 M E N U / Episode.2 I N T E R I O R / Episode.3 R E V I E W`, `· 메뉴명 가격` 리스트, 모바일용 짧은 호흡 줄바꿈)을 그대로 적용하여 초안을 생성합니다.")
        
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
            
            st.markdown("#### 📐 최신 글 전개 구조 (Episode 포맷)")
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
    st.markdown("### 📚 참고 중인 최신 블로그 포스팅 목록 (최신 5건)")
    st.caption("블로그 `idanae`의 가장 최근 리뷰 포스팅 5건입니다. (최신순, 꼬맨틀 등 퀴즈 게시글 100% 배제 완료)")
    
    posts = load_few_shots(5)
    if posts:
        st.write(f"총 **{len(posts)}개**의 최신 리뷰 포스팅 양식이 학습 및 참고 데이터로 등록되어 있습니다.")
        for idx, p in enumerate(posts, 1):
            with st.expander(f"{idx}. [{p.get('category')}] {p.get('title')} ({p.get('pub_date')})", expanded=(idx == 1)):
                st.markdown(f"🔗 [네이버 블로그 원문 보기]({p.get('url')})")
                st.markdown("**본문 발췌 (최신 작성 양식):**")
                st.text(p.get("content", "")[:1500] + ("..." if len(p.get("content", "")) > 1500 else ""))
    else:
        st.info("수집된 포스팅 데이터가 없습니다.")
