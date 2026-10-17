import random
import uuid
import pandas as pd
import plotly.express as px
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
        response = supabase.table("menu_duels").insert(data).execute()
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception:
        return False


# Select Winner Logic
def select_winner(selected: str, left: str, right: str):
    if left == right:
        return

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

    st.session_state.next_candidates.append(selected)
    st.session_state.match_index += 1

    if st.session_state.match_index * 2 >= len(
        st.session_state.current_candidates
    ):
        if len(st.session_state.next_candidates) == 1:
            st.session_state.winner = st.session_state.next_candidates[0]
        else:
            if len(st.session_state.next_candidates) == 4:
                st.session_state.current_round_name = "4강"
            elif len(st.session_state.next_candidates) == 2:
                st.session_state.current_round_name = "결승"

            st.session_state.current_candidates = (
                st.session_state.next_candidates.copy()
            )
            st.session_state.next_candidates = []
            st.session_state.match_index = 0


# Fetch Analysis Data from Supabase
def fetch_analysis_data():
    try:
        # Select id, game_id, round, left_menu, right_menu, winner columns
        res = (
            supabase.table("menu_duels")
            .select("id, game_id, round, left_menu, right_menu, winner")
            .execute()
        )
        data = res.data
        return data, None
    except Exception as e:
        return None, str(e)


# Render Analytics View
def render_analytics():
    st.markdown("---")
    st.header("📊 학급 전체 대결 기록 분석")

    if st.button("🔄 분석 결과 다시 불러오기"):
        st.cache_data.clear()
        st.rerun()

    data, error = fetch_analysis_data()

    if error:
        st.error(f"🚨 기록을 불러오는 중 오류가 발생했습니다: {error}")
        return

    if not data or len(data) == 0:
        st.info("ℹ️ 아직 저장된 대결 기록이 없습니다. 월드컵에 참여해 보세요!")
        return

    total_records = len(data)
    game_ids = set(row["game_id"] for row in data if row.get("game_id"))
    total_games = len(game_ids)

    st.caption(
        f"💡 **집계 안내**: 총 **{total_records}건**의 대결 기록과 **{total_games}개**의 판(게임)을 바탕으로 분석했습니다. "
        "기록 수와 실제 참여 인원은 다를 수 있으며, 진행 중에 남긴 대결 기록도 포함되어 있습니다."
    )

    # Initialize stats dictionary for all candidates
    stats = {
        menu: {"duels": 0, "wins": 0, "championships": 0} for menu in CANDIDATES
    }

    for row in data:
        left = row.get("left_menu")
        right = row.get("right_menu")
        winner = row.get("winner")
        round_name = row.get("round")

        # Count duels for both left and right menu
        if left in stats:
            stats[left]["duels"] += 1
        if right in stats:
            stats[right]["duels"] += 1

        # Count wins
        if winner in stats:
            stats[winner]["wins"] += 1

        # Count championships (round == '결승')
        if round_name == "결승" and winner in stats:
            stats[winner]["championships"] += 1

    # Format table data
    table_rows = []
    for menu in CANDIDATES:
        duels = stats[menu]["duels"]
        wins = stats[menu]["wins"]
        championships = stats[menu]["championships"]

        if duels > 0:
            win_rate_val = (wins / duels) * 100
            win_rate_str = f"{win_rate_val:.1f}%"
        else:
            win_rate_val = -1.0
            win_rate_str = "아직 알 수 없음"

        table_rows.append(
            {
                "반찬": menu,
                "대결 수": duels,
                "승리 수": wins,
                "승률 (%)": win_rate_str,
                "우승 횟수": championships,
                "win_rate_val": win_rate_val,
            }
        )

    df = pd.DataFrame(table_rows)

    # Sort table by win rate descending, then duels, then wins
    df_sorted = df.sort_values(
        by=["win_rate_val", "대결 수", "승리 수"], ascending=[False, False, False]
    ).reset_index(drop=True)

    # Display Table
    st.subheader("📋 반찬별 승률 및 대결 요약")
    display_df = df_sorted[
        ["반찬", "대결 수", "승리 수", "승률 (%)", "우승 횟수"]
    ]
    st.dataframe(display_df, use_container_width=True)

    # Plotly Horizontal Bar Chart
    st.subheader("📈 반찬별 승률 비교")

    # Filter candidates with available win rate for chart
    chart_df = df_sorted[df_sorted["win_rate_val"] >= 0].copy()

    if not chart_df.empty:
        # Sort ascending for plotly horizontal bar chart (top displayed highest)
        chart_df = chart_df.sort_values(
            by="win_rate_val", ascending=True
        ).reset_index(drop=True)

        fig = px.bar(
            chart_df,
            x="win_rate_val",
            y="반찬",
            orientation="h",
            labels={"win_rate_val": "승률 (%)", "반찬": "반찬 이름"},
            text=chart_df["win_rate_val"].apply(lambda v: f"{v:.1f}%"),
            title="반찬별 승률 (%)",
        )
        fig.update_traces(
            textposition="auto", marker_color="#FF4B4B", hovertemplate="%{y}: %{x:.1f}%"
        )
        fig.update_layout(xaxis_range=[0, 100], yaxis={"categoryorder": "value ascending"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("비교할 대결 기록이 부족하여 그래프를 표시하지 않습니다.")


# App Layout Header
st.title("🍱 급식 월드컵 🏆")
st.write("최애 급식 반찬을 골라주세요!")

# Error State
if st.session_state.get("db_error", False):
    st.error(
        "🚨 저장 결과를 확인하지 못했습니다. 대결 저장이 정상적으로 완료되었는지 확인이 필요합니다."
    )
    st.warning("재선택이 잠겼습니다. 다시 시작 버튼을 눌러 다시 시도해주세요.")
    if st.button("처음부터 다시 시작하기", type="primary"):
        init_game()
        st.rerun()

# Winner State
elif st.session_state.winner:
    st.balloons()
    st.header("🎉 우승 반찬 🎉")
    st.subheader(f"✨ {st.session_state.winner} ✨")
    st.write("축하합니다! 이번 월드컵의 최고의 반찬으로 선정되었습니다.")

    if st.button("다시 시작하기", type="primary"):
        init_game()
        st.rerun()

    # Show Analytics on Winner Screen
    render_analytics()

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
            f"👍 {left_menu} 선택",
            key=f"btn_left_{match_idx}",
            use_container_width=True,
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

    # Show Analytics below game on match screen
    render_analytics()
