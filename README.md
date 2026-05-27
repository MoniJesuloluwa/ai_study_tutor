# AI Study Tutor

A personal study assistant that teaches through dialogue — not just summaries. Load your notes, pick a topic, and study through explanation, quizzing, Socratic practice, or flashcards.

---

## What It Was

The original version used OpenAI's `gpt-4o-mini` and had three core problems:

- **It was a glorified summarizer.** The tutor would explain a topic by dumping information at the student with no follow-up, no checking questions, and no adaptation based on how the student responded.
- **Quiz mode didn't evaluate.** Questions were generated, but student answers were never actually assessed — there was no feedback, no scoring, no explanation of what was right or wrong.
- **Core features were unimplemented.** The Streamlit dashboard was an empty file. The practice mode was an empty file. Progress tracking existed as a module but nothing ever called it, so no sessions were ever recorded.

---

## What Changed

### Model & Integration
Replaced OpenAI with **Anthropic's Claude** (`claude-opus-4-7`) with adaptive thinking enabled for pedagogically complex tasks. Prompt caching is applied to system prompts and student notes, reducing API costs across multi-turn sessions.

### The Tutor Actually Teaches Now
Each mode was rebuilt around the **Socratic method**:

- **Explain** — after explaining a concept, the tutor always ends with a checking question. When the student responds, it evaluates their understanding, corrects misconceptions, and adapts the depth of the next explanation accordingly. Fully multi-turn.
- **Quiz** — questions test genuine understanding, not just recall. Each answer is evaluated by Claude and returned with a score (`correct / partial / incorrect`), specific feedback on what was right and wrong, and the correct understanding explained before moving on.
- **Practice** — a Socratic dialogue where the tutor guides the student to answers through probing questions rather than giving them directly. Hints are progressive and only given when the student is genuinely stuck.
- **Flashcards** — generated from notes, testing understanding over memorisation.

### Streamlit Dashboard
Built out from an empty file into a full interactive app:
- Sidebar for loading notes, selecting topic, mode, and number of questions/cards
- Chat interface for Explain and Practice modes with streaming responses
- One-question-at-a-time quiz flow with colour-coded feedback
- Flashcard flip interface with Got it / Missed it tracking
- Progress tab with quiz score trends (Plotly chart), per-topic summaries, and session history

### Progress Tracking
Sessions are now actually recorded to `data/progress.json` after every mode. Tracks session history, last studied date, modes used per topic, and quiz score trends over time.

### CLI
Updated to match the new API and made interactive throughout:
- Explain mode loops as a multi-turn conversation until the user types `quit`
- Quiz mode asks questions one at a time, collects answers, and shows evaluated feedback per question
- New `practice` command for Socratic dialogue in the terminal
- New `dashboard` command to launch the Streamlit app

---

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your Anthropic API key to .env
```

## Usage

```bash
# Streamlit dashboard
streamlit run ui/dashboard.py

# or via main.py
python main.py dashboard

# CLI
python main.py explain --topic "photosynthesis" --notes-folder data/notes
python main.py quiz --topic "photosynthesis" --num 5
python main.py practice --topic "photosynthesis"
python main.py flashcards --topic "photosynthesis" --num 10
```

## Notes Format

Place your study notes in `data/notes/` as `.txt`, `.md`, or `.pdf` files. The tutor uses them as the primary source and supplements with general knowledge only when needed.
