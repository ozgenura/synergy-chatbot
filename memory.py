"""Toplantılar arası hafıza: yalnızca dokümanda bulunamayan açık maddeleri tutar.

Bu dosya bilgi kaynağı değildir; fiyat ve kurallar her zaman data/ altındaki dosyadan gelir.
Kaydı Python tutar, model hangi maddenin açık olduğuna karar vermez.
"""

import json
import os
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from rag import normalize

GAP_KINDS = {"company", "unknown", "title"}
# scripts/check_memory.py ile ölçüldü. Skorlar tek başına ayırmıyor ("Otopark ücreti" /
# "Sigorta ücreti" 0.73, gerçekten aynı konu olan bir çift 0.72), ortak anahtar kelime de aranır.
SAME_TOPIC_THRESHOLD = 0.68
GENERIC_WORDS = {"ücret", "ücreti", "fiyat", "fiyatı", "mars", "para", "nerede", "kadar", "hangi", "dahil", "imkanı", "şirket", "şirketin", "peki", "neler", "nasıl", "neden", "niye", "bunu", "şunu", "nereye"}

SimilarityFn = Callable[[str, list[str]], list[float]]


def keywords(question: str) -> set[str]:
    words = re.findall(r"\w+", normalize(question))
    return {word for word in words if len(word) >= 4 and word not in GENERIC_WORDS}


def share_keyword(first: str, second: str) -> bool:
    """Türkçe ekleri için kelime köklerini ilk 4 harfle karşılaştırır ("taksitle" / "taksit", "park" / "otopark")."""
    return any(a[:4] in b or b[:4] in a for a in keywords(first) for b in keywords(second))


def same_topic(first: str, second: str, score: float) -> bool:
    return score >= SAME_TOPIC_THRESHOLD and share_keyword(first, second)


@dataclass
class OpenGap:
    question: str
    kind: str
    first_meeting: int
    last_meeting: int
    times_asked: int = 1


class GapMemory:
    def __init__(self, path: Path):
        self.path = path
        self.meeting_count = 0
        self.gaps: list[OpenGap] = []
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.meeting_count = int(data["meeting_count"])
            self.gaps = [OpenGap(**gap) for gap in data["gaps"]]
        except (OSError, ValueError, KeyError, TypeError):
            # Dosya yoksa ya da bozuksa toplantı hafızasız başlar; cevaplar bundan etkilenmez.
            self.meeting_count = 0
            self.gaps = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"meeting_count": self.meeting_count, "gaps": [asdict(gap) for gap in self.gaps]}
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def start_meeting(self) -> None:
        self.meeting_count += 1
        self._save()

    def find(self, question: str, kind: str, similarity: SimilarityFn) -> OpenGap | None:
        """Aynı konudaki açık maddeyi bulur. Tüm yönetici soruları tek konu sayılır."""
        if kind not in GAP_KINDS or not self.gaps:
            return None
        if kind == "title":
            return next((gap for gap in self.gaps if gap.kind == "title"), None)
        candidates = [gap for gap in self.gaps if gap.kind != "title"]
        if not candidates:
            return None
        scores = similarity(question, [gap.question for gap in candidates])
        matches = [(score, gap) for score, gap in zip(scores, candidates) if same_topic(question, gap.question, score)]
        return max(matches, key=lambda pair: pair[0])[1] if matches else None

    def carried_over(self, gap: OpenGap | None) -> bool:
        return gap is not None and gap.first_meeting < self.meeting_count

    def record(self, question: str, kind: str, similarity: SimilarityFn) -> None:
        """Dokümanda bulunamayan soruyu açık maddelere ekler veya mevcut maddeyi günceller."""
        if kind not in GAP_KINDS or (kind != "title" and not keywords(question)):
            # "neler dahil?" gibi konusu olmayan sorular kalıcı listeye yazılmaz.
            return
        gap = self.find(question, kind, similarity)
        if gap is None:
            self.gaps.append(OpenGap(question, kind, self.meeting_count, self.meeting_count))
        else:
            gap.times_asked += 1
            gap.last_meeting = self.meeting_count
        self._save()

    def carried_gaps(self) -> list[OpenGap]:
        """Önceki toplantılardan gelen açık maddeler."""
        return [gap for gap in self.gaps if gap.first_meeting < self.meeting_count]

    def reset(self) -> None:
        self.meeting_count = 0
        self.gaps = []
        self.path.unlink(missing_ok=True)
