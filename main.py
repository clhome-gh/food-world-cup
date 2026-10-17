import random
import uuid
import streamlit as st
from supabase import create_client, Client

# Streamlit Page Setting
st.set_page_config(page_title="급식 월드컵", page_icon="🍱", layout="centered")


# Supabase Connection Initialization
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error("Supabase 연결 설정(secrets)을 확인해주세요.")
    st.stop()

# Initial Candidate List
CANDIDATES = [
    "제육볶음",
    "간장찜닭",
    "가자미순살튀김",
    "돈육불백",
    "미트볼데리야끼볶음",
    "수육",
    "진미채고추장볶음",
    "치즈떡닭갈비",
]


# Initialize State
def init_game():
    shuffled = CANDIDATES.copy()
    random.shuffle(shuffled)
    st.session_state.game_id = str(uuid.uuid4())
    st.session_state.current_round_name = "8강"
    st.session_state.current_candidates = shuffled
    st.session_state.next_candidates = []
    st.session_state.match_index = 0
    st.session_state.winner = None
    st.session_state.db_error = False


if "game_id" not in st.session_state:
    init_game()


# DB Save Match Data
def save_duel(
    game_id: str,
    round_name: str,
    left_menu: str,
    right_menu: str,
    winner: str,
) -> bool:
    try:
        data = {
            "game_id": game_id,
            "round": round_name,
            "left_menu": left_menu,
            "right_menu": right_menu,
            "winner": winner,
        }
        # Save to menu_duels table in public schema
        response = supabase.table("menu_duels").insert(data).execute()
        # Verify insertion
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception as e:
        return False


# Select Winner Logic
def select_winner(selected: str, left: str, right: str):
    if left == right:
        return

    # Try saving to Supabase
    success = save_duel(
        game_id=st.session_state.game_id,
        round_name=st.session_state.current_round_name,
        left_menu=left,
        right_menu=right,
        winner=selected,
    )

    if not success:
        st.session_state.db_error = True
        return

    # Advance to next match/round
    st.session_state.next_candidates.append(selected)
    st.session_state.match_index += 1

    # Check if current round completed
    if st.session_state.match_index * 2 >= len(
        st.session_state.current_candidates
    ):
        if len(st.session_state.next_candidates) == 1:
            # Tournament Finished
            st.session_state.winner = st.session_state.next_candidates[0]
        else:
            # Next Round setup
            if len(st.session_state.next_candidates) == 4:
                st.session_state.current_round_name = "4강"
            elif len(st.session_state.next_candidates) == 2:
                st.session_state.current_round_name = "결승"

            st.session_state.current_candidates = (
                st.session_state.next_candidates.copy()
            )
            st.session_state.next_candidates = []
            st.session_state.match_index = 0


# UI Layout
st.title("🍱 급식 월드컵 🏆")
st.write("최애 급식 반찬을 골라주세요!")

# Error state check
if st.session_state.get("db_error", False):
    st.error(
        "🚨 저장 결과를 확인하지 못했습니다. 대결 저장이 정상적으로 완료되었는지 확인이 필요합니다."
    )
    st.warning("재선택이 잠겼습니다. 다시 시작 버튼을 눌러 다시 시도해주세요.")
    if st.button("처음부터 다시 시작하기", type="primary"):
        init_game()
        st.rerun()

# Winner state check
elif st.session_state.winner:
    st.balloons()
    st.header("🎉 우승 반찬 🎉")
    st.subheader(f"✨ {st.session_state.winner} ✨")
    st.write("축하합니다! 이번 월드컵의 최고의 반찬으로 선정되었습니다.")
    st.markdown("---")
    if st.button("다시 시작하기", type="primary"):
        init_game()
        st.rerun()

# Tournament Ongoing
else:
    match_idx = st.session_state.match_index
    left_menu = st.session_state.current_candidates[match_idx * 2]
    right_menu = st.session_state.current_candidates[match_idx * 2 + 1]

    st.subheader(
        f"[{st.session_state.current_round_name}] {match_idx + 1}번째 대결"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.info(left_menu)
        if st.button(
            f"👍 {left_menu} 선택", key=f"btn_left_{match_idx}", use_container_width=True
        ):
            select_winner(left_menu, left_menu, right_menu)
            st.rerun()

    with col2:
        st.info(right_menu)
        if st.button(
            f"👍 {right_menu} 선택",
            key=f"btn_right_{match_idx}",
            use_container_width=True,
        ):
            select_winner(right_menu, left_menu, right_menu)
            st.rerun()
