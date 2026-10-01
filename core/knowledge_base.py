from typing import List, Dict
import re


# ~4 chars per token, so 150,000 chars is roughly 37k tokens of notes per request.
MAX_CONTEXT_CHARS = 150_000


class KnowledgeBase:
    """
    Very simple in-memory knowledge base.
    Holds a list of notes and can build a crude 'relevant context'
    for a given topic by keyword matching.

    Later you can upgrade this to use embeddings/vector search.
    """

    def __init__(self):
        self.notes: List[Dict[str, str]] = []

    def load_notes(self, notes: List[Dict[str, str]]):
        """Replace existing notes with the given list."""
        self.notes = notes

    def _score_note(self, topic: str, content: str) -> int:
        """
        Naive scoring: count occurrences of topic words in the content.
        """
        topic_words = re.findall(r"\w+", topic.lower())
        text = content.lower()
        score = 0
        for w in topic_words:
            if w:
                score += text.count(w)
        return score

    def build_context_for_topic(self, topic: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
        """
        Returns a big context string built from the most relevant notes.
        For now: sort notes by naive score, then concatenate until max_chars.
        """
        if not self.notes:
            return ""

        scored = []
        for note in self.notes:
            score = self._score_note(topic, note["content"])
            scored.append((score, note))

        # highest score first
        scored.sort(key=lambda x: x[0], reverse=True)

        context_parts = []
        total_chars = 0
        for score, note in scored:
            if score == 0 and context_parts:
                # if we've already added some relevant notes,
                # we can skip completely irrelevant ones.
                continue

            text = f"From {note['name']}:\n" + note["content"].strip() + "\n\n"
            if total_chars + len(text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 0:
                    context_parts.append(text[:remaining])
                break
            else:
                context_parts.append(text)
                total_chars += len(text)

        return "".join(context_parts) if context_parts else ""
