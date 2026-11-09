"""Panel açıkken sayfanın kenarında duran maskot.

Masaüstü maskotuyla aynı çizimleri kullanır. JavaScript yerine kare şeridi ve CSS
animasyonu kullanılır; böylece Streamlit'in yeniden çizimi animasyonu bozmaz.
"""

from base64 import b64encode
from html import escape

from mascot_art import HEIGHT, PALETTE, WIDTH, Grid, runs, sprite

Frame = tuple[str, int]

STEP_S = 0.24
ENTER_S = 1.2
EXIT_WAIT_S = 1.4
EXIT_S = EXIT_WAIT_S + ENTER_S
REACTION_MIN_S = 6.0
REACTION_S_PER_CHAR = 0.24
REACTIONS = ("talking", "gap", "repeat")

_BLINK_LOOP: tuple[Frame, ...] = (("idle", 0),) * 7 + (("idle", 7),)
FILMS: dict[str, tuple[Frame, ...]] = {
    "idle": _BLINK_LOOP * 3 + (("watch", 0),) * 8,
    "thinking": (("thinking", 0),),
    "talking": (("talking", 0), ("talking", 1)),
    "gap": (("gap", 0), ("gap", 1), ("gap", 2), ("gap", 3)),
    "repeat": (("repeat", 0), ("repeat", 1)),
    "enter": (("walk", 0), ("walk", 1)),
    "exit": (("walk", 0), ("walk", 1)),
}

BASE_CSS = """
.sm-root { --sm-s: 4; position: fixed; right: 20px; bottom: 14px; z-index: 999980; width: calc(26px * var(--sm-s)); height: calc(33px * var(--sm-s)); pointer-events: none; }
.sm-layer { position: absolute; inset: 0; }
.sm-sprite { width: 100%; height: 100%; background-repeat: no-repeat; }
.sm-after { visibility: hidden; }
.sm-bubble { position: absolute; right: 0; bottom: calc(100% + 12px); width: max-content; max-width: 190px; padding: 8px 10px; background: #ffffff; border: 2px solid #1b1f2a; color: #1b1f2a; font: 13px/1.4 "Segoe UI", sans-serif; }
.sm-bubble::after { content: ""; position: absolute; right: 44px; top: 100%; border: 7px solid transparent; border-top-color: #1b1f2a; }
.sm-line { opacity: 0; animation: sm-line 30s linear infinite; }
@keyframes sm-film { from { background-position: 0 0; } to { background-position: 100% 0; } }
@keyframes sm-in { from { transform: translateX(170px); } to { transform: none; } }
@keyframes sm-out { from { transform: none; } to { transform: translateX(170px); } }
@keyframes sm-line { 0%, 66% { opacity: 0; } 68%, 84% { opacity: 1; } 86%, 100% { opacity: 0; } }
@media (min-width: 901px) and (max-width: 1320px) { [data-testid="stMainBlockContainer"], [data-testid="stBottomBlockContainer"] { padding-right: 140px !important; } .sm-bubble { max-width: 120px; } }
@media (max-width: 900px) { .sm-root { --sm-s: 2; right: 16px; bottom: 124px; } .sm-bubble { display: none; } }
@media (prefers-reduced-motion: reduce) { .sm-sprite { animation: none !important; } .sm-layer { transform: none !important; } }
"""


def _paths(grid: Grid) -> str:
    """Pikselleri renge göre tek yolda birleştirir; sayfaya giden veri küçük kalır."""
    by_color: dict[str, list[str]] = {}
    for x, y, width, color in runs(grid):
        by_color.setdefault(color, []).append(f"M{x} {y}h{width}v1h-{width}z")
    return "".join(f'<path fill="{PALETTE[color]}" d="{"".join(parts)}"/>' for color, parts in by_color.items())


def sheet_svg(frames: tuple[Frame, ...], facing_left: bool) -> str:
    """Kareleri yan yana dizer. Tekrar eden kareler bir kez çizilip referansla kullanılır."""
    unique = list(dict.fromkeys(frames))
    defs = "".join(f'<g id="f{i}">{_paths(sprite(mood, step, facing_left))}</g>' for i, (mood, step) in enumerate(unique))
    uses = "".join(f'<use href="#f{unique.index(frame)}" x="{i * WIDTH}"/>' for i, frame in enumerate(frames))
    width = len(frames) * WIDTH
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{HEIGHT}" viewBox="0 0 {width} {HEIGHT}" '
        f'shape-rendering="crispEdges"><defs>{defs}</defs>{uses}</svg>'
    )


def _film_rule(selector: str, state: str, facing_left: bool) -> str:
    frames = FILMS[state]
    count = len(frames)
    data = b64encode(sheet_svg(frames, facing_left).encode()).decode()
    animation = "none" if count == 1 else f"sm-film {count * STEP_S:.2f}s steps({count}, jump-none) infinite"
    return f".{selector} {{ background-image: url(data:image/svg+xml;base64,{data}); background-size: {count * 100}% 100%; animation: {animation}; }}"


def duration(state: str, text: str = "") -> float | None:
    """Tepkinin saniye cinsinden süresi; süresiz durumlar için None."""
    if state == "enter":
        return ENTER_S
    if state == "exit":
        return EXIT_S
    if state in REACTIONS:
        return max(REACTION_MIN_S, len(text) * REACTION_S_PER_CHAR)
    return None


def _layer(layer_class: str, film_class: str) -> str:
    return f'<div class="sm-layer {layer_class}"><div class="sm-sprite {film_class}"></div></div>'


def page_mascot_html(state: str = "idle", text: str = "", idle_line: str = "") -> str:
    """Duruma uygun maskotu döndürür. Metin model çıktısı olabileceği için kaçışlanır."""
    # Boş satır Streamlit'in HTML bloğunu keser; metin tek satıra indirilir.
    text = " ".join(text.split())
    seconds = duration(state, text)
    rules = [_film_rule("sm-a", state, facing_left=state != "exit")]
    layers = [_layer("sm-until", "sm-a")]
    bubble_class = ""

    if seconds is not None:
        # Streamlit öğeleri yeniden kullanır; aynı addaki bitmiş animasyon yeni öğeye geçmesin diye ad duruma özeldir.
        rules.append(f"@keyframes sm-hide-{state} {{ from, to {{ visibility: hidden; }} }}")
        rules.append(f"@keyframes sm-show-{state} {{ from, to {{ visibility: visible; }} }}")
        hide = f"sm-hide-{state} 1ms linear {seconds:.2f}s forwards"
        move ={"enter": f"sm-in {ENTER_S}s linear, ", "exit": f"sm-out {ENTER_S}s linear {EXIT_WAIT_S}s forwards, "}.get(state, "")
        rules.append(f".sm-until {{ animation: {move}{hide}; }}")
        rules.append(f".sm-timed {{ animation: {hide}; }}")
        bubble_class = " sm-timed"
        if state != "exit":
            rules.append(_film_rule("sm-b", "idle", facing_left=True))
            rules.append(f".sm-after {{ animation: sm-show-{state} 1ms linear {seconds:.2f}s forwards; }}")
            layers.append(_layer("sm-after", "sm-b"))

    bubble = ""
    if text:
        bubble = f'<div class="sm-bubble{bubble_class}">{escape(text)}</div>'
    elif state == "idle" and idle_line:
        bubble = f'<div class="sm-bubble sm-line">{escape(idle_line)}</div>'

    return f'<style>{BASE_CSS}{"".join(rules)}</style><div class="sm-root" aria-hidden="true">{bubble}{"".join(layers)}</div>'
