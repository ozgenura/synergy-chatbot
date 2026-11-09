"""Maskotun çizim ve durum mantığı; pencere açmaz."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mascot_art import HEIGHT, MOODS, PALETTE, WIDTH, runs, sprite  # noqa: E402
from mascot_state import bubble_text, publish_answer, read_state, state_for, write_state  # noqa: E402
from meeting import AgendaItem  # noqa: E402


def test_every_frame_fits_and_uses_palette():
    for mood in MOODS:
        for step in range(8):
            for facing_left in (False, True):
                grid = sprite(mood, step, facing_left)
                assert all(0 <= x < WIDTH and 0 <= y < HEIGHT for x, y in grid)
                assert set(grid.values()) <= set(PALETTE)


def test_facing_left_mirrors():
    right, left = sprite("idle"), sprite("idle", facing_left=True)
    assert all(left[(WIDTH - 1 - x, y)] == color for (x, y), color in right.items())


def test_runs_cover_all_pixels():
    grid = sprite("talking", 1)
    assert sum(width for _, _, width, _ in runs(grid)) == len(grid)


def test_state_for_answer():
    gap = AgendaItem("CEO?", "**Bottom line:** Bu veri elimdeki dokümanda yok.", "title", [])
    repeat = AgendaItem("Çay?", "**Bottom line:** Çay 500 TL.", "company", ["çay"], repeated=True)
    normal = AgendaItem("Çay?", "**Bottom line:** Çay 500 TL.", "company", ["çay"])
    assert (state_for(gap), state_for(repeat), state_for(normal)) == ("gap", "repeat", "talking")


def test_state_file_round_trip(tmp_path):
    path = tmp_path / "mascot_state.json"
    write_state("thinking", "...", path)
    first = read_state(path)
    publish_answer(AgendaItem("Çay?", "**Bottom line:** Çay 500 TL. Karar sizin.", "company", ["çay"]), path)
    second = read_state(path)
    assert first["state"] == "thinking"
    assert second["state"] == "talking"
    assert second["text"] == "Çay 500 TL."
    assert second["id"] != first["id"]


def test_missing_state_is_none(tmp_path):
    assert read_state(tmp_path / "yok.json") is None


def test_bubble_removes_markdown():
    assert bubble_text("**Bottom line:** Çay 500 TL.") == "Bottom line: Çay 500 TL."
