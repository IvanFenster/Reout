# main.py
import os
from typing import List
from static import popular_cities
import streamlit as st
from streamlit_searchbox import st_searchbox

# ---------- THEME (dark-blue palette) ----------
st.markdown(
    """
    <style>
    :root {
        --primary-color: #1f6feb;          /* bright blue accents */
        --background-color: #001a3d;       /* dark blue page background */
        --secondary-background-color: #002451; /* cards / form background */
        --text-color: #e6eefc;             /* light blue-gray text */
        --font: "Inter", sans-serif;
    }

    /* Page base */
    html, body, [class*="css"]  {
        color: var(--text-color);
        background-color: var(--background-color);
        font-family: var(--font);
    }

    /* Headings */
    h1, h2, h3, h4 {
        color: var(--primary-color);
        margin-top: 0.3em;
        margin-bottom: 0.3em;
    }

    /* Buttons */
    .stButton>button {
        background: var(--primary-color);
        color: white;
        border: none;
    }

    /* Sliders */
    .stSlider > div[data-testid*="stTickBar"] {
        color: var(--text-color);
    }

    /* Form "cards" */
    section[data-testid="stForm"] {
        background: var(--secondary-background-color);
        border-radius: 8px;
        padding: 1.5rem;
        border: 1px solid rgba(31,111,235,0.15);
    }

    /* ── NEW: dark-blue dropdown menu ───────────────────────────── */
    /* The menu container that appears when the selectbox opens */
    div[data-baseweb="select"] div[role="listbox"] {
        background: var(--secondary-background-color) !important;
        color: var(--text-color);
    }
    /* Individual option items */
    div[data-baseweb="select"] [role="option"] {
        background: var(--secondary-background-color) !important;
        color: var(--text-color);
    }
    div[data-baseweb="select"] [role="option"]:hover {
        background: rgba(31,111,235,0.25) !important;  /* subtle hover highlight */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- BASIC SETUP ----------
st.set_page_config("Hangout Planner", layout="centered")
st.title("📍 Hangout Planner")

# Session state init
for k, v in [("members", []), ("city", None)]:
    st.session_state.setdefault(k, v)

# helper used by st_searchbox – keeps only matches that contain the query text
def city_suggestions(search_term: str):
    search_term = search_term.lower()
    return [c for c in popular_cities if search_term in c.lower()][:10]


st.subheader("🏙️  Hangout location")
typed_city = st_searchbox(                                             # ← NEW widget
    city_suggestions,
    key="city_sb",
    placeholder="Start typing a city…",
    label="City",
)

# typed_city is None until the user hits Enter or chooses a suggestion
st.session_state["city"] = typed_city.strip() if typed_city else ""

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


def openai_chat(prompt: str, model: str = "gpt-4o-mini") -> str:
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

    if st.form_submit_button("Add member ➕"):
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
                        model="gpt-4o-mini",
                    )
                    st.markdown(itinerary)
                except Exception as e:
                    st.error(f"OpenAI error:\n```\n{e}\n```")
else:
    st.info("Add at least one member to start planning.")
