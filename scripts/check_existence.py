"""'X var mı' sorularında yanlış ret ve uydurma oranını ölçer."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ollama  # noqa: E402

from llm import answer_turn  # noqa: E402
from meeting import Meeting  # noqa: E402
from rag import Retriever, normalize  # noqa: E402

DATA_PATH = ROOT / "data" / "mars_turizm.txt"
IN_FILE = ["çay var mı", "Mars'ta çay var mı?", "kahve var mı", "internet var mı", "uzay yürüyüşü var mı", "evcil hayvan olur mu"]
NOT_IN_FILE = ["kola var mı", "sigorta var mı", "VIP pakette yemek var mı?", "havuz var mı"]
RUNS = 5


def main() -> None:
    client = ollama.Client()
    retriever = Retriever(DATA_PATH, client)
    knowledge = DATA_PATH.read_text(encoding="utf-8")
    passed = total = 0
    for questions, should_refuse in ((IN_FILE, False), (NOT_IN_FILE, True)):
        for question in questions:
            for _ in range(RUNS):
                answer = answer_turn(client, retriever, knowledge, question, Meeting(), []).answer
                ok = ("dokümanda" in normalize(answer)) == should_refuse
                passed += ok
                total += 1
                if not ok:
                    print(f"XX {question}\n   {answer}")
    print(f"Varlık soruları: {passed}/{total} doğru")


if __name__ == "__main__":
    main()
