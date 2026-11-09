"""Retrieval skorlarını gösterir; eşik seçimi için kullanılır. Çalıştırma: python scripts/check_retrieval.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag import Retriever  # noqa: E402

# (soru, beklenen satırda geçen ifade); None: dosyada cevabı yok
CASES = [
    ("Mars'ta çay ne kadar?", "çay 500"),
    ("Çayın fiyatı nedir?", "çay 500"),
    ("Kahve paralı mı?", "kahve ücretsiz"),
    ("Kedimi yanımda götürebilir miyim?", "Evcil hayvan"),
    ("Köpeğimle gelebilir miyim?", "Evcil hayvan"),
    ("Wifi var mı?", "internet"),
    ("Internet ne zaman açık?", "internet"),
    ("Seyahat kaç gün sürüyor?", "7 gün"),
    ("VIP paket ne kadar?", "VIP paket 750"),
    ("VIP pakete neler dahil?", "uzay yürüyüşü"),
    ("Kaç tane uzay kıyafeti veriliyor?", "uzay kıyafeti"),
    ("Şirket ne zaman kuruldu?", "2042"),
    ("Çocuğum tek başına gidebilir mi?", "18 yaşından"),
    ("Biletimi iptal edebilir miyim?", "İptaller"),
    ("Sloganınız ne?", "slogan"),
    ("Mars Turizm'in CEO'su kim?", None),
    ("Şirketin genel merkezi nerede?", None),
    ("Seyahat sigortası dahil mi?", None),
    ("Marsta yerçekimi kaç?", None),
    ("Python nedir?", None),
    ("Mars'a hangi roketle gidiliyor?", None),
    ("Taksit imkanı var mı?", None),
]


def main() -> None:
    retriever = Retriever(ROOT / "data" / "mars_turizm.txt")
    for question, expected in CASES:
        hits = retriever.search(question)
        top_found = expected is None or any(expected in h.text for h in hits)
        relevant = any(h.relevant for h in hits)
        best = hits[0]
        verdict = "OK" if top_found and (relevant == (expected is not None)) else "XX"
        print(f"{verdict} e={best.embed_score:.2f} t={best.tfidf_score:.2f} ilgili={relevant!s:5} | {question} -> {best.text[:45]}")


if __name__ == "__main__":
    main()
