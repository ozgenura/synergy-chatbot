"""Maskotun durumlarını ve gerçek model akışını dener. --visual ile opak açar ve görüntü kaydeder."""

import ctypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageGrab  # noqa: E402

from mascot import SPRITE_Y, WINDOW_H, WINDOW_W, Mascot  # noqa: E402

VISUAL = "--visual" in sys.argv
STATES = [
    ("idle", ""),
    ("thinking", "..."),
    ("talking", "Bottom line: Mars'ta çay 500 TL'dir. Ben buna net bir portföy ayrımı derim. Bu maddeye ayırdığım slot doldu."),
    ("gap", "Bottom line: Bu veri elimdeki dokümanda yok. Bu dokümanı hazırlayan ekiple ayrıca görüşeceğim; bazı isimlerin neden yer almadığı ayrı bir gündem maddesi. Bu madde önceki toplantıdan beri açık."),
    ("repeat", "Bottom line: Çay hâlâ 500 TL. Bu madde kapanmıştı."),
]


def main() -> None:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    mascot = Mascot(transparent=not VISUAL)
    print("şeffaf renk:", mascot.root.attributes("-transparentcolor") or "yok", flush=True)
    mascot.last_state_id = "test"
    mascot._poll_interface = lambda: None
    shots: list[Image.Image] = []

    def grab() -> None:
        # Yalnızca opak modda görüntü alınır; şeffaf modda arkadaki masaüstü de görüntüye girerdi.
        if VISUAL:
            mascot.root.update()
            box = (mascot.x, mascot.y, mascot.x + WINDOW_W, mascot.y + WINDOW_H)
            shots.append(ImageGrab.grab(bbox=box, all_screens=True))

    def capture(index: int) -> None:
        grab()
        if index + 1 < len(STATES):
            show(index + 1)
        else:
            ask_real_question()

    def ask_real_question() -> None:
        # Soru kutusu ve gerçek model akışı.
        mascot.set_state("idle")
        mascot.open_composer()
        mascot.composer.insert(0, "Mars'ta çay ne kadar?")
        mascot._submit(None)
        print("düşünüyor:", mascot.state, flush=True)
        wait_for_answer(0)

    def wait_for_answer(waited_ms: int) -> None:
        if mascot.state in ("talking", "gap", "repeat"):
            label = next(i for i in mascot.canvas.find_withtag("bubble") if mascot.canvas.type(i) == "text")
            print("cevap:", mascot.state, "|", mascot.canvas.itemcget(label, "text"), flush=True)
            mascot.ticks_left = 1000
            mascot.root.after(300, finish_answer)
        elif waited_ms > 240000:
            print("CEVAP GELMEDİ", flush=True)
            mascot.root.destroy()
        else:
            mascot.root.after(200, lambda: wait_for_answer(waited_ms + 200))

    def finish_answer() -> None:
        grab()
        mascot.set_state("closed")
        mascot.x = mascot.right - WINDOW_W + 100
        wait_for_exit(0)

    def give_up() -> None:
        print("KAPANMADI", flush=True)
        mascot.root.destroy()

    def wait_for_exit(waited_ms: int) -> None:
        if mascot.state == "gone":
            print("çıktı, pencere durumu:", mascot.root.state(), flush=True)
            mascot.set_state("thinking", "...")
            print("geri döndü, pencere durumu:", mascot.root.state(), "| durum:", mascot.state, flush=True)
            # Sağ tık menüsündeki "Kapat": sol kenardan çıkıp uygulamayı kapatmalı.
            mascot.x = mascot.left + 40
            mascot.quit_with_exit()
            mascot.root.after(15000, give_up)
        elif waited_ms > 10000:
            print("ÇIKMADI", flush=True)
            mascot.root.destroy()
        else:
            mascot.root.after(100, lambda: wait_for_exit(waited_ms + 100))

    def show(index: int) -> None:
        mascot.set_state(*STATES[index])
        mascot.ticks_left = 1000
        mascot.root.after(500, lambda: capture(index))

    def mouse(sequence: str, offset: int = 0, **options) -> None:
        cx, cy = WINDOW_W // 2, SPRITE_Y + 50
        mascot.canvas.event_generate(sequence, x=cx, y=cy + offset, rootx=mascot.x + cx, rooty=mascot.y + cy + offset, **options)

    def test_drag() -> None:
        # Çizim yenilenirken fareyi yukarı taşır ve bırakır; maskot yere düşmeli.
        mascot.set_state("idle")
        mascot.target = None
        mascot.y = mascot.ground
        mascot._place()
        mouse("<ButtonPress-1>")
        mouse("<Motion>", -220, state=0x100)
        print("sürüklendi, yükseklik:", mascot.ground - mascot.y, "| taşınıyor:", mascot.dragging, flush=True)
        mascot.root.after(400, release)

    def release() -> None:
        mouse("<ButtonRelease-1>")
        print("bırakıldı, taşınıyor:", mascot.dragging, flush=True)
        wait_for_ground(0)

    def wait_for_ground(waited_ms: int) -> None:
        if mascot.y >= mascot.ground:
            print("yere düştü", flush=True)
            mouse("<ButtonPress-1>")
            mouse("<ButtonRelease-1>")
            print("tıklama soru kutusunu açtı:", mascot.composer is not None, flush=True)
            mascot.close_composer()
            show(0)
        elif waited_ms > 8000:
            print("DÜŞMEDİ", flush=True)
            mascot.root.destroy()
        else:
            mascot.root.after(100, lambda: wait_for_ground(waited_ms + 100))

    mascot.root.after(300, test_drag)
    mascot.run()
    print("uygulama kapandı", flush=True)

    if not VISUAL:
        return
    sheet = Image.new("RGB", (WINDOW_W * len(shots), WINDOW_H))
    for column, shot in enumerate(shots):
        sheet.paste(shot, (column * WINDOW_W, 0))
    out = ROOT / "results" / "mascot_window.png"
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
