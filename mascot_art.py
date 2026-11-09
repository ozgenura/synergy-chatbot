"""Synergy maskotunun piksel çizimleri. Harici görsel kullanılmaz, her kare koddan üretilir."""

WIDTH, HEIGHT = 26, 33

PALETTE = {
    "K": "#1b1f2a",  # dış çizgi
    "S": "#f2c39b",  # ten
    "H": "#3a2a20",  # saç
    "R": "#9aa0ab",  # kır şakak
    "N": "#24344f",  # takım
    "L": "#3b5278",  # yaka
    "P": "#1d2940",  # pantolon
    "W": "#f4f5f7",  # gömlek
    "T": "#c8323c",  # kravat
    "C": "#8a5428",  # çanta
    "G": "#e6b73c",  # altın
    "M": "#7a2a2a",  # ağız içi
    "D": "#6cc4f0",  # ter damlası
}

MOODS = ("idle", "walk", "watch", "thinking", "talking", "gap", "repeat", "carried")

Grid = dict[tuple[int, int], str]


def _rect(grid: Grid, x: int, y: int, width: int, height: int, color: str) -> None:
    for py in range(y, y + height):
        for px in range(x, x + width):
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                grid[(px, py)] = color


def _outlined(grid: Grid, x: int, y: int, width: int, height: int, color: str) -> None:
    _rect(grid, x, y, width, height, "K")
    _rect(grid, x + 1, y + 1, width - 2, height - 2, color)


def _head(grid: Grid, mood: str, step: int) -> None:
    _rect(grid, 6, 7, 1, 3, "S")
    _rect(grid, 19, 7, 1, 3, "S")
    _outlined(grid, 7, 2, 12, 11, "S")
    _rect(grid, 7, 1, 12, 3, "K")
    _rect(grid, 8, 2, 10, 2, "H")
    _rect(grid, 8, 4, 5, 1, "H")
    _rect(grid, 8, 5, 1, 2, "R")
    _rect(grid, 17, 4, 1, 3, "R")

    if mood == "gap":
        # Kırgın kaşlar: içe doğru yükselir.
        for x, y in ((9, 6), (10, 6), (11, 5), (16, 6), (15, 6), (14, 5)):
            grid[(x, y)] = "K"
        _rect(grid, 10, 8, 2, 1, "K")
        _rect(grid, 14, 8, 2, 1, "K")
    elif mood in ("thinking", "watch", "repeat"):
        # Yana bakış: gözler kayar, kaşlar gözlere değmez.
        _rect(grid, 10, 5, 3, 1, "K")
        _rect(grid, 15, 5, 3, 1, "K")
        _rect(grid, 11, 7, 2, 2, "K")
        _rect(grid, 16, 7, 1, 2, "K")
    else:
        _rect(grid, 9, 5, 3, 1, "K")
        _rect(grid, 14, 5, 3, 1, "K")
        if step % 8 == 7:
            _rect(grid, 10, 8, 2, 1, "K")
            _rect(grid, 14, 8, 2, 1, "K")
        else:
            _rect(grid, 10, 7, 2, 2, "K")
            _rect(grid, 14, 7, 2, 2, "K")

    if mood == "talking":
        if step % 2:
            _rect(grid, 11, 10, 4, 2, "M")
        else:
            _rect(grid, 12, 10, 3, 1, "K")
    elif mood in ("gap", "carried"):
        _rect(grid, 11, 10, 4, 1, "K")
        grid[(10, 11)] = "K"
        grid[(15, 11)] = "K"
    else:
        # Kendinden emin yarım gülüş; yana bakarken göze değmemesi için köşesiz.
        _rect(grid, 11, 10, 5, 1, "K")
        if mood not in ("thinking", "watch", "repeat"):
            grid[(16, 9)] = "K"


def _torso(grid: Grid) -> None:
    _rect(grid, 11, 13, 4, 1, "S")
    _outlined(grid, 6, 14, 14, 11, "N")
    _rect(grid, 11, 15, 4, 4, "W")
    _rect(grid, 10, 15, 1, 5, "L")
    _rect(grid, 15, 15, 1, 5, "L")
    _rect(grid, 12, 15, 2, 1, "T")
    _rect(grid, 12, 16, 2, 6, "T")
    _rect(grid, 8, 17, 2, 1, "W")


