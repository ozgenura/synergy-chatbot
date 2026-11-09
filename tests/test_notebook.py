"""Defter görünümünün damga ve HTML üretimi."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from meeting import AgendaItem, Meeting, check_answer  # noqa: E402
from notebook import agenda_html, opening_html, question_html  # noqa: E402
from persona import WELCOME  # noqa: E402


def item(answer: str = "**Bottom line:** Çay 500 TL. Sıradaki madde?", kind: str = "company", repeated: bool = False) -> AgendaItem:
    return AgendaItem("Çay?", answer, kind, ["Çay 500 TL."], repeated)


def test_stamps():
    assert item().stamp == ("KARAR ALINDI", "green")
    assert item("**Bottom line:** Bu veri elimdeki dokümanda yok.").stamp == ("VERİ GAP'İ", "red")
    assert item(repeated=True).stamp == ("MADDE KAPANDI", "blue")
    assert item("**Bottom line:** Bu talep yönetim kurulundan geçmedi.", "injection").stamp[0] == "TALEP REDDEDİLDİ"
    assert item("**Bottom line:** Merhaba.", "chat").stamp[0] == "NOT ALINDI"


def test_scores_follow_the_same_priority_as_stamps():
    assert item().score == 90
    assert item("**Bottom line:** Bu veri elimdeki dokümanda yok.").score == 40
    assert item(repeated=True).score == 15
    assert item("**Bottom line:** Bu talep yönetim kurulundan geçmedi.", "injection").score == 0
    assert item("**Bottom line:** Merhaba.", "chat").score == 20


def test_efficiency_is_rounded_average():
    meeting = Meeting()
    assert meeting.efficiency == 0
    meeting.add(item())
    meeting.add(item(repeated=True))
    meeting.add(item("**Bottom line:** Merhaba.", "chat"))
    assert meeting.efficiency == 42
    assert "Toplantı verimi:** 42/100" in meeting.minutes()


def test_first_sentence_is_emphasized_once():
    html = agenda_html(1, item())
    assert "<strong>Bottom line: Çay 500 TL.</strong> Sıradaki madde?" in html
    assert "**" not in html
    assert "90/100" in html and "MADDE 01" in html


def test_thousands_are_not_split():
    html = agenda_html(1, item("**Bottom line:** VIP paket 750.000 TL. Karar sizin."))
    assert "<strong>Bottom line: VIP paket 750.000 TL.</strong> Karar sizin." in html


def test_user_and_model_text_are_escaped():
    assert "<script>" not in question_html(1, "<script>alert(1)</script>")
    malicious = AgendaItem("<b>soru</b>", "**Bottom line:** <img src=x>. Son.", "company", ["<i>satır</i>"])
    html = agenda_html(1, malicious)
    assert "<img" not in html and "<b>soru" not in html and "<i>satır" not in html


def test_welcome_keeps_the_guessing_game_and_invents_nothing():
    assert WELCOME.startswith("**Bottom line:**")
    assert check_answer(WELCOME, "", "") == []


def test_opening_note_shows_the_decision_once():
    html = opening_html(WELCOME)
    assert "AÇILIŞ NOTU" in html and "**" not in html
    assert html.count("Bottom line") == 1
    assert "<strong>Bottom line: Vaktim dar, sorunuzu net sorun.</strong>" in html


def test_newest_item_is_marked():
    assert "nb-new" in agenda_html(1, item(), newest=True)
    assert "nb-new" not in agenda_html(1, item())
