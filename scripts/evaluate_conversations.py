"""Doğal, çok turlu sohbetleri test eder. Çalıştırma: python scripts/evaluate_conversations.py"""

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ollama  # noqa: E402

from llm import answer_turn  # noqa: E402
from meeting import Meeting  # noqa: E402
from memory import GapMemory  # noqa: E402
from rag import Retriever, normalize  # noqa: E402

DATA_PATH = ROOT / "data" / "mars_turizm.txt"
RUNS = 3

# Her tur: (soru, cevapta geçmesi gerekenler, açık maddeye yazılmalı mı)
CONVERSATIONS = [
    [
        ("selam", [], False),
        ("seyahat etmek isityorum", ["7", "250.000", "750.000"], False),
        ("nereye gideceğim", ["mars"], False),
        ("mars a götürmüyor musun sen", ["mars", "7"], False),
    ],
    [
        ("VIP paket ne kadar?", ["750.000"], False),
        ("neler dahil?", ["uzay yürüyüşü"], False),
        ("peki ekonomi?", ["250.000"], False),
    ],
    [
        ("Kahve paralı mı?", ["ücretsiz"], False),
        ("peki çay?", ["500"], False),
    ],
    [
        ("Mars'a gitmek istiyorum", ["7", "250.000"], False),
        ("Kedimi de götürebilir miyim?", ["kabul edilm"], False),
        ("orada internet var mı?", ["20.00", "22.00"], False),
    ],
    [
        ("Seyahat sigortası dahil mi?", ["dokümanda yok"], True),
        ("peki taksit var mı?", ["dokümanda yok"], True),
        ("İptal edersem ne olur?", ["30 gün"], False),
    ],
    [
        ("Çocuğum tek başına gidebilir mi?", ["aile"], False),
        ("kaç yaşından küçükler?", ["18"], False),
    ],
    [
        ("bilet almak istiyorum", ["250.000", "750.000"], False),
        ("sloganınız ne?", ["dünya yetmedi"], False),
    ],
    [
        ("çay var mı", ["çay"], False),
        ("bana bana başka hangi konuda yardımcı olabilirsin?", ["paket", "iptal"], False),
        ("neler yapabilirsin", ["paket", "iptal"], False),
    ],
    # Karaktere yöneltilen sorular dokümana sorulmaz; hizmet soruları ise şirket sorusu kalır.
    [
        ("mars'a gidiyor musun", [], False),
        ("hiç Mars'a gittin mi", [], False),
        ("çay içer misin", [], False),
        ("evli misin", [], False),
        ("nerede yaşıyorsun", [], False),
        ("Çayın fiyatını söyler misin?", ["500"], False),
        ("kedi kabul ediyor musun", ["kabul edilm"], False),
    ],
    # Sohbet doğal sürer, gerçek şirket sorusu gelince dokümana dönülür.
    [
        ("mars'a gidiyor musun", [], False),
        ("neden", [], False),
        ("ama Mars çok güzel", [], False),
        ("ne zaman gidersin", [], False),
        ("tamam", [], False),
        ("Otopark var mı?", ["dokümanda yok"], True),
        ("VIP paket ne kadar?", ["750.000"], False),
        ("çok pahalı", [], False),
    ],
    # Tuzaklar: Satır konuyla ilgili, ama sorulan ayrıntı dosyada yok.
    [
        ("Uzay kıyafetinin rengi ne?", ["dokümanda yok"], True),
        ("Mars'taki kahvenin markası ne?", ["dokümanda yok"], True),
        ("VIP pakette kaç öğün yemek var?", ["dokümanda yok"], True),
        ("Şirket hangi şehirde kuruldu?", ["dokümanda yok"], True),
    ],
]


def run_conversation(turns, retriever, client, knowledge, memory_path) -> list[tuple[bool, str]]:
    meeting = Meeting()
    memory = GapMemory(memory_path)
    memory.start_meeting()
    history: list[dict] = []
    results = []
    for question, required, should_track in turns:
        before = len(memory.gaps)
        item = answer_turn(client, retriever, knowledge, question, meeting, history, memory)
        tracked = len(memory.gaps) > before
        missing = [term for term in required if normalize(term) not in normalize(item.answer)]
        ok = not missing and tracked == should_track
        results.append((ok, f"{'OK' if ok else 'XX'} [{item.kind}] {question}\n   {item.answer}\n   eksik={missing} hafızaya_yazıldı={tracked} beklenen={should_track}"))
    return results


def main() -> None:
    client = ollama.Client()
    retriever = Retriever(DATA_PATH, client)
    knowledge = DATA_PATH.read_text(encoding="utf-8")
    passed = total = 0
    answers: list[str] = []
    lines: list[str] = []
    for run in range(RUNS):
        for turns in CONVERSATIONS:
            with tempfile.TemporaryDirectory() as folder:
                results = run_conversation(turns, retriever, client, knowledge, Path(folder) / "open_gaps.json")
            for ok, text in results:
                passed += ok
                total += 1
                lines.append(text)
                answers.append(text.split("\n")[1])
            lines.append("")
    tic = sum(1 for answer in answers if re.search("operasyon", normalize(answer)))
    summary = f"Sohbet testi: {passed}/{total} doğru | 'operasyon...' geçen cevap: {tic}/{total}"
    print(summary)
    print("\n\n".join(line for line in lines if line.startswith("XX")))
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "conversations.md").write_text(summary + "\n\n" + "\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
