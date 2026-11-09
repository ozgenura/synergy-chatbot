"""Synergy'nin masaüstü maskotu. Çalıştırma: python mascot.py

Şeffaf ve her zaman üstte bir pencerede yaşar. Tıklayınca soru kutusu açılır,
sürüklenebilir, sağ tık ile kapanır. Streamlit arayüzündeki konuşmaya da tepki verir.
"""

import ctypes
import ctypes.wintypes
import queue
import random
import threading
import tkinter as tk
from pathlib import Path

import httpx
import ollama

from llm import answer_turn, warm_up
from mascot_art import HEIGHT, PALETTE, WIDTH, runs, sprite
from mascot_state import IDLE_LINES, bubble_text, read_state, state_for
from meeting import Meeting
from memory import GapMemory
from rag import Retriever

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "mars_turizm.txt"
MEMORY_PATH = ROOT / "memory" / "open_gaps.json"

SCALE = 5
WINDOW_W, WINDOW_H = 460, 420
TRANSPARENT = "#ff00fe"
TICK_MS = 120
SPEED = 5
EXIT_SPEED = 25
GRAVITY = 28
SPRITE_W, SPRITE_H = WIDTH * SCALE, HEIGHT * SCALE
SPRITE_X, SPRITE_Y = (WINDOW_W - SPRITE_W) // 2, WINDOW_H - SPRITE_H
BUBBLE_W = 360
RETURN_AFTER_S = 15


def work_area() -> tuple[int, int, int, int]:
    """Görev çubuğu hariç ekran alanı."""
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right, rect.bottom


