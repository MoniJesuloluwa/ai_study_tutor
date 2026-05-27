from typing import List, Dict, Generator
from core.tutor import Tutor


class PracticeSession:
    """
    Manages a Socratic practice conversation.
    Wraps Tutor so the caller only needs to pass new user messages.
    """

    def __init__(self, topic: str, context: str):
        self.topic = topic
        self.context = context
        self.tutor = Tutor()
        self.history: List[Dict] = []
        self.turn_count = 0

    def start_stream(self) -> Generator[str, None, None]:
        """Generate the tutor's opening question."""
        for chunk in self.tutor.practice_stream(self.topic, self.context, []):
            yield chunk

    def reply_stream(self, assistant_opening: str, user_message: str) -> Generator[str, None, None]:
        """
        Given the tutor's previous text and the student's reply,
        generate the next tutor turn.
        """
        if not self.history:
            # First reply — build initial history
            self.history = [
                {
                    "role": "user",
                    "content": f"I want to practice the topic: {self.topic}. Please start the session.",
                },
                {"role": "assistant", "content": assistant_opening},
            ]

        self.history.append({"role": "user", "content": user_message})
        self.turn_count += 1

        full_response = ""
        for chunk in self.tutor.practice_stream(self.topic, self.context, self.history):
            full_response += chunk
            yield chunk

        self.history.append({"role": "assistant", "content": full_response})

    def start(self) -> str:
        """Non-streaming version for CLI."""
        return self.tutor.practice(self.topic, self.context, [])

    def reply(self, assistant_opening: str, user_message: str) -> str:
        """Non-streaming version for CLI."""
        if not self.history:
            self.history = [
                {
                    "role": "user",
                    "content": f"I want to practice the topic: {self.topic}. Please start the session.",
                },
                {"role": "assistant", "content": assistant_opening},
            ]
        self.history.append({"role": "user", "content": user_message})
        self.turn_count += 1
        response = self.tutor.practice(self.topic, self.context, self.history)
        self.history.append({"role": "assistant", "content": response})
        return response
