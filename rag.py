"""Mars Turizm bilgi dosyasını satırlara böler ve soruya en ilgili satırları seçer.

İki sinyal birleştirilir:
- bge-m3 embedding: anlam benzerliği ("kedim" -> "evcil hayvan")
- karakter n-gram TF-IDF: Türkçe ekleri tolere eden kelime eşleşmesi ("çayın" -> "çay")
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import ollama
from sklearn.feature_extraction.text import TfidfVectorizer

EMBED_MODEL = "bge-m3"
TOP_K = 3
# scripts/check_retrieval.py ile ölçüldü. Eşik yalnızca bariz konu dışı soruları eler:
# skorlar "dosyada var/yok" ayrımını yapamıyor ("wifi" 0.52, "genel merkez" 0.59).
# Satırların soruyu gerçekten cevaplayıp cevaplamadığına model karar verir.
EMBED_THRESHOLD = 0.50
TFIDF_THRESHOLD = 0.18
CONFIDENT_EMBED = 0.60
CONFIDENT_TFIDF = 0.30


def normalize(text: str) -> str:
    """Türkçe büyük/küçük harf dönüşümünü doğru yapar (İ->i, I->ı)."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def load_chunks(path: Path) -> list[str]:
    """Her bilgi satırı bir parçadır; başlık satırı atlanır."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines[1:] if line.strip()]


@dataclass
class Hit:
    text: str
    embed_score: float
    tfidf_score: float

    @property
    def relevant(self) -> bool:
        return self.embed_score >= EMBED_THRESHOLD or self.tfidf_score >= TFIDF_THRESHOLD

    @property
    def confident(self) -> bool:
        """Modelin aşırı temkinli "veri yok" demesini önlemek için güçlü eşleşme işareti."""
        return self.embed_score >= CONFIDENT_EMBED or self.tfidf_score >= CONFIDENT_TFIDF


class Retriever:
    def __init__(self, path: Path, client: ollama.Client | None = None):
        self.client = client or ollama.Client()
        self.chunks = load_chunks(path)
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), preprocessor=normalize)
        self.tfidf = self.vectorizer.fit_transform(self.chunks)
        self.embeddings = self._embed(self.chunks)

    def _embed(self, texts: list[str]) -> np.ndarray:
        response = self.client.embed(model=EMBED_MODEL, input=texts, keep_alive="30m")
        vectors = np.array(response["embeddings"])
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def similarities(self, question: str, texts: list[str]) -> list[float]:
        return (self._embed(texts) @ self._embed([question])[0]).tolist()

    def search(self, question: str, k: int = TOP_K, skip_slogan: bool = False) -> list[Hit]:
        embed_scores = self.embeddings @ self._embed([question])[0]
        tfidf_scores = (self.tfidf @ self.vectorizer.transform([question]).T).toarray().ravel()
        hits = [Hit(c, float(e), float(t)) for c, e, t in zip(self.chunks, embed_scores, tfidf_scores)]
        if skip_slogan:
            hits = [hit for hit in hits if "slogan" not in normalize(hit.text)]
        hits.sort(key=lambda h: max(h.embed_score, h.tfidf_score), reverse=True)
        return hits[:k]
