import argparse
import subprocess
import sys
from ui.cli import CLI


def main():
    parser = argparse.ArgumentParser(
        description="AI Study Tutor — Explain topics, generate quizzes, and make flashcards from your notes."
    )

    subparsers = parser.add_subparsers(dest="command")

    # explain
    explain_parser = subparsers.add_parser("explain", help="Explain a topic using your notes (interactive)")
    explain_parser.add_argument("--topic", type=str, required=True, help="Topic or question to explain")
    explain_parser.add_argument("--notes-folder", type=str, default="data/notes", help="Folder containing your notes")

    # quiz
    quiz_parser = subparsers.add_parser("quiz", help="Interactive quiz with evaluation and scoring")
    quiz_parser.add_argument("--topic", type=str, required=True, help="Topic or chapter to quiz on")
    quiz_parser.add_argument("--notes-folder", type=str, default="data/notes", help="Folder containing your notes")
    quiz_parser.add_argument("--num", type=int, default=5, help="Number of questions")

    # flashcards
    flash_parser = subparsers.add_parser("flashcards", help="Generate flashcards from your notes")
    flash_parser.add_argument("--topic", type=str, required=True, help="Topic or chapter for flashcards")
    flash_parser.add_argument("--notes-folder", type=str, default="data/notes", help="Folder containing your notes")
    flash_parser.add_argument("--num", type=int, default=10, help="Number of flashcards")

    # practice
    practice_parser = subparsers.add_parser("practice", help="Socratic practice dialogue on a topic")
    practice_parser.add_argument("--topic", type=str, required=True, help="Topic to practice")
    practice_parser.add_argument("--notes-folder", type=str, default="data/notes", help="Folder containing your notes")

    # dashboard
    subparsers.add_parser("dashboard", help="Launch the Streamlit dashboard")

    args = parser.parse_args()
    cli = CLI()

    if args.command == "explain":
        cli.explain_topic(args.topic, args.notes_folder)

    elif args.command == "quiz":
        cli.generate_quiz(args.topic, args.notes_folder, args.num)

    elif args.command == "flashcards":
        cli.generate_flashcards(args.topic, args.notes_folder, args.num)

    elif args.command == "practice":
        cli.run_practice(args.topic, args.notes_folder)

    elif args.command == "dashboard":
        subprocess.run([sys.executable, "-m", "streamlit", "run", "ui/dashboard.py"])

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
