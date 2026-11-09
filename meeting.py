"""Toplantı katmanı: cevap kontrolü, tekrar soru tespiti, panel metrikleri ve tutanak."""

import random
import re
from dataclasses import dataclass, field

from persona import CLOSING_KINDS, CLOSINGS
from rag import normalize

JARGON = [
    "bottom line", "stakeholder", "engagement", "pilot", "rollout", "blocker", "slot", "gündem",
    "yönetim kurulu", "vizyon", "strateji", "kpi", "mindset", "portföy", "paydaş", "verimlilik",
]
NUMBER_PATTERN = re.compile(r"\d[\d.,:]*\d|\d")
FORBIDDEN_PATTERN = re.compile(r"\bceo", re.IGNORECASE)
LEAK_PATTERN = re.compile(r"kaynak\s*:|kaynak satır|talimat", re.IGNORECASE)
GAP_PATTERN = re.compile(r"dokümanda (yok|mevcut değil|bulunm)|belirtilmemiş")
BOTTOM_LINE_PATTERN = re.compile(r"^[*_\s]*bottom line[*_\s]*:?[*_\s]*", re.IGNORECASE)


QUESTION_SCORES = {"chat": 20, "self": 20, "personal": 20, "help": 50, "relocation": 75, "opinion": 75, "trip": 85}


def numbers_in(text: str) -> set[str]:
    return {re.sub(r"[.,:]", "", n) for n in NUMBER_PATTERN.findall(text)}


def check_answer(answer: str, knowledge: str, question: str) -> list[str]:
    """Kurallara aykırılıkları döndürür; boş liste cevabın temiz olduğu anlamına gelir."""
    problems = []
    invented = numbers_in(answer) - numbers_in(knowledge) - numbers_in(question)
    if invented:
        problems.append(f"Kaynakta olmayan sayılar yazdın: {', '.join(sorted(invented))}. Bu sayıları çıkar.")
    if FORBIDDEN_PATTERN.search(answer):
        problems.append('"CEO" kelimesini yazdın. Onun yerine "bu pozisyon" de ve kendine unvan verme.')
    if LEAK_PATTERN.search(answer):
        problems.append('"KAYNAK" veya "talimat" kelimesini yazdın. Bunları cevaptan çıkar.')
    return problems


def ensure_bottom_line(answer: str) -> str:
    """Her cevabın aynı kalın etiketle başlamasını sağlar."""
    body = BOTTOM_LINE_PATTERN.sub("", answer.strip(), count=1).strip()
    return f"**Bottom line:** {body}"


def first_sentence(answer: str) -> str:
    """Tutanak için "Bottom line" cümlesini çıkarır; sayılardaki noktaları bölmez."""
    clean = answer.replace("**", "").strip()
    clean = re.sub(r"^bottom line:\s*", "", clean, flags=re.IGNORECASE)
    match = re.match(r".+?[.!?](?=\s|$)", clean, flags=re.DOTALL)
    return (match.group(0) if match else clean).strip()


def question_key(question: str) -> str:
    return " ".join(re.findall(r"\w+", normalize(question)))


@dataclass
class AgendaItem:
    question: str
    answer: str
    kind: str
    sources: list[str]
    repeated: bool = False
    corrected: bool = False

    @property
    def is_gap(self) -> bool:
        # Model ret cümlesini bazen farklı kurar; karar yalnızca ilk cümleye bakılarak verilir.
        return bool(GAP_PATTERN.search(normalize(first_sentence(self.answer))))

    @property
    def score(self) -> int:
        """Sorunun gündeme katkısı. Şaka amaçlıdır; kurala bağlıdır, model üretmez."""
        if self.kind == "injection":
            return 0
        if self.is_gap:
            return 40
        if self.repeated:
            return 15
        return QUESTION_SCORES.get(self.kind, 90)

    @property
    def stamp(self) -> tuple[str, str]:
        """Defter görünümündeki damganın metni ve rengi."""
        if self.kind == "injection":
            return "TALEP REDDEDİLDİ", "red"
        if self.is_gap:
            return "VERİ GAP'İ", "red"
        if self.repeated:
            return "MADDE KAPANDI", "blue"
        if self.kind == "help":
            return "GÜNDEM SUNULDU", "gray"
        if self.kind in ("chat", "self", "personal"):
            return "NOT ALINDI", "gray"
        return "KARAR ALINDI", "green"


@dataclass
class Meeting:
    items: list[AgendaItem] = field(default_factory=list)
    closings: list[str] = field(default_factory=list)

    def next_closing(self, kind: str) -> str:
        """Kapanışları karışık sırayla tüketir; havuz bitmeden aynı cümle tekrar etmez."""
        if kind not in CLOSING_KINDS:
            return ""
        if not self.closings:
            self.closings = random.sample(CLOSINGS, len(CLOSINGS))
        return self.closings.pop()

    def is_repeat(self, question: str) -> bool:
        key = question_key(question)
        return any(question_key(item.question) == key for item in self.items)

    def add(self, item: AgendaItem) -> None:
        self.items.append(item)

    @property
    def efficiency(self) -> int:
        return round(sum(item.score for item in self.items) / len(self.items)) if self.items else 0

    def metrics(self) -> dict[str, int]:
        answers = " ".join(normalize(item.answer) for item in self.items)
        return {
            "Gündem maddesi": len(self.items),
            "Dokümandan yanıtlanan": sum(1 for i in self.items if i.sources and not i.is_gap and i.kind != "chat"),
            "Tespit edilen veri gap'i": sum(1 for i in self.items if i.is_gap),
            "Tekrar açılan madde": sum(1 for i in self.items if i.repeated),
            "Kullanılan jargon": sum(answers.count(term) for term in JARGON),
        }

    def minutes(self, carried_questions: list[str] | None = None) -> str:
        """Tutanak yalnızca konuşma kaydından ve açık maddelerden üretilir, LLM'e yazdırılmaz."""
        lines = ["# TOPLANTI TUTANAĞI", ""]
        for number, item in enumerate(self.items, start=1):
            status = "Veri gap'i" if item.is_gap else "Kapatıldı"
            lines += [f"**Madde {number}:** {item.question}", f"- Karar: {first_sentence(item.answer)}", f"- Durum: {status}", f"- Soru KPI: {item.score}/100", ""]
        lines += [f"**Toplantı verimi:** {self.efficiency}/100", ""]
        if carried_questions:
            lines += ["**Önceki toplantılardan devreden açık maddeler:**", *[f"- {question}" for question in carried_questions], ""]
        return "\n".join(lines).strip()
