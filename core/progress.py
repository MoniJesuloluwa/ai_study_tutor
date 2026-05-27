import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROGRESS_FILE = Path("data/progress.json")

_EMPTY = {"sessions": [], "topics": {}}


def _load() -> Dict:
    if not PROGRESS_FILE.exists():
        return dict(_EMPTY)
    try:
        data = json.loads(PROGRESS_FILE.read_text())
        return data if data else dict(_EMPTY)
    except (json.JSONDecodeError, ValueError):
        return dict(_EMPTY)


def _save(data: Dict) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, indent=2))


def record_session(
    topic: str,
    mode: str,
    score: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    """Record a completed study session."""
    data = _load()

    session = {
        "id": str(uuid.uuid4())[:8],
        "date": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "mode": mode,
    }
    if score is not None and total:
        session["score"] = score
        session["total"] = total
        session["pct"] = round(score / total * 100, 1)

    data["sessions"].append(session)

    # Update per-topic summary
    t = data["topics"].setdefault(topic, {
        "sessions": 0,
        "last_studied": None,
        "modes_used": [],
        "quiz_scores": [],
    })
    t["sessions"] += 1
    t["last_studied"] = datetime.now().date().isoformat()
    if mode not in t["modes_used"]:
        t["modes_used"].append(mode)
    if score is not None and total:
        t["quiz_scores"].append(round(score / total * 100, 1))

    _save(data)


def get_all_sessions() -> List[Dict]:
    return _load().get("sessions", [])


def get_topic_summary() -> Dict:
    return _load().get("topics", {})


def get_recent_sessions(n: int = 10) -> List[Dict]:
    sessions = get_all_sessions()
    return sessions[-n:]


def get_quiz_scores_for_topic(topic: str) -> List[float]:
    topics = get_topic_summary()
    return topics.get(topic, {}).get("quiz_scores", [])