class Mascot:
    def __init__(self, transparent: bool = True):
        self.root = tk.Tk()
        self.root.title("Synergy")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        if transparent:
            self.root.attributes("-transparentcolor", TRANSPARENT)
        self.canvas = tk.Canvas(self.root, width=WINDOW_W, height=WINDOW_H, bg=TRANSPARENT, highlightthickness=0, bd=0)
        self.canvas.pack()

        self.left, self.top, self.right, self.bottom = work_area()
        self.x = random.randint(self.left, max(self.left, self.right - WINDOW_W))
        self.y = self.ground
        self.fall = 0
        self.step = 0
        self.facing_left = False
        self.mood = "idle"
        self.state = "idle"
        self.ticks_left = 0
        self.target: int | None = None
        self.idle_ticks = 20
        self.gone_ticks = 0
        self.press: tuple[int, int] | None = None
        self.dragging = False
        self.composer: tk.Entry | None = None
        self.quitting = False
        self.destroyed = False
        self.last_state_id = (read_state() or {}).get("id")

        self.questions: queue.Queue[str] = queue.Queue()
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Soru sor", command=self.open_composer)
        self.menu.add_command(label="Kapat", command=self.quit_with_exit)
        # Çizim her karede yenilendiği için olaylar çizime değil tuvale bağlanır; yoksa bırakma olayı kaybolur.
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<ButtonPress-3>", lambda event: self.menu.tk_popup(event.x_root, event.y_root))

        self._place()
        self._draw()
        self.root.after(TICK_MS, self._tick)

    @property
    def ground(self) -> int:
        return self.bottom - WINDOW_H

    def _place(self) -> None:
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{self.x}+{self.y}")

    # --- Sohbet motoru: Tk donmasın diye ayrı iş parçacığında çalışır.

    def _worker(self) -> None:
        client = ollama.Client()
        retriever = None
        meeting = Meeting()
        history: list[dict] = []
        started = False
        while True:
            question = self.questions.get()
            try:
                if retriever is None:
                    retriever = Retriever(DATA_PATH, client)
                    warm_up(client)
                # Arayüz de aynı dosyaya yazabildiği için hafıza her turda yeniden okunur.
                memory = GapMemory(MEMORY_PATH)
                if not started:
                    memory.start_meeting()
                    started = True
                item = answer_turn(client, retriever, DATA_PATH.read_text(encoding="utf-8"), question, meeting, history, memory)
                self.events.put((state_for(item), bubble_text(item.answer)))
            except (ollama.ResponseError, ConnectionError, httpx.HTTPError):
                self.events.put(("gap", "Bottom line: Modele ulaşamıyorum. Ollama açık mı kontrol edin."))

    # --- Etkileşim

    def _on_press(self, event: tk.Event) -> None:
        # Şeffaf alanlar tıklamayı almaz; maskotun üstünde kalan görünür alan baloncuktur.
        if event.y < SPRITE_Y:
            self.set_state("idle")
            return
        self.press = (event.x_root - self.x, event.y_root - self.y)
        self.dragging = False

    def _on_drag(self, event: tk.Event) -> None:
        if self.press is None:
            return
        new_x, new_y = event.x_root - self.press[0], event.y_root - self.press[1]
        if self.dragging or abs(new_x - self.x) + abs(new_y - self.y) > 4:
            self.dragging = True
            self.x, self.y = new_x, min(new_y, self.ground)
            self.target = None
            self._place()

    def _on_release(self, _: tk.Event) -> None:
        if self.press is None:
            return
        was_dragging = self.dragging
        self.press = None
        self.dragging = False
        self.fall = 0
        if not was_dragging:
            self.close_composer() if self.composer else self.open_composer()

    def open_composer(self) -> None:
        if self.composer:
            return
        self.set_state("idle")
        self.target = None
        self.composer = tk.Entry(self.root, font=("Segoe UI", 12), width=34, relief="solid", bd=1)
        self.canvas.create_window(WINDOW_W // 2, SPRITE_Y - 22, window=self.composer, tags="composer")
        self.composer.bind("<Return>", self._submit)
        self.composer.bind("<Escape>", lambda _: self.close_composer())
        self.root.focus_force()
        self.composer.focus_force()

    def close_composer(self) -> None:
        if self.composer:
            self.canvas.delete("composer")
            self.composer.destroy()
            self.composer = None

    def _submit(self, _: tk.Event) -> None:
        question = self.composer.get().strip()
        self.close_composer()
        if question:
            self.questions.put(question)
            self.set_state("thinking", "...")

    # --- Durumlar ve hareket

    def quit_with_exit(self) -> None:
        """Uygulamayı kapatmadan önce çantasını alıp ekrandan çıkar."""
        self.close_composer()
        self.set_state("closed", "Bir sonraki toplantıya geçiyorum.")
        self.quitting = True

    def set_state(self, state: str, text: str = "") -> None:
        if self.quitting:
            return
        if self.gone_ticks:
            self.gone_ticks = 0
            self.root.deiconify()
            self.x = max(self.left, self.right - WINDOW_W)
            self._place()
        self.state = state
        self.ticks_left = max(50, len(text) * 2) if state in ("talking", "gap", "repeat") else 0
        self.target = None
        self._show_bubble(text)

    def _show_bubble(self, text: str) -> None:
        self.canvas.delete("bubble")
        if not text:
            return
        label = self.canvas.create_text(WINDOW_W // 2, 14, text=text, width=BUBBLE_W, font=("Segoe UI", 11), fill="#1b1f2a", anchor="n", tags="bubble")
        x0, y0, x1, y1 = self.canvas.bbox(label)
        shift = max(0, SPRITE_Y - 26 - y1) if y1 < SPRITE_Y - 26 else 0
        self.canvas.move(label, 0, shift)
        y0, y1 = y0 + shift, y1 + shift
        pad = 12
        self.canvas.create_rectangle(x0 - pad, y0 - pad, x1 + pad, y1 + pad, fill="#ffffff", outline=PALETTE["K"], width=3, tags="bubble")
        center = WINDOW_W // 2
        self.canvas.create_polygon(center - 10, y1 + pad, center + 10, y1 + pad, center, y1 + pad + 14, fill="#ffffff", outline=PALETTE["K"], width=3, tags="bubble")
        self.canvas.create_line(center - 8, y1 + pad, center + 8, y1 + pad, fill="#ffffff", width=3, tags="bubble")
        self.canvas.tag_raise(label)

    def _poll_interface(self) -> None:
        """Streamlit arayüzündeki konuşmaya tepki verir."""
        current = read_state()
        if current and current.get("id") != self.last_state_id:
            self.last_state_id = current.get("id")
            if current["state"] == "quit":
                self.quit_with_exit()
            else:
                self.set_state(current["state"], current.get("text", ""))

    def _idle_behavior(self) -> None:
        if self.composer:
            self.mood = "idle"
            return
        if self.target is not None:
            self.mood = "walk"
            direction = 1 if self.target > self.x else -1
            self.facing_left = direction < 0
            self.x += direction * SPEED
            if abs(self.target - self.x) <= SPEED:
                self.target = None
                self.idle_ticks = random.randint(15, 60)
            self._place()
            return
        self.mood = "watch" if self.idle_ticks % 37 < 8 else "idle"
        self.idle_ticks -= 1
        if self.idle_ticks <= 0:
            if random.random() < 0.15:
                self.set_state("talking", random.choice(IDLE_LINES))
                self.ticks_left = 25
            else:
                self.target = random.randint(self.left, max(self.left, self.right - WINDOW_W))

    def _leave(self) -> None:
        """Çantasını alıp en yakın ekran kenarından çıkar."""
        self.mood = "walk"
        self.facing_left = self.x + WINDOW_W // 2 < (self.left + self.right) // 2
        self.x += -EXIT_SPEED if self.facing_left else EXIT_SPEED
        self._place()
        if self.x + SPRITE_X > self.right or self.x + SPRITE_X + SPRITE_W < self.left:
            if self.quitting:
                self.destroyed = True
                self.root.destroy()
                return
            self.root.withdraw()
            self.state = "gone"
            self.gone_ticks = RETURN_AFTER_S * 1000 // TICK_MS

    def _tick(self) -> None:
        self.step += 1
        self._poll_interface()
        while not self.events.empty():
            self.set_state(*self.events.get())

        if self.state == "gone":
            self.gone_ticks -= 1
            if self.gone_ticks <= 0:
                self.set_state("idle")
        elif self.dragging:
            self.mood = "carried"
        elif self.y < self.ground and self.press is None:
            self.mood = "carried"
            self.fall += 4
            self.y = min(self.ground, self.y + min(self.fall, GRAVITY))
            self._place()
        elif self.state == "closed":
            self._leave()
        elif self.state == "thinking":
            self.mood = "thinking"
        elif self.state in ("talking", "gap", "repeat"):
            self.mood = self.state
            self.ticks_left -= 1
            if self.ticks_left <= 0:
                self.set_state("idle")
        else:
            self._idle_behavior()

        if self.destroyed:
            return
        if self.state != "gone":
            self._draw()
        self.root.after(TICK_MS, self._tick)

    def _draw(self) -> None:
        self.canvas.delete("sprite")
        frame = sprite(self.mood, self.step // 2, self.facing_left)
        for x, y, width, color in runs(frame):
            px, py = SPRITE_X + x * SCALE, SPRITE_Y + y * SCALE
            self.canvas.create_rectangle(px, py, px + width * SCALE, py + SCALE, fill=PALETTE[color], outline="", tags="sprite")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    # Yüksek DPI ekranlarda koordinatlar ve piksel çizimi bulanıklaşmasın.
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    Mascot().run()


if __name__ == "__main__":
    main()
