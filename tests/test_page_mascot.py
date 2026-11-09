"""Sayfa kenarı maskotunun HTML üretimi; tarayıcı açmaz."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from page_mascot import ENTER_S, EXIT_S, FILMS, REACTION_MIN_S, duration, page_mascot_html, sheet_svg  # noqa: E402


def test_every_state_renders():
    for state in FILMS:
        html = page_mascot_html(state, "Çay 500 TL.")
        assert 'class="sm-root"' in html and "sm-a" in html


def test_text_is_escaped_and_kept_on_one_line():
    html = page_mascot_html("talking", "<img src=x>\n\nikinci satır")
    assert "<img" not in html
    assert "&lt;img src=x&gt; ikinci satır" in html
    body = html.split("</style>", 1)[1]
    assert "\n" not in body


def test_reaction_lasts_longer_for_long_text():
    assert duration("talking", "kısa") == REACTION_MIN_S
    assert duration("gap", "a" * 100) == 24
    assert duration("enter") == ENTER_S and duration("exit") == EXIT_S
    assert duration("idle") is None and duration("thinking") is None


def test_reaction_returns_to_idle():
    assert "sm-after" in page_mascot_html("talking", "Karar.")
    assert "sm-after" in page_mascot_html("enter")


def test_exit_and_thinking_have_no_following_idle():
    assert 'class="sm-layer sm-after"' not in page_mascot_html("exit")
    assert 'class="sm-layer sm-after"' not in page_mascot_html("thinking", "...")


def test_idle_line_only_shows_when_idle():
    assert "sm-line" in page_mascot_html("idle", idle_line="Vizyon beklemez.").split("</style>", 1)[1]
    assert "Vizyon" not in page_mascot_html("thinking", "...", idle_line="Vizyon beklemez.")


def test_film_stops_on_exact_frames():
    # jump-none'da adım sayısı kare sayısına eşit olmalı; yoksa şerit karelerin arasında durur.
    html = page_mascot_html("talking", "Karar.")
    assert "steps(2, jump-none)" in html
    assert f"steps({len(FILMS['idle'])}, jump-none)" in page_mascot_html("idle")


def test_timers_are_named_per_state():
    # Streamlit aynı HTML öğesini yeniden kullanır; ortak ad, bitmiş animasyonu yeni duruma taşır.
    enter, leaving = page_mascot_html("enter"), page_mascot_html("exit", "Gidiyorum.")
    assert "sm-hide-enter" in enter and "sm-hide-exit" not in enter
    assert "sm-hide-exit" in leaving and "sm-hide-enter" not in leaving


def test_repeated_frames_are_drawn_once():
    svg = sheet_svg(FILMS["idle"], True)
    assert svg.count("<use ") == len(FILMS["idle"])
    assert svg.count("<g id=") == len(set(FILMS["idle"]))
