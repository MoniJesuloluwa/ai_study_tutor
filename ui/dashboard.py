"""
Streamlit dashboard for the AI Study Tutor.
Run with: streamlit run ui/dashboard.py
"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import pandas as pd

from core.loader import NotesLoader
from core.knowledge_base import KnowledgeBase, MAX_CONTEXT_CHARS
from core.tutor import Tutor
from core.practice import PracticeSession
import core.progress as progress

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Study Tutor",
    page_icon="📚",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init_state():
    defaults = {
        "mode": None,
        "topic": "",
        "context": "",
        "notes_loaded": False,
        "notes_report": None,
        "broad_topic": False,
        # Explain / Practice
        "chat_history": [],        # [{role, content}]
        "chat_display": [],        # [{role, content}] for display
        "practice_session": None,
        "practice_opening": "",
        # Quiz
        "quiz_questions": [],
        "quiz_idx": 0,
        "quiz_answers": [],
        "quiz_evaluations": [],
        "quiz_scores": [],
        "quiz_done": False,
        # Flashcards
        "flashcards": [],
        "card_idx": 0,
        "card_flipped": False,
        "card_scores": [],
        # Mock exam
        "exam_questions": [],
        "exam_started_at": None,
        "exam_minutes": 30,
        "exam_results": None,
        # General
        "session_started": False,
        "tutor": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


def get_tutor() -> Tutor:
    if st.session_state.tutor is None:
        st.session_state.tutor = Tutor()
    return st.session_state.tutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def parse_uploads(files: tuple):
    return NotesLoader().load_notes_from_uploads(files)


def uploads_as_tuple(uploads) -> tuple:
    return tuple((f.name, f.getvalue()) for f in uploads)


def load_notes(folder: str, topic: str, uploads=None):
    """Returns (context, report). A blank topic means use everything loaded."""
    unreadable = []
    if uploads:
        notes, unreadable = parse_uploads(uploads_as_tuple(uploads))
    else:
        try:
            notes = NotesLoader().load_notes_from_folder(folder)
        except FileNotFoundError:
            notes = []
    report = {"read": [n["name"] for n in notes], "unreadable": unreadable, "truncated": False}
    if not notes:
        return "", report

    ctx = ""
    if topic.strip():
        kb = KnowledgeBase()
        kb.load_notes(notes)
        ctx = kb.build_context_for_topic(topic)
    if not ctx.strip():
        ctx = "\n\n".join(f"From {n['name']}:\n{n['content'].strip()}" for n in notes)[:MAX_CONTEXT_CHARS]
    report["truncated"] = len(ctx) >= MAX_CONTEXT_CHARS
    return ctx, report


def topic_label(topic: str, report: dict) -> str:
    if topic.strip():
        return topic.strip()
    label = ", ".join(Path(name).stem for name in report["read"]) or "My notes"
    return label if len(label) <= 60 else label[:57] + "..."


def reset_session():
    keys = [
        "chat_history", "chat_display", "practice_session", "practice_opening",
        "quiz_questions", "quiz_idx", "quiz_answers", "quiz_evaluations",
        "quiz_scores", "quiz_done", "flashcards", "card_idx", "card_flipped",
        "card_scores", "session_started",
        "exam_questions", "exam_started_at", "exam_results",
    ]
    for k in keys:
        del st.session_state[k]
    _init_state()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📚 AI Study Tutor")
    st.divider()

    api_key_missing = not os.getenv("ANTHROPIC_API_KEY")
    if api_key_missing:
        st.error(
            "Anthropic API key not found. Create a file named `.env` in the project "
            "folder containing `ANTHROPIC_API_KEY=your-key`, then restart the app."
        )

    uploaded_files = st.file_uploader(
        "Upload your notes",
        type=["pdf", "pptx", "txt", "md"],
        accept_multiple_files=True,
        help="PDF, PowerPoint (.pptx), text, or Markdown files.",
        key="notes_upload",
    )
    if uploaded_files:
        _read, _unreadable = parse_uploads(uploads_as_tuple(uploaded_files))
        if _read:
            st.success(f"{len(_read)} file{'s' if len(_read) != 1 else ''} read")
        if _unreadable:
            st.warning(
                "Couldn't read any text from: " + ", ".join(_unreadable)
                + ". They may be scanned, image-only, or empty."
            )
    with st.expander("Or use a notes folder"):
        notes_folder = st.text_input(
            "Notes folder", value="data/notes", key="notes_folder_input",
            help="Used only when no files are uploaded.",
        )
    topic = st.text_input("Topic to study", placeholder="Leave blank to study everything uploaded", key="topic_input")

    mode = st.radio(
        "Mode",
        ["Explain", "Quiz", "Practice", "Flashcards", "Mock Exam"],
        key="mode_radio",
    )

    num_questions = st.slider("Number of questions / cards", 3, 10, 5)
    exam_minutes = 30
    if mode == "Mock Exam":
        exam_minutes = st.number_input(
            "Time limit (minutes)", min_value=5, max_value=180, value=30, step=5,
            help="A soft limit: the clock runs, but you can still submit when it hits zero.",
        )

    folder_has_files = (not uploaded_files) and Path(notes_folder).expanduser().is_dir() and any(
        p.suffix.lower() in NotesLoader.SUPPORTED_EXTENSIONS
        for p in Path(notes_folder).expanduser().rglob("*")
    )
    can_start = bool(topic.strip()) or bool(uploaded_files) or folder_has_files
    start_btn = st.button(
        "▶ Start Session", type="primary", use_container_width=True,
        disabled=api_key_missing or not can_start,
    )

    if start_btn:
        reset_session()
        with st.spinner("Loading notes..."):
            ctx, report = load_notes(notes_folder, topic, uploaded_files)
        st.session_state.topic = topic_label(topic, report)
        st.session_state.broad_topic = not topic.strip()
        st.session_state.notes_report = report
        st.session_state.context = ctx
        st.session_state.mode = mode
        st.session_state.exam_minutes = int(exam_minutes)
        st.session_state.notes_loaded = True
        st.session_state.session_started = True
        st.rerun()

    if not can_start:
        st.caption("Enter a topic, upload notes, or point to a notes folder.")

    st.divider()
    if st.button("🔄 Reset", use_container_width=True):
        reset_session()
        st.rerun()


# ---------------------------------------------------------------------------
# Main area — tabs
# ---------------------------------------------------------------------------

tab_study, tab_progress = st.tabs(["📖 Study", "📊 Progress"])

# ===========================================================================
# PROGRESS TAB
# ===========================================================================

with tab_progress:
    st.header("Your Progress")

    sessions = progress.get_all_sessions()
    topic_summary = progress.get_topic_summary()

    if not sessions:
        st.info("No sessions recorded yet. Complete a study session to see your progress.")
    else:
        # KPI row
        col1, col2, col3 = st.columns(3)
        quiz_sessions = [s for s in sessions if s.get("score") is not None]
        avg_pct = (
            sum(s["pct"] for s in quiz_sessions) / len(quiz_sessions)
            if quiz_sessions else 0
        )
        col1.metric("Total Sessions", len(sessions))
        col2.metric("Topics Studied", len(topic_summary))
        col3.metric("Avg Quiz Score", f"{avg_pct:.0f}%" if quiz_sessions else "—")

        st.divider()

        # Quiz score trend
        if quiz_sessions:
            st.subheader("Quiz Score History")
            df = pd.DataFrame(quiz_sessions)
            df["date"] = pd.to_datetime(df["date"])
            fig = px.line(
                df, x="date", y="pct", color="topic",
                markers=True, labels={"pct": "Score (%)", "date": "Date"},
                template="plotly_white",
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Topic breakdown
        st.subheader("Topics")
        for t, info in topic_summary.items():
            with st.expander(f"**{t}** — {info['sessions']} session(s)"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Sessions", info["sessions"])
                c2.metric("Last studied", info.get("last_studied", "—"))
                scores = info.get("quiz_scores", [])
                c3.metric("Avg quiz", f"{sum(scores)/len(scores):.0f}%" if scores else "—")
                if info.get("modes_used"):
                    st.caption("Modes used: " + ", ".join(info["modes_used"]))

        # Recent activity
        st.subheader("Recent Sessions")
        recent = progress.get_recent_sessions(10)
        for s in reversed(recent):
            score_str = f"  •  {s['score']}/{s['total']} ({s['pct']}%)" if s.get("score") is not None else ""
            st.caption(f"**{s['topic']}** — {s['mode']}{score_str}  —  {s['date'][:10]}")


# ===========================================================================
# STUDY TAB
# ===========================================================================

with tab_study:
    if not st.session_state.session_started:
        st.info("👈 Upload your notes, add a topic if you like, then click **Start Session**.")
        st.stop()

    topic = st.session_state.topic
    context = st.session_state.context
    mode = st.session_state.mode

    st.header(f"{mode}: {topic}")
    report = st.session_state.notes_report
    if report and report["read"]:
        st.caption("Using: " + ", ".join(report["read"]))
    if report and report["unreadable"]:
        st.warning("Couldn't read any text from: " + ", ".join(report["unreadable"]))
    if report and report["truncated"]:
        st.info(
            "Your notes are longer than the tutor can read at once, so some text was left out. "
            "Try uploading fewer files or entering a more specific topic."
        )
    if not context.strip():
        st.warning("No readable notes found. The tutor will use general knowledge.")

    # -----------------------------------------------------------------------
    # EXPLAIN MODE
    # -----------------------------------------------------------------------
    if mode == "Explain":
        st.caption("The tutor will explain the topic and ask checking questions. Respond to deepen your understanding.")

        # Display existing chat
        for msg in st.session_state.chat_display:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # First message — auto-generate explanation
        if not st.session_state.chat_history:
            if st.session_state.broad_topic:
                first_text = (
                    "These are all my notes for the course. Don't explain everything at once. "
                    "Give me a short roadmap of the themes in teaching order, naming the files for each, "
                    "then teach only the first theme and end with a checking question."
                )
            else:
                first_text = f"Topic: {topic}"
            first_user = {"role": "user", "content": first_text}
            st.session_state.chat_history = [first_user]

            with st.chat_message("assistant"):
                response_text = st.write_stream(
                    get_tutor().explain_stream(topic, context, st.session_state.chat_history)
                )

            st.session_state.chat_display.append({"role": "assistant", "content": response_text})
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
            progress.record_session(topic, "explain")

        # Chat input
        if user_input := st.chat_input("Respond to the tutor's question, or ask for clarification..."):
            with st.chat_message("user"):
                st.markdown(user_input)

            st.session_state.chat_display.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.chat_message("assistant"):
                response_text = st.write_stream(
                    get_tutor().explain_stream(topic, context, st.session_state.chat_history)
                )

            st.session_state.chat_display.append({"role": "assistant", "content": response_text})
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
            st.rerun()

    # -----------------------------------------------------------------------
    # PRACTICE MODE
    # -----------------------------------------------------------------------
    elif mode == "Practice":
        st.caption("The tutor will guide you through the topic using the Socratic method — expect questions, not lectures!")

        for msg in st.session_state.chat_display:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Start practice session
        if not st.session_state.practice_session:
            session = PracticeSession(topic, context)
            st.session_state.practice_session = session

            with st.chat_message("assistant"):
                opening = st.write_stream(session.start_stream())

            st.session_state.practice_opening = opening
            st.session_state.chat_display.append({"role": "assistant", "content": opening})
            progress.record_session(topic, "practice")

        # Chat input
        if user_input := st.chat_input("Your response..."):
            with st.chat_message("user"):
                st.markdown(user_input)

            st.session_state.chat_display.append({"role": "user", "content": user_input})
            session = st.session_state.practice_session

            with st.chat_message("assistant"):
                response_text = st.write_stream(
                    session.reply_stream(st.session_state.practice_opening, user_input)
                )

            # After first reply the opening is now irrelevant (history is in session)
            st.session_state.practice_opening = ""
            st.session_state.chat_display.append({"role": "assistant", "content": response_text})
            st.rerun()

    # -----------------------------------------------------------------------
    # QUIZ MODE
    # -----------------------------------------------------------------------
    elif mode == "Quiz":
        tutor = get_tutor()

        # Generate questions on first load
        if not st.session_state.quiz_questions and not st.session_state.quiz_done:
            with st.spinner(f"Generating {num_questions} quiz questions..."):
                questions = tutor.generate_quiz_questions(topic, context, num_questions)
            st.session_state.quiz_questions = questions
            st.rerun()

        questions = st.session_state.quiz_questions
        idx = st.session_state.quiz_idx

        if st.session_state.quiz_done:
            # ---- Summary ----
            scores = st.session_state.quiz_scores
            total = len(scores)
            correct = sum(1 for s in scores if s == 2)
            partial = sum(1 for s in scores if s == 1)
            wrong = sum(1 for s in scores if s == 0)
            weighted = correct * 2 + partial
            max_score = total * 2
            pct = round(weighted / max_score * 100) if max_score else 0

            st.subheader("Quiz Complete!")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Score", f"{pct}%")
            c2.metric("Correct", correct)
            c3.metric("Partial", partial)
            c4.metric("Incorrect", wrong)

            if pct >= 80:
                st.success("Excellent work! You have a strong grasp of this topic.")
            elif pct >= 50:
                st.warning("Good effort. Review the questions you missed and try again.")
            else:
                st.error("Keep studying! Use Explain or Practice mode to strengthen your understanding.")

            # Show all Q&A
            st.divider()
            st.subheader("Review")
            for i, (q, ans, ev, sc) in enumerate(zip(
                questions,
                st.session_state.quiz_answers,
                st.session_state.quiz_evaluations,
                scores,
            )):
                icon = "✅" if sc == 2 else ("⚠️" if sc == 1 else "❌")
                with st.expander(f"{icon} Q{i+1}: {q[:80]}..."):
                    st.markdown(f"**Your answer:** {ans}")
                    st.markdown("---")
                    st.markdown(f"**Tutor feedback:**\n{ev}")

            if st.button("🔄 Retake Quiz"):
                keys = ["quiz_questions", "quiz_idx", "quiz_answers", "quiz_evaluations", "quiz_scores", "quiz_done"]
                for k in keys:
                    del st.session_state[k]
                _init_state()
                st.rerun()

        elif idx < len(questions):
            # ---- Active question ----
            progress_pct = idx / len(questions)
            st.progress(progress_pct, text=f"Question {idx + 1} of {len(questions)}")
            st.divider()

            st.subheader(f"Q{idx + 1}. {questions[idx]}")

            # Show previous evaluation if just submitted
            if len(st.session_state.quiz_evaluations) > idx:
                ev = st.session_state.quiz_evaluations[idx]
                sc = st.session_state.quiz_scores[idx]
                if sc == 2:
                    st.success(ev)
                elif sc == 1:
                    st.warning(ev)
                else:
                    st.error(ev)

                if idx + 1 < len(questions):
                    if st.button("Next Question →"):
                        st.session_state.quiz_idx += 1
                        st.rerun()
                else:
                    if st.button("See Results →"):
                        st.session_state.quiz_done = True
                        progress.record_session(
                            topic, "quiz",
                            score=sum(1 for s in st.session_state.quiz_scores if s >= 1),
                            total=len(questions),
                        )
                        st.rerun()
            else:
                # Awaiting answer
                with st.form(key=f"quiz_form_{idx}"):
                    answer = st.text_area(
                        "Your answer",
                        placeholder="Type your answer here...",
                        height=120,
                    )
                    submitted = st.form_submit_button("Submit Answer", type="primary")

                if submitted:
                    if not answer.strip():
                        st.warning("Please write an answer before submitting.")
                    else:
                        with st.spinner("Evaluating your answer..."):
                            result = tutor.evaluate_answer(topic, questions[idx], answer, context)

                        st.session_state.quiz_answers.append(answer)
                        st.session_state.quiz_evaluations.append(result["feedback"])
                        st.session_state.quiz_scores.append(result["score"])
                        st.rerun()

    # -----------------------------------------------------------------------
    # MOCK EXAM MODE
    # -----------------------------------------------------------------------
    elif mode == "Mock Exam":
        tutor = get_tutor()

        if not st.session_state.exam_questions:
            with st.spinner(f"Writing a {num_questions}-question exam from your notes..."):
                st.session_state.exam_questions = tutor.generate_exam_questions(context, num_questions)
            st.session_state.exam_started_at = time.time()
            st.rerun()

        exam_qs = st.session_state.exam_questions
        results = st.session_state.exam_results
        limit_s = st.session_state.exam_minutes * 60

        if results is None:
            # ---- Taking the exam ----
            started = st.session_state.exam_started_at

            @st.fragment(run_every=1)
            def exam_clock():
                remaining = limit_s - (time.time() - started)
                if remaining > 0:
                    m, sec = divmod(int(remaining), 60)
                    st.metric("Time remaining", f"{m:02d}:{sec:02d}")
                else:
                    st.error("Time is up. Finish your thought and submit; in the real exam you would stop here.")

            exam_clock()
            st.caption(
                f"{len(exam_qs)} questions, closed book. Write full answers as you would on paper. "
                "Answers are marked when you submit."
            )
            st.divider()

            for i, q in enumerate(exam_qs):
                st.markdown(f"**Q{i + 1}.** {q['question']}")
                st.caption(f"Topic area: {q['area']}")
                st.text_area(
                    "Your answer", key=f"exam_ans_{i}", height=140,
                    label_visibility="collapsed", placeholder="Write your answer here...",
                )

            if st.button("Submit exam", type="primary"):
                answers = [st.session_state.get(f"exam_ans_{i}", "") for i in range(len(exam_qs))]
                if not any(a.strip() for a in answers):
                    st.warning("Write at least one answer before submitting.")
                else:
                    elapsed = time.time() - started
                    try:
                        with st.spinner("Marking your exam..."):
                            graded = tutor.grade_exam(exam_qs, answers, context)
                    except Exception as exc:
                        st.error(f"Marking failed ({exc}). Your answers are still here, so try submitting again.")
                    else:
                        weighted = sum(g["score"] for g in graded)
                        progress.record_session(topic, "mock exam", score=weighted, total=2 * len(exam_qs))
                        st.session_state.exam_results = {
                            "answers": answers, "graded": graded, "elapsed": elapsed,
                        }
                        st.rerun()

        else:
            # ---- Results ----
            graded = results["graded"]
            n = len(exam_qs)
            weighted = sum(g["score"] for g in graded)
            pct = round(weighted / (2 * n) * 100) if n else 0
            full = sum(1 for g in graded if g["score"] == 2)
            elapsed = int(results["elapsed"])
            over = elapsed - limit_s

            st.subheader("Exam marked")
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{pct}%")
            c2.metric("Full marks", f"{full} of {n}")
            c3.metric(
                "Time used",
                f"{elapsed // 60}m {elapsed % 60:02d}s",
                delta=f"{over // 60}m over" if over > 0 else None,
                delta_color="inverse",
            )

            if pct >= 80:
                st.success("Strong result. Keep the weak areas below ticking over and you're in good shape.")
            elif pct >= 50:
                st.warning("A decent base. The weak areas below are where the marks are.")
            else:
                st.error("Plenty of room to improve. Work through the weak areas below, then retake.")

            st.divider()
            st.subheader("Where to focus")
            by_area = {}
            for q, g in zip(exam_qs, graded):
                by_area.setdefault(q["area"], []).append(g["score"])
            ranked = sorted(by_area.items(), key=lambda kv: sum(kv[1]) / (2 * len(kv[1])))
            for area, scores in ranked:
                area_pct = round(sum(scores) / (2 * len(scores)) * 100)
                st.progress(area_pct / 100, text=f"{area}: {area_pct}% ({len(scores)} question{'s' if len(scores) != 1 else ''})")

            st.divider()
            st.subheader("Review")
            for i, (q, ans, g) in enumerate(zip(exam_qs, results["answers"], graded)):
                icon = "✅" if g["score"] == 2 else ("⚠️" if g["score"] == 1 else "❌")
                with st.expander(f"{icon} Q{i + 1} ({q['area']}): {q['question'][:70]}..."):
                    st.markdown(f"**Question:** {q['question']}")
                    st.markdown(f"**Your answer:** {ans.strip() or '_(no answer)_'}")
                    st.markdown(f"**Marker's feedback:** {g['feedback']}")

            if st.button("🔄 New mock exam"):
                for k in ["exam_questions", "exam_started_at", "exam_results"]:
                    del st.session_state[k]
                _init_state()
                st.rerun()

    # -----------------------------------------------------------------------
    # FLASHCARDS MODE
    # -----------------------------------------------------------------------
    elif mode == "Flashcards":
        tutor = get_tutor()

        if not st.session_state.flashcards:
            with st.spinner(f"Generating {num_questions} flashcards..."):
                cards = tutor.generate_flashcards(topic, context, num_questions)
            st.session_state.flashcards = cards
            st.session_state.card_scores = [None] * len(cards)
            progress.record_session(topic, "flashcards")
            st.rerun()

        cards = st.session_state.flashcards
        idx = st.session_state.card_idx
        total = len(cards)

        # Summary when done
        all_scored = all(s is not None for s in st.session_state.card_scores)
        if idx >= total and all_scored:
            got = sum(1 for s in st.session_state.card_scores if s)
            st.subheader(f"Flashcards Complete! {got}/{total} correct")
            pct = round(got / total * 100) if total else 0
            st.progress(pct / 100, text=f"{pct}% accuracy")

            if pct >= 80:
                st.success("Great recall! You know this topic well.")
            else:
                st.info("Keep reviewing the cards you missed.")

            st.divider()
            for i, (card, scored) in enumerate(zip(cards, st.session_state.card_scores)):
                icon = "✅" if scored else "❌"
                with st.expander(f"{icon} Card {i+1}: {card['question'][:60]}..."):
                    st.markdown(f"**Q:** {card['question']}")
                    st.markdown(f"**A:** {card['answer']}")

            if st.button("🔄 Restart Cards"):
                st.session_state.card_idx = 0
                st.session_state.card_flipped = False
                st.session_state.card_scores = [None] * len(cards)
                st.rerun()

        elif idx < total:
            st.progress(idx / total, text=f"Card {idx + 1} of {total}")
            card = cards[idx]

            # Card display
            st.divider()
            st.subheader(f"Card {idx + 1}")

            with st.container(border=True):
                st.markdown(f"**Question:** {card['question']}")

                if st.session_state.card_flipped:
                    st.divider()
                    st.markdown(f"**Answer:** {card['answer']}")

                    c1, c2 = st.columns(2)
                    if c1.button("✅ Got it", use_container_width=True):
                        st.session_state.card_scores[idx] = True
                        st.session_state.card_idx += 1
                        st.session_state.card_flipped = False
                        st.rerun()
                    if c2.button("❌ Missed it", use_container_width=True):
                        st.session_state.card_scores[idx] = False
                        st.session_state.card_idx += 1
                        st.session_state.card_flipped = False
                        st.rerun()
                else:
                    if st.button("Flip Card 🔁", use_container_width=True):
                        st.session_state.card_flipped = True
                        st.rerun()
