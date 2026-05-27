import os
from typing import List, Dict, Generator
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# System prompts — cached at the API level (stable content first)
# ---------------------------------------------------------------------------

_EXPLAIN_SYSTEM = """You are an expert tutor who uses the Socratic method. You never just dump information — you teach through structured explanation and dialogue.

When explaining a topic:
1. Start with a clear, organised explanation using the student's notes as the primary source. Structure it with headings or numbered steps where helpful. Use analogies and concrete examples.
2. After your explanation, always end with a checking question to test the student's understanding. Something like "Can you tell me in your own words what X means?" or "What do you think would happen if Y?"
3. When the student responds, evaluate their understanding — acknowledge what is correct, gently correct misconceptions, and deepen the explanation based on their gaps.
4. Adapt your language and depth to how the student is responding.

You have access to the student's personal study notes. Use them as the primary source. If you supplement with general knowledge, say so explicitly."""

_QUIZ_SYSTEM = """You are an expert tutor running a quiz. Your job is not just to test — it is to teach through assessment.

For each question:
- Ask clear, specific questions that test genuine understanding (not just recall)
- When evaluating an answer, be thorough: acknowledge what was right, explain what was wrong and why, and provide the correct understanding
- Give partial credit where deserved — a student who has the right idea but wrong detail is not the same as one who has no idea
- Use encouraging language. Mistakes are learning opportunities.
- If the student was wrong, always explain the concept before moving on so they actually learn from the error"""

_PRACTICE_SYSTEM = """You are a Socratic tutor running an interactive practice session. Your goal is to guide the student to answers through questioning — not to deliver answers directly.

How to run the session:
1. Begin by asking the student a thoughtful question about the topic (open-ended, not yes/no)
2. When they answer, probe deeper: "What do you mean by...?", "Can you give an example?", "Why does that happen?", "What would be the consequence of...?"
3. When their answer is incorrect, don't correct directly — ask a question that reveals the gap. Let them discover the error.
4. Only give hints when the student is genuinely stuck after multiple attempts. Give progressive hints (smallest hint first).
5. Only reveal a full answer after the student has genuinely engaged and still can't get there.
6. Celebrate correct reasoning explicitly. Build on their own words and examples.
7. Keep the dialogue moving — this is a conversation, not a lecture."""

_FLASHCARD_SYSTEM = """You are a study assistant generating concise, high-quality flashcards from student notes.

Create flashcards that:
- Test understanding, not just memorisation
- Are precise and unambiguous
- Have clear, complete answers (not one-word)
- Cover the most important concepts in the notes

Format each flashcard as:
Q: [question]
A: [answer]"""


class Tutor:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not found. Add it to your .env file.")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-opus-4-7"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _system_with_notes(self, system_text: str, context: str) -> list:
        """Build system prompt list with notes cached at the API level."""
        blocks = [
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if context.strip():
            blocks.append({
                "type": "text",
                "text": f"STUDENT NOTES:\n{context[:6000]}",
                "cache_control": {"type": "ephemeral"},
            })
        return blocks

    def _first_user_message(self, topic: str) -> str:
        return f"Topic: {topic}"

    # ------------------------------------------------------------------
    # Explain mode — multi-turn Socratic explanation
    # ------------------------------------------------------------------

    def explain_stream(
        self,
        topic: str,
        context: str,
        history: List[Dict],
    ) -> Generator[str, None, None]:
        """Streaming Socratic explanation. history is full message list."""
        system = self._system_with_notes(_EXPLAIN_SYSTEM, context)
        messages = history if history else [
            {"role": "user", "content": self._first_user_message(topic)}
        ]
        with self.client.messages.stream(
            model=self.model,
            max_tokens=1200,
            thinking={"type": "adaptive"},
            system=system,
            messages=messages,
        ) as stream:
            yield from stream.text_stream

    def explain(self, topic: str, context: str, history: List[Dict]) -> str:
        """Non-streaming version for CLI."""
        system = self._system_with_notes(_EXPLAIN_SYSTEM, context)
        messages = history if history else [
            {"role": "user", "content": self._first_user_message(topic)}
        ]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            thinking={"type": "adaptive"},
            system=system,
            messages=messages,
        )
        return next(b.text for b in response.content if b.type == "text")

    # ------------------------------------------------------------------
    # Quiz mode — generate questions and evaluate answers
    # ------------------------------------------------------------------

    def generate_quiz_questions(
        self, topic: str, context: str, num: int = 5
    ) -> List[str]:
        """Generate `num` quiz questions as a list of strings."""
        system = self._system_with_notes(_QUIZ_SYSTEM, context)
        prompt = (
            f"Generate exactly {num} quiz questions about '{topic}' based on the notes. "
            f"Number them 1 to {num}. Questions only — no answers. "
            "Mix question types: some conceptual ('explain why...'), some applied ('what would happen if...'), some definitional."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = next(b.text for b in response.content if b.type == "text")
        # Parse numbered lines
        questions = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                # Strip leading number and punctuation
                parts = line.split(".", 1)
                if len(parts) == 2:
                    questions.append(parts[1].strip())
                else:
                    questions.append(line)
        return questions[:num] if questions else [raw]

    def evaluate_answer(
        self,
        topic: str,
        question: str,
        student_answer: str,
        context: str,
    ) -> Dict:
        """
        Evaluate a student's quiz answer.
        Returns {"feedback": str, "score": int, "correct": bool}
        score is 0, 1, or 2 (0=wrong, 1=partial, 2=correct)
        """
        system = self._system_with_notes(_QUIZ_SYSTEM, context)
        prompt = (
            f"Topic: {topic}\n"
            f"Question: {question}\n"
            f"Student's answer: {student_answer}\n\n"
            "Evaluate this answer. Be a thoughtful teacher — acknowledge what is right, "
            "explain what is wrong and why, give the correct understanding clearly. "
            "End your response with exactly one of these tags on its own line: "
            "[CORRECT], [PARTIAL], or [INCORRECT]"
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = next(b.text for b in response.content if b.type == "text")

        # Parse score tag
        correct = False
        score = 0
        if "[CORRECT]" in text:
            score = 2
            correct = True
        elif "[PARTIAL]" in text:
            score = 1
        else:
            score = 0

        # Clean tag from feedback
        feedback = text.replace("[CORRECT]", "").replace("[PARTIAL]", "").replace("[INCORRECT]", "").strip()
        return {"feedback": feedback, "score": score, "correct": correct}

    # ------------------------------------------------------------------
    # Practice mode — Socratic dialogue
    # ------------------------------------------------------------------

    def practice_stream(
        self,
        topic: str,
        context: str,
        history: List[Dict],
    ) -> Generator[str, None, None]:
        """Streaming Socratic practice dialogue."""
        system = self._system_with_notes(_PRACTICE_SYSTEM, context)
        messages = history if history else [
            {"role": "user", "content": f"I want to practice the topic: {topic}. Please start the session."}
        ]
        with self.client.messages.stream(
            model=self.model,
            max_tokens=800,
            thinking={"type": "adaptive"},
            system=system,
            messages=messages,
        ) as stream:
            yield from stream.text_stream

    def practice(self, topic: str, context: str, history: List[Dict]) -> str:
        """Non-streaming practice turn for CLI."""
        system = self._system_with_notes(_PRACTICE_SYSTEM, context)
        messages = history if history else [
            {"role": "user", "content": f"I want to practice the topic: {topic}. Please start the session."}
        ]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            thinking={"type": "adaptive"},
            system=system,
            messages=messages,
        )
        return next(b.text for b in response.content if b.type == "text")

    # ------------------------------------------------------------------
    # Flashcards
    # ------------------------------------------------------------------

    def generate_flashcards(
        self, topic: str, context: str, num: int = 10
    ) -> List[Dict[str, str]]:
        """Generate Q/A flashcards. Returns list of {question, answer}."""
        system = self._system_with_notes(_FLASHCARD_SYSTEM, context)
        prompt = (
            f"Create {num} flashcards about '{topic}' from the notes. "
            "Each card must test a distinct concept. Format: Q: ... A: ..."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = next(b.text for b in response.content if b.type == "text")
        return self._parse_flashcards(raw)

    def _parse_flashcards(self, raw: str) -> List[Dict[str, str]]:
        cards = []
        current_q = None
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("Q:"):
                current_q = line[2:].strip()
            elif line.startswith("A:") and current_q:
                cards.append({"question": current_q, "answer": line[2:].strip()})
                current_q = None
        if not cards:
            cards.append({"question": "Flashcards", "answer": raw})
        return cards
