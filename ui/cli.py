from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from core.loader import NotesLoader
from core.knowledge_base import KnowledgeBase, MAX_CONTEXT_CHARS
from core.tutor import Tutor
from core.practice import PracticeSession
import core.progress as progress


class CLI:
    """Command-line interface for the AI Study Tutor."""

    def __init__(self):
        self.console = Console()
        self.loader = NotesLoader()
        self.kb = KnowledgeBase()
        self.tutor = Tutor()

    # ---------- Helpers ----------

    def _load_notes_and_context(self, notes_folder: str, topic: str) -> str:
        self.console.print(f"[bold]Loading notes from:[/] {notes_folder}")
        notes = self.loader.load_notes_from_folder(notes_folder)
        if not notes:
            self.console.print("[yellow]No notes found. Make sure the folder has .txt, .md, or .pdf files.[/]")
            return ""
        self.kb.load_notes(notes)
        context = self.kb.build_context_for_topic(topic)
        if not context.strip():
            self.console.print("[yellow]No strongly matching notes for that topic. Using all notes as context.[/]")
            all_text = "\n\n".join(n["content"] for n in notes)
            return all_text[:MAX_CONTEXT_CHARS]
        return context

    # ---------- Explain ----------

    def explain_topic(self, topic: str, notes_folder: str):
        self.console.rule(f"[bold blue]Explain: {topic}[/bold blue]")
        context = self._load_notes_and_context(notes_folder, topic)

        history = []
        first_turn = True

        while True:
            if first_turn:
                self.console.print("[dim]Generating explanation…[/dim]")
            else:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan] (or 'quit' to exit)")
                if user_input.strip().lower() in {"quit", "q", "exit"}:
                    break
                history.append({"role": "user", "content": user_input})

            response = self.tutor.explain(topic, context, history)
            self.console.print(Panel(response, border_style="cyan"))
            history.append({"role": "assistant", "content": response})
            first_turn = False

        progress.record_session(topic, "explain")
        self.console.print("[dim]Session recorded.[/dim]")

    # ---------- Quiz ----------

    def generate_quiz(self, topic: str, notes_folder: str, num_questions: int):
        self.console.rule(f"[bold green]Quiz: {topic}[/bold green]")
        context = self._load_notes_and_context(notes_folder, topic)

        self.console.print(f"[dim]Generating {num_questions} questions…[/dim]")
        questions = self.tutor.generate_quiz_questions(topic, context, num_questions)

        total_score = 0
        max_score = len(questions) * 2  # 2 points per question

        for i, question in enumerate(questions, start=1):
            self.console.print(f"\n[bold green]Q{i}:[/bold green] {question}")
            answer = Prompt.ask("[bold cyan]Your answer[/bold cyan]")
            result = self.tutor.evaluate_answer(topic, question, answer, context)

            score_label = {2: "[green]Correct[/green]", 1: "[yellow]Partial[/yellow]", 0: "[red]Incorrect[/red]"}
            self.console.print(Panel(
                result["feedback"],
                title=score_label.get(result["score"], ""),
                border_style="green" if result["score"] == 2 else ("yellow" if result["score"] == 1 else "red"),
            ))
            total_score += result["score"]

        pct = round(total_score / max_score * 100) if max_score else 0
        self.console.rule(f"[bold]Final score: {total_score}/{max_score} ({pct}%)[/]")
        progress.record_session(topic, "quiz", score=total_score, total=max_score)

    # ---------- Flashcards ----------

    def generate_flashcards(self, topic: str, notes_folder: str, num_cards: int):
        self.console.rule(f"[bold magenta]Flashcards: {topic}[/bold magenta]")
        context = self._load_notes_and_context(notes_folder, topic)

        self.console.print(f"[dim]Generating {num_cards} flashcards…[/dim]")
        cards = self.tutor.generate_flashcards(topic, context, num_cards)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column(" # ", justify="right")
        table.add_column("Question")
        table.add_column("Answer")

        for idx, card in enumerate(cards, start=1):
            table.add_row(str(idx), card["question"], card["answer"])

        self.console.print(table)
        progress.record_session(topic, "flashcards")

    # ---------- Practice ----------

    def run_practice(self, topic: str, notes_folder: str):
        self.console.rule(f"[bold yellow]Practice: {topic}[/bold yellow]")
        context = self._load_notes_and_context(notes_folder, topic)

        session = PracticeSession(topic, context)
        self.console.print("[dim]Starting Socratic practice session…[/dim]")

        opening = session.start()
        self.console.print(Panel(opening, border_style="yellow"))

        while True:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan] (or 'quit' to exit)")
            if user_input.strip().lower() in {"quit", "q", "exit"}:
                break
            response = session.reply(opening, user_input)
            self.console.print(Panel(response, border_style="yellow"))

        progress.record_session(topic, "practice")
        self.console.print("[dim]Session recorded.[/dim]")