def _legs(grid: Grid, mood: str, step: int) -> None:
    left, right = 0, 0
    if mood == "walk":
        left, right = (-1, 1) if step % 2 else (1, -1)
    lift = 2 if mood == "carried" and step % 2 else 0
    _outlined(grid, 8 + left, 25, 4, 6 - lift, "P")
    _outlined(grid, 14 + right, 25, 4, 6 - (2 - lift if mood == "carried" else 0), "P")
    _rect(grid, 7 + left, 30 - lift, 5, 2, "K")
    _rect(grid, 14 + right, 30 - (2 - lift if mood == "carried" else 0), 5, 2, "K")


def _briefcase_arm(grid: Grid, mood: str, step: int) -> None:
    if mood == "carried":
        _outlined(grid, 3, 11, 4, 8, "N")
        _rect(grid, 4, 9, 2, 2, "S")
        return
    swing = 1 if mood == "walk" and step % 2 else 0
    _outlined(grid, 3, 15, 4, 9, "N")
    _rect(grid, 4, 24, 2, 2, "S")
    _rect(grid, 2 + swing, 25, 3, 1, "K")
    _outlined(grid, 0 + swing, 26, 7, 6, "C")
    _rect(grid, 3 + swing, 27, 1, 2, "G")


def _free_arm(grid: Grid, mood: str, step: int) -> None:
    if mood == "talking":
        lift = step % 2
        _outlined(grid, 19, 15, 4, 5, "N")
        _outlined(grid, 21, 10 - lift, 4, 7, "N")
        _rect(grid, 22, 7 - lift, 3, 3, "S")
    elif mood == "thinking":
        _outlined(grid, 19, 15, 4, 5, "N")
        _outlined(grid, 16, 15, 6, 4, "N")
        _rect(grid, 16, 12, 3, 3, "S")
    elif mood in ("watch", "repeat"):
        _outlined(grid, 19, 15, 4, 5, "N")
        _outlined(grid, 9, 19, 13, 4, "N")
        _outlined(grid, 10, 18, 5, 5, "G")
        _rect(grid, 11, 19, 3, 3, "W")
        grid[(12, 20)] = "K"
        if mood == "repeat":
            _rect(grid, 18, 16 + step % 2 * 2, 3, 3, "S")
        else:
            _rect(grid, 7, 20, 2, 3, "S")
    elif mood == "gap":
        _outlined(grid, 19, 15, 4, 5, "N")
        _outlined(grid, 15, 15, 7, 4, "N")
        _rect(grid, 13 + step % 2, 13, 3, 3, "S")
        if step % 4 < 2:
            _rect(grid, 21, 4, 2, 3, "D")
            grid[(21, 3)] = "D"
    elif mood == "carried":
        _outlined(grid, 19, 11, 4, 8, "N")
        _rect(grid, 20, 9, 2, 2, "S")
    else:
        swing = 1 if mood == "walk" and step % 2 else 0
        _outlined(grid, 19 + swing, 15, 4, 9, "N")
        _rect(grid, 20 + swing, 24, 2, 2, "S")


def sprite(mood: str = "idle", step: int = 0, facing_left: bool = False) -> Grid:
    """İstenen ruh hali ve animasyon adımı için piksel haritasını döndürür."""
    grid: Grid = {}
    _legs(grid, mood, step)
    _briefcase_arm(grid, mood, step)
    _torso(grid)
    _head(grid, mood, step)
    _free_arm(grid, mood, step)
    if facing_left:
        return {(WIDTH - 1 - x, y): color for (x, y), color in grid.items()}
    return grid


def runs(grid: Grid) -> list[tuple[int, int, int, str]]:
    """Komşu aynı renkli pikselleri (x, y, genişlik, renk) şeritlerine birleştirir."""
    result = []
    for y in range(HEIGHT):
        x = 0
        while x < WIDTH:
            color = grid.get((x, y))
            if color is None:
                x += 1
                continue
            start = x
            while grid.get((x, y)) == color:
                x += 1
            result.append((start, y, x - start, color))
    return result
