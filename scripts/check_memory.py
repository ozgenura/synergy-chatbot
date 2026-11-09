"""Hafıza konu eşiğini ölçer ve iki toplantılık akışı gerçek modelle dener."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ollama  # noqa: E402

from llm import answer_turn  # noqa: E402
from meeting import Meeting  # noqa: E402
from memory import GapMemory, same_topic  # noqa: E402
from rag import Retriever  # noqa: E402

DATA_PATH = ROOT / "data" / "mars_turizm.txt"

SAME_TOPIC = [
    ("Seyahat sigortası dahil mi?", "Sigorta var mı?"),
    ("Şirketin genel merkezi nerede?", "Genel merkeziniz neresi?"),
    ("Taksit imkanı var mı?", "Taksitle ödeyebilir miyim?"),
    ("Sigorta var mı?", "Yolculuk için sigorta yapılıyor mu?"),
    ("Otopark ücreti ne kadar?", "Arabamı park etmek kaç para?"),
    ("Mars'a hangi roketle gidiliyor?", "Yolculukta hangi roket kullanılıyor?"),
]
DIFFERENT_TOPIC = [
    ("Seyahat sigortası dahil mi?", "Taksit imkanı var mı?"),
    ("Şirketin genel merkezi nerede?", "Mars'a hangi roketle gidiliyor?"),
    ("Taksit imkanı var mı?", "Otopark ücreti ne kadar?"),
    ("Sigorta var mı?", "Otopark var mı?"),
    ("Taksit var mı?", "Sigorta var mı?"),
    ("Şirketin genel merkezi nerede?", "Uzay limanı nerede?"),
    ("Otopark ücreti ne kadar?", "Sigorta ücreti ne kadar?"),
]
QUESTIONS = ["Mars Turizm'in CEO'su kim?", "Seyahat sigortası dahil mi?", "Sigorta var mı?", "Mars'ta çay ne kadar?"]


def ask(retriever: Retriever, client: ollama.Client, knowledge: str, memory: GapMemory, question: str) -> None:
    item = answer_turn(client, retriever, knowledge, question, Meeting(), [], memory)
    print(f"[{memory.meeting_count}. toplantı | {item.kind} | gap={item.is_gap}] {question}\n  {item.answer}\n")


def main() -> None:
    client = ollama.Client()
    retriever = Retriever(DATA_PATH, client)
    knowledge = DATA_PATH.read_text(encoding="utf-8")
    for label, pairs, expected in (("aynı konu", SAME_TOPIC, True), ("farklı konu", DIFFERENT_TOPIC, False)):
        for first, second in pairs:
            score = retriever.similarities(first, [second])[0]
            verdict = "OK" if same_topic(first, second, score) == expected else "XX"
            print(f"{verdict} {label}: {score:.2f} | {first} / {second}")
    print()
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "open_gaps.json"
        for _ in range(2):
            memory = GapMemory(path)
            memory.start_meeting()
            for question in QUESTIONS[:2] if memory.meeting_count == 1 else QUESTIONS:
                ask(retriever, client, knowledge, memory, question)
        print("Açık maddeler:", [(g.question, g.times_asked) for g in GapMemory(path).gaps])


if __name__ == "__main__":
    main()
