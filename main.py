# main.py
import os
from typing import List
from static import popular_cities
import streamlit as st
import datetime as dt
import gspread #okay

st.markdown(
    """
    <style>
    /* menu panel (old selector) */
    div[data-baseweb="select"] div[role="listbox"],
    /* menu panel (new selector) */
    div[data-baseweb="menu"]
    {   /* entire drop-down background + border */
        background: #13244f !important;          /* dark navy */
        border: 1px solid #4361ee !important;    /* blue outline */
    }

    /* option row (old) */
    div[data-baseweb="select"] [role="option"],
    /* option row (new) */
    div[data-baseweb="menu"] div[role="option"]
    {
        background: #13244f !important;
        color: #f1faee !important;               /* light text */
        padding: 0.55rem 0.75rem !important;
    }

    /* hover / focus */
    div[data-baseweb="select"] [role="option"]:hover,
    div[data-baseweb="menu"] div[role="option"]:hover,
    div[data-baseweb="select"] [role="option"][aria-selected="true"],
    div[data-baseweb="menu"] div[role="option"][aria-selected="true"]
    {
        background: #274b8d !important;          /* bright blue highlight */
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# ---------- BASIC SETUP ----------
st.set_page_config("Reout", layout="centered")
st.title("Reout")

st.markdown(
    "Tell us your city, add each friend’s preferences, then hit **Generate** for an AI-crafted itinerary."
)

# Session state init
for k, v in [("members", []), ("city", None)]:
    st.session_state.setdefault(k, v)

# helper used by st_searchbox – keeps only matches that contain the query text
def city_suggestions(search_term: str):
    search_term = search_term.lower()
    return [c for c in popular_cities if search_term in c.lower()][:10]


st.subheader("🏙️  Hangout Location")
st.session_state["city"] = st.text_input(
    "City",                               # field label
    value="",                             # start empty
    placeholder="Type any city name…"     # grey hint text
).strip()                                 # store trimmed value

st.divider()

# ---------- HELPERS ----------
def add_member(data: dict) -> None:
    st.session_state["members"].append(data)




def build_prompt(members: List[dict], city: str) -> str:
    header = (
        f"You are an expert event planner. Draft a detailed step-by-step outing in **{city}**.\n\n"
        "You should consider all preferences of the Participants:"
    )
    people = [
        f"- {m['name']}: budget ${m['budget']}, "
        f"days {', '.join(m['days']) or 'any'}, "
        f"times {', '.join(m['times']) or 'any'}, "
        f"activity {m['activity']}, setting {m['setting']}, "
        f"interests {', '.join(m['interests']) or 'general'}, "
        f"cuisines {', '.join(m['cuisines']) or 'any'}, "
        f"dietary {', '.join(m['dietary']) or 'none'}, transport {m['transport']}."
        for m in members
    ]
    footer = (
        "\nReturn step-by-step plan with 2–5 places to go. At the beginning, suggest when the "
        "hangout should be and how long it should take. For each place give address, estimated "
        "time, one-sentence description, and cost estimate. Ensure all venues are real and form "
        "a coherent plan for the group."
    )
    return "\n".join([header, *people, footer])


def openai_chat(prompt: str, model: str = "gpt-4o-mini-search-preview") -> str:
    """Works with openai-python ≥1.0 and <1.0."""
    try:
        from openai import OpenAI  # new SDK
        client = OpenAI()
        rsp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Generate the plan."},
            ],
        )
        return rsp.choices[0].message.content
    except Exception as e:
        if "APIRemovedInV1" in str(e):
            import openai  # old SDK fallback
            rsp = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Generate the plan."},
                ],
            )
            return rsp.choices[0].message["content"]
        raise

@st.cache_data(show_spinner=False)
def available_models() -> list[str]:
    """Return the list of model IDs your key can use."""
    try:
        from openai import OpenAI
        client = OpenAI()
        return [m.id for m in client.models.list().data]
    except Exception:
        import openai
        return [m["id"] for m in openai.Model.list()["data"]]


def _sheet_client():
    sa = gspread.service_account_from_dict(st.secrets["gcp"])
    return sa.open_by_key(st.secrets["SPREADSHEET_KEY"]).sheet1

# ---------- MEMBER FORM ----------
with st.form("member_form", clear_on_submit=True):
    st.subheader("👤 Add participant")
    name = st.text_input("Name")

    col1, col2 = st.columns(2)
    with col1:
        budget = st.slider("Budget ($)", 0, 200, 30, 5)
    with col2:
        transport = st.selectbox(
            "Transportation", ["Walking", "Subway", "Taxi/Ride-share", "Bike", "Car"]
        )

    st.markdown("### 🗓️  Availability")
    days = st.multiselect("Days of the week", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    times = st.multiselect("Time of day", ["Morning", "Afternoon", "Evening", "Late night"])

    st.markdown("### 🎯 Activities")
    interests = st.multiselect(
        "Interests",
        ["Food", "Museums", "Parks", "Night-life", "Shopping", "Art", "Music",
         "Sports", "Escape rooms", "Movies", "Hiking", "Boating", "Photography"]
    )
    activity = st.select_slider(
        "How much activity?",
        options=["Very relaxed", "Relaxed", "Moderate", "Active", "Very active"],
        value="Moderate",
    )
    setting = st.radio("Preferred setting", ["Indoors", "Outdoors", "Both"], horizontal=True)

    st.markdown("### 🍽️  Dining preferences")
    cuisines = st.multiselect(
        "Preferred cuisines",
        ["Mediterranean", "Italian", "Asian", "American", "Mexican", "Indian", "Thai",
         "Chinese", "French", "Greek", "Japanese", "Korean", "Middle Eastern", "Vegan"]
    )
    dietary = st.multiselect(
        "Dietary restrictions", ["Vegetarian", "Vegan", "Gluten-free", "Halal", "Kosher"]
    )


    # ── CENTERED BUTTON ──
    col_l, col_c, col_r = st.columns([1, 2, 1])  # 1-2-1 grid
    with col_c:
        submitted = st.form_submit_button(
            "Add this member to hangout",
            type="primary",  # Streamlit gives it a blue background
            use_container_width=True  # make it full-width inside the middle column
        )

    if submitted:
        if not name:
            st.error("Name can’t be empty.")
        else:
            add_member(
                dict(
                    name=name, budget=budget, days=days, times=times, interests=interests,
                    cuisines=cuisines, dietary=dietary, transport=transport,
                    activity=activity, setting=setting,
                )
            )
            st.success(f"{name} added!")

# ---------- MEMBERS SUMMARY & PLAN ----------
if st.session_state["members"]:
    st.subheader("👥 Group so far")
    for m in st.session_state["members"]:
        st.markdown(
            f"- **{m['name']}** · ${m['budget']} · {m['activity']} · "
            f"{', '.join(m['cuisines']) or 'any cuisine'}"
        )

    st.markdown("---")
    if st.button("🚀 Generate outing plan", type="primary"):
        if not st.session_state["city"]:
            st.error("Choose or enter a city first 📍")
        else:
            with st.spinner("Generating your hangout plan …"):
                try:
                    itinerary = openai_chat(
                        build_prompt(st.session_state["members"], st.session_state["city"]),
                        model="gpt-4o-mini-search-preview",
                    )
                    st.markdown(itinerary)
                except Exception as e:
                    st.error(f"OpenAI error:\n```\n{e}\n```")
else:
    st.info("Add at least one member to start planning.")

# ----- show AI itinerary -----
st.markdown(itinerary)

# ──────────────────────────────────────────────────
# FEEDBACK & LIVE RATING UPDATE
# ──────────────────────────────────────────────────
st.divider()
st.subheader("📝 How useful was this plan?")

def _on_star_change():
    """Called whenever the star‐rating radio button changes."""
    ws = _sheet_client()
    city = st.session_state["city"]
    rating = st.session_state["feedback_rating"]
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    # If this is the first time rating:
    if "feedback_row" not in st.session_state:
        # Append a new row: [timestamp, city, rating, ""]
        ws.append_row([now, city, rating, ""], value_input_option="USER_ENTERED")
        # Figure out what row we just added:
        row_idx = len(ws.get_all_values())
        st.session_state["feedback_row"] = row_idx
    else:
        # Update the existing row's 3rd column (rating)
        row_idx = st.session_state["feedback_row"]
        ws.update_cell(row_idx, 3, rating)

# 1) Radio with on_change callback
rating = st.radio(
    "Rate the itinerary",
    [1, 2, 3, 4, 5],
    format_func=lambda i: "⭐" * i,
    horizontal=True,
    key="feedback_rating",
    on_change=_on_star_change,
)

# 2) Free-text comment box
comment = st.text_area(
    "Comments (optional)",
    placeholder="What did you like? What could be better?",
    key="feedback_comment",
    height=120,
)

# 3) Button to submit the comment
if st.button("Submit comment"):
    if "feedback_row" not in st.session_state:
        st.warning("Please pick a star rating first.")
    else:
        ws = _sheet_client()
        row_idx = st.session_state["feedback_row"]
        user_note = st.session_state["feedback_comment"]
        ws.update_cell(row_idx, 4, user_note)
        st.success("Thanks for your feedback! 🙌")