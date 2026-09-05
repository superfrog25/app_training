"""Personalised gym and HYROX workout generator.

Run locally with: streamlit run app.py
"""
from __future__ import annotations

import random
import json
import io
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont


EXERCISES = {
    "HYROX": [
        ("Sled push", {"sled"}), ("Sled pull", {"sled"}),
        ("Wall balls", {"medicine ball"}), ("Sandbag lunges", {"sandbag"}),
        ("Farmer's carry", {"dumbbells", "kettlebells"}),
        ("Burpee broad jumps", set()), ("SkiErg", {"skierg"}),
        ("Row erg", {"rower"}), ("Box step-ups", {"box", "dumbbells"}),
        ("Dumbbell thrusters", {"dumbbells"}),
        ("Incline treadmill power walk", {"treadmill"}),
    ],
    "Leg strength": [
        ("Goblet squat", {"dumbbells", "kettlebells"}),
        ("Barbell back squat", {"barbell", "rack"}), ("Romanian deadlift", {"barbell", "dumbbells"}),
        ("Bulgarian split squat", {"dumbbells", "bench"}), ("Leg press", {"leg press"}),
        ("Walking lunges", set()), ("Hip thrust", {"barbell", "bench"}),
    ],
    "Push": [
        ("Push-ups", set()), ("Dumbbell bench press", {"dumbbells", "bench"}),
        ("Barbell bench press", {"barbell", "bench"}), ("Dumbbell overhead press", {"dumbbells"}),
        ("Cable chest fly", {"cable machine"}), ("Dips", {"dip station"}),
    ],
    "Pull": [
        ("Pull-ups", {"pull-up bar"}), ("Lat pulldown", {"cable machine"}),
        ("Seated cable row", {"cable machine"}), ("Single-arm dumbbell row", {"dumbbells", "bench"}),
        ("Inverted row", {"pull-up bar"}), ("Face pulls", {"cable machine"}),
    ],
    "Engine": [
        ("Assault bike", {"bike"}), ("Jump rope", {"jump rope"}), ("Kettlebell swings", {"kettlebells"}),
        ("Battle ropes", {"battle ropes"}), ("Burpees", set()), ("Box jumps", {"box"}),
        ("Treadmill intervals", {"treadmill"}),
    ],
    "Core": [
        ("Plank", set()), ("Dead bug", set()), ("Pallof press", {"cable machine"}),
        ("Hanging knee raise", {"pull-up bar"}), ("Russian twists", {"medicine ball"}),
        ("Ab-wheel rollout", {"ab wheel"}),
    ],
}

EQUIPMENT = sorted({item for items in EXERCISES.values() for _, tools in items for item in tools})
HOLD_WORDS = ("plank", "hang")
DISTANCE_WORDS = ("sled", "carry", "lunges")
ERG_WORDS = ("ski", "row")
LIBRARY_FILE = Path(__file__).with_name("workout_library.json")


@dataclass
class Workout:
    title: str
    summary: str
    sections: list[tuple[str, list[str]]]


def available_moves(groups: list[str], equipment: set[str]) -> list[tuple[str, str]]:
    moves = []
    for group in groups:
        for move, required in EXERCISES[group]:
            if required.issubset(equipment):
                moves.append((group, move))
    return moves


def choose_moves(pool: list[tuple[str, str]], count: int, rng: random.Random) -> list[tuple[str, str]]:
    if not pool:
        return []
    if len(pool) >= count:
        return rng.sample(pool, count)
    return [rng.choice(pool) for _ in range(count)]


def target_for(move: str, level: str, reps: int) -> str:
    lower = move.lower()
    adjustment = {"Beginner": -3, "Intermediate": 0, "Advanced": 3}[level]
    if any(word in lower for word in HOLD_WORDS):
        return "30–45 sec hold" if level == "Beginner" else "45–60 sec hold"
    if any(word in lower for word in DISTANCE_WORDS):
        return "30–50 m" if level == "Beginner" else "50–100 m"
    if any(word in lower for word in ERG_WORDS):
        return "400 m" if level == "Beginner" else "500 m"
    return f"{max(6, reps + adjustment)} reps"


def generate(style: str, minutes: int, level: str, groups: list[str], equipment: set[str],
             interval: str, reps: int, run_distance: float, sim_rounds: int, seed: int) -> Workout | None:
    pool = available_moves(groups, equipment)
    if not pool:
        return None
    rng = random.Random(seed)
    if style == "Circuit":
        # The selected duration is for the working circuit only. Warm-up and
        # cool-down are deliberately additional time, not deducted from it.
        rounds = max(2, minutes // 6)
        sections = [("Warm-up", ["5–8 min easy cardio + dynamic mobility"])]
        sections.append((f"Main circuit — {rounds} rounds", [
            f"{group}: {move} — {interval if interval else target_for(move, level, reps)}"
            for group, move in choose_moves(pool, 4, rng)
        ] + ["Rest 60–90 sec after each round."]))
        sections.append(("Cool-down", ["5 min easy walk or bike, then light mobility."]))
        return Workout(
            "Personalised gym circuit",
            f"{minutes} min main circuit · + 10–13 min warm-up/cool-down · {level}",
            sections,
        )
    if style == "EMOM":
        blocks = max(2, minutes // 10)
        lines = []
        for i, (group, move) in enumerate(choose_moves(pool, blocks, rng), 1):
            lines.append(f"Minutes {(i - 1) * 10 + 1}–{i * 10}: {group} — {move}; 30 sec work / 30 sec rest.")
        return Workout("EMOM workout", f"{minutes} min · {level} · 30s work / 30s rest", [("Schedule", lines), ("Cool-down", ["5 min easy movement and mobility."])])
    lines = []
    for i, (group, move) in enumerate(choose_moves(pool, sim_rounds, rng), 1):
        lines.append(f"Block {i}: Run {run_distance:.1f} km, then {group}: {move} — {target_for(move, level, reps)}.")
    return Workout("HYROX-style simulation", f"{sim_rounds} blocks · {sim_rounds * run_distance:.1f} km total running · {level}", [("Race-style blocks", lines), ("Pacing", ["Keep the first half controlled; aim to finish the final block strong."])])


def as_markdown(workout: Workout) -> str:
    text = f"# {workout.title}\n\n{workout.summary}\n"
    for heading, lines in workout.sections:
        text += f"\n## {heading}\n" + "\n".join(f"- {line}" for line in lines) + "\n"
    return text


def export_lines(workout: Workout) -> list[tuple[str, str]]:
    """Return simple styled lines used by the PDF and JPG workout card."""
    lines = [(workout.title, "title"), (workout.summary, "summary")]
    for heading, items in workout.sections:
        lines.append((heading, "heading"))
        lines.extend((f"- {item}", "body") for item in items)
    return lines


def make_workout_image(workout: Workout) -> Image.Image:
    """Create a high-resolution, printable workout card without external services."""
    width, margin = 1600, 100
    fonts = {
        "title": ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 64),
        "summary": ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 34),
        "heading": ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 42),
        "body": ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 34),
    }
    wrapped_lines: list[tuple[str, str]] = []
    wrap_widths = {"title": 35, "summary": 68, "heading": 52, "body": 72}
    for content, style in export_lines(workout):
        safe_content = content.replace("–", "-").replace("—", "-").replace("“", '"').replace("”", '"')
        wrapped_lines.extend((line, style) for line in textwrap.wrap(safe_content, width=wrap_widths[style]) or [""])

    row_heights = {"title": 88, "summary": 58, "heading": 74, "body": 52}
    height = 150 + sum(row_heights[style] for _, style in wrapped_lines) + 80
    image = Image.new("RGB", (width, height), "#fcfcfa")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((45, 35, width - 45, height - 35), radius=30, fill="#ffffff", outline="#dbe4dd", width=3)
    y = 95
    colors = {"title": "#1f6b45", "summary": "#5f6b63", "heading": "#1d4f91", "body": "#202522"}
    for content, style in wrapped_lines:
        if style == "heading":
            y += 18
        draw.text((margin, y), content, fill=colors[style], font=fonts[style])
        y += row_heights[style]
    return image


def workout_jpg(workout: Workout) -> bytes:
    buffer = io.BytesIO()
    make_workout_image(workout).save(buffer, format="JPEG", quality=95, optimize=True)
    return buffer.getvalue()


def workout_pdf(workout: Workout) -> bytes:
    buffer = io.BytesIO()
    make_workout_image(workout).save(buffer, format="PDF", resolution=144.0)
    return buffer.getvalue()


def load_library() -> dict[str, dict]:
    """Read saved workouts, returning an empty library if it is new or invalid."""
    if not LIBRARY_FILE.exists():
        return {}
    try:
        saved = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
        return saved if isinstance(saved, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_to_library(name: str, workout: Workout) -> None:
    library = load_library()
    library[name] = {
        "title": workout.title,
        "summary": workout.summary,
        "sections": workout.sections,
        "saved_at": datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    LIBRARY_FILE.write_text(json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")


def show_workout(title: str, summary: str, sections: list) -> None:
    st.subheader(title)
    st.caption(summary)
    for heading, lines in sections:
        with st.container(border=True):
            st.markdown(f"### {heading}")
            for line in lines:
                st.markdown(f"- {line}")


st.set_page_config(page_title="Gym Session Generator", page_icon="🏋️", layout="wide")
st.title("🏋️ Personalised Gym Session Generator")
st.caption("Build a gym, conditioning, or HYROX-inspired session around your time, ability, focus, and equipment.")

with st.sidebar:
    st.header("Your settings")
    name = st.text_input("Name (optional)")
    style = st.selectbox("Workout format", ["Circuit", "EMOM", "HYROX simulation"])
    level = st.select_slider("Training level", options=["Beginner", "Intermediate", "Advanced"], value="Intermediate")
    groups = st.multiselect("Focus areas", list(EXERCISES), default=["HYROX", "Leg strength", "Engine"])
    equipment = st.multiselect("Equipment you have", EQUIPMENT, default=EQUIPMENT)
    st.divider()
    minutes = st.slider(
        "Main work length (minutes)", 20, 90, 40, 5,
        help="This is the main circuit or EMOM time. Warm-up and cool-down are extra time.",
    )
    if style == "Circuit":
        target_mode = st.radio("Station target", ["Timed", "Repetitions"], horizontal=True)
        interval = st.selectbox("Work / rest", ["40 sec work / 20 sec rest", "30 sec work / 30 sec rest", "50 sec work / 10 sec rest"]) if target_mode == "Timed" else ""
        reps = st.slider("Repetitions per station", 8, 25, 12) if target_mode == "Repetitions" else 12
        run_distance, sim_rounds = 1.0, 3
    elif style == "HYROX simulation":
        run_distance = st.slider("Run per block (km)", 0.25, 1.0, 1.0, 0.25)
        sim_rounds = st.slider("Simulation blocks", 1, 8, 4)
        interval, reps = "", 15
    else:
        interval, reps, run_distance, sim_rounds = "", 12, 1.0, 3
    generate_clicked = st.button("Generate a new session", type="primary", use_container_width=True)

if "seed" not in st.session_state:
    st.session_state.seed = random.randrange(1_000_000)
if generate_clicked:
    st.session_state.seed = random.randrange(1_000_000)

workout_tab, library_tab = st.tabs(["Generate workout", "Library"])

with workout_tab:
    if not groups:
        st.info("Choose at least one focus area in the sidebar to generate a session.")
    else:
        workout = generate(style, minutes, level, groups, set(equipment), interval, reps, run_distance, sim_rounds, st.session_state.seed)
        if workout is None:
            st.warning("None of the selected focus areas has a move that matches your equipment. Add equipment or choose another focus area.")
        else:
            if name:
                st.subheader(f"{name}'s session")
            show_workout(workout.title, workout.summary, workout.sections)
            save_name = st.text_input("Training name", placeholder="e.g. Saturday HYROX prep")
            if st.button("Save in Library", type="secondary"):
                cleaned_name = save_name.strip()
                if not cleaned_name:
                    st.warning("Please give this training a name before saving it.")
                else:
                    save_to_library(cleaned_name, workout)
                    st.success(f"Saved “{cleaned_name}” in your Library.")
            st.download_button("Download workout (.md)", as_markdown(workout), file_name="my_gym_session.md", mime="text/markdown")
            export_pdf, export_jpg = st.columns(2)
            with export_pdf:
                st.download_button("Download workout (PDF)", workout_pdf(workout), file_name="my_gym_session.pdf", mime="application/pdf")
            with export_jpg:
                st.download_button("Download workout (JPG)", workout_jpg(workout), file_name="my_gym_session.jpg", mime="image/jpeg")
            st.info("Training note: choose loads that leave 1–3 quality reps in reserve, and stop for pain (not normal effort).")

with library_tab:
    library = load_library()
    st.subheader("Your saved trainings")
    if not library:
        st.info("Your Library is empty. Generate a workout, give it a name, then choose “Save in Library.”")
    else:
        selected_name = st.selectbox("Open a saved training", list(library.keys()))
        saved_workout = library[selected_name]
        st.caption(f"Saved {saved_workout.get('saved_at', 'previously')}")
        show_workout(
            saved_workout["title"],
            saved_workout["summary"],
            saved_workout["sections"],
        )
        saved_as_workout = Workout(
            saved_workout["title"], saved_workout["summary"], saved_workout["sections"]
        )
        st.download_button(
            "Download saved workout (.md)",
            as_markdown(saved_as_workout),
            file_name=f"{selected_name.replace(' ', '_').lower()}.md",
            mime="text/markdown",
            key=f"download-{selected_name}",
        )
        export_pdf, export_jpg = st.columns(2)
        with export_pdf:
            st.download_button(
                "Download saved workout (PDF)", workout_pdf(saved_as_workout),
                file_name=f"{selected_name.replace(' ', '_').lower()}.pdf", mime="application/pdf",
                key=f"pdf-{selected_name}",
            )
        with export_jpg:
            st.download_button(
                "Download saved workout (JPG)", workout_jpg(saved_as_workout),
                file_name=f"{selected_name.replace(' ', '_').lower()}.jpg", mime="image/jpeg",
                key=f"jpg-{selected_name}",
            )
