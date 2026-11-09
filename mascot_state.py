"""Streamlit arayüzü ile masaüstü maskotu arasındaki küçük durum dosyası."""

import json
import os
import time
from pathlib import Path

from meeting import AgendaItem, first_sentence

STATE_PATH = Path(__file__).parent / "memory" / "mascot_state.json"
IDLE_LINES = ["Bu çeyrek zor geçecek.", "Vizyon beklemez.", "Kim bu kadar slot açtı?", "Toplantım var."]


def state_for(item: AgendaItem) -> str:
    """Cevabın maskotta hangi davranışa karşılık geldiğini seçer."""
    if item.is_gap:
        return "gap"
    return "repeat" if item.repeated else "talking"


def bubble_text(answer: str) -> str:
    return answer.replace("**", "").strip()


def write_state(state: str, text: str = "", path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    payload = {"id": time.time_ns(), "state": state, "text": text}
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        # Maskot o an dosyayı okuyorsa bu durum atlanır; sohbeti etkilememeli.
        pass


def publish_answer(item: AgendaItem, path: Path = STATE_PATH) -> None:
    """Arayüzdeki cevabın özetini maskota iletir."""
    write_state(state_for(item), first_sentence(item.answer), path)


def read_state(path: Path = STATE_PATH) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
