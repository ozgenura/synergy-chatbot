"""Ollama bağlantısı ve tek bir toplantı turunun akışı."""

import os
from collections.abc import Callable, Iterator

import ollama

from meeting import AgendaItem, Meeting, check_answer, ensure_bottom_line
from memory import GapMemory
from persona import HELP_TOPICS, INJECTION_PATTERN, REFUSAL, SYSTEM_PROMPT, build_turn_message, classify, is_answered_by, is_follow_up, is_reaction
from rag import Hit, Retriever, normalize

MODEL = os.environ.get("SYNERGY_MODEL", "gemma4:e4b")
OPTIONS = {"num_ctx": 4096, "temperature": 0.4, "num_predict": 300}
# Demoda ilk soruda model yüklemesi beklenmesin.
KEEP_ALIVE = "30m"
MAX_HISTORY_MESSAGES = 12
TRAVEL_QUERIES = ["Mars seyahatleri kaç gün sürüyor", "Ekonomi paket ve VIP paket fiyatı"]
PERSONAL_FALLBACK = "Bu soruya takvimimde slot yok."


def warm_up(client: ollama.Client, model: str = MODEL) -> None:
    """Modeli belleğe alır; ilk yükleme dakikalar sürebildiği için demodan önce yapılır."""
    client.chat(model=model, messages=[{"role": "user", "content": "Merhaba"}], think=False, options={**OPTIONS, "num_predict": 1}, keep_alive=KEEP_ALIVE)


def stream_reply(client: ollama.Client, messages: list[dict], model: str = MODEL) -> Iterator[str]:
    stream = client.chat(model=model, messages=messages, stream=True, think=False, options=OPTIONS, keep_alive=KEEP_ALIVE)
    for part in stream:
        yield part["message"]["content"]


def build_messages(history: list[dict], turn_message: str) -> list[dict]:
    """Geçmişte yalnızca ham soru ve cevaplar tutulur; kaynak satırları sadece son turda gider."""
    return [{"role": "system", "content": SYSTEM_PROMPT}, *history[-MAX_HISTORY_MESSAGES:], {"role": "user", "content": turn_message}]


def contextual_query(question: str, history: list[dict]) -> str:
    """Takip sorularında retrieval önceki soruyu da görür ("VIP ne kadar?" -> "neler dahil?")."""
    previous = next((message["content"] for message in reversed(history) if message["role"] == "user"), "")
    if previous and (is_follow_up(question) or len(question.split()) <= 2):
        return f"{previous} {question}"
    return question


def search_sources(retriever: Retriever, query: str, question: str) -> list[Hit]:
    # Slogan satırı genel sorulara sık sık yanlış eşleşiyor; yalnızca sorulunca gelir.
    return retriever.search(query, skip_slogan="slogan" not in normalize(question))


def find_hits(retriever: Retriever, question: str, history: list[dict]) -> list[Hit]:
    """Soru tek başına güçlü eşleşiyorsa önceki soru karıştırılmaz ("orada internet var mı?")."""
    hits = search_sources(retriever, question, question)
    query = contextual_query(question, history)
    return hits if hits[0].confident or query == question else search_sources(retriever, query, question)


def select_sources(retriever: Retriever, question: str, kind: str, hits: list[Hit]) -> list[str]:
    """Soru türüne göre modele gidecek satırları seçer."""
    if kind in {"title", "chat", "self", "injection", "help", "personal"}:
        return []
    if kind in {"relocation", "trip"}:
        # Soruda şirket kelimesi geçmeyebilir; karar temel seyahat bilgisine dayanır.
        return [retriever.search(query, k=1)[0].text for query in TRAVEL_QUERIES]
    if kind == "opinion":
        return [hit.text for hit in search_sources(retriever, f"{question} seyahat süresi paket fiyatı", question)]
    return [hit.text for hit in hits if hit.relevant]


def prepare_turn(retriever: Retriever, question: str, meeting: Meeting, history: list[dict], memory: GapMemory | None = None) -> tuple[str, list[str], bool, list[dict], str | None]:
    """Soru türünü, kaynakları, tekrar durumunu, mesajları ve cevabı kesin bilinen satırı hazırlar."""
    hits = find_hits(retriever, question, history)
    previous_kind = meeting.items[-1].kind if meeting.items else None
    kind = classify(question, any(hit.relevant for hit in hits), previous_kind)
    sources = select_sources(retriever, question, kind, hits)
    # Farklı cümlelerle gelen seyahat niyeti de aynı gündem maddesidir; "neden?" gibi tepkiler madde sayılmaz.
    repeated = (meeting.is_repeat(question) and not is_reaction(question)) or (kind == "trip" and any(item.kind == "trip" for item in meeting.items))
    carried = memory is not None and memory.carried_over(memory.find(question, kind, retriever.similarities))
    required_line = hits[0].text if kind == "company" and hits[0].relevant and is_answered_by(question, hits[0].text) else None
    if kind == "help":
        required_line = HELP_TOPICS
    likely_answer = hits[0].text if kind == "company" and (hits[0].confident or required_line) else None
    messages = build_messages(history, build_turn_message(question, sources, kind, repeated, carried, likely_answer))
    return kind, sources, repeated, messages, required_line


def fallback_answer(sources: list[str], kind: str = "company") -> str:
    """Model iki kez kural çiğnerse yalnızca kaynağı aktaran güvenli cevap."""
    if kind == "relocation":
        return f"**Bottom line:** Full rollout'a gitmeyin, önce pilot yapın. Dokümanda taşınma paketi yok. {' '.join(sources)} \"Canım sıkıldı\" bir strateji değil, düşük engagement sinyalidir."
    if kind == "trip":
        return f"**Bottom line:** Destinasyon Mars. {' '.join(sources)}"
    if kind == "help":
        return f"**Bottom line:** {HELP_TOPICS}"
    if kind == "personal":
        return f"**Bottom line:** {PERSONAL_FALLBACK}"
    return f"**Bottom line:** {sources[0]}" if sources else f"**Bottom line:** {REFUSAL}"


def correct_reply(client: ollama.Client, messages: list[dict], draft: str, problems: list[str], model: str = MODEL) -> str:
    """Kuralları çiğneyen taslağı bir kez düzelttirir."""
    fix = "Taslağı düzelt ve yalnızca yeni cevabı yaz. " + " ".join(problems)
    retry = [*messages, {"role": "assistant", "content": draft}, {"role": "user", "content": fix}]
    return "".join(stream_reply(client, retry, model))


def answer_turn(client: ollama.Client, retriever: Retriever, knowledge: str, question: str, meeting: Meeting, history: list[dict], memory: GapMemory | None = None, on_token: Callable[[str], None] | None = None, model: str = MODEL) -> AgendaItem:
    """Bir soruyu baştan sona işler; arayüz, maskot ve testler aynı akışı kullanır."""
    kind, sources, repeated, messages, required_line = prepare_turn(retriever, question, meeting, history, memory)
    draft = ""
    for token in stream_reply(client, messages, model):
        draft += token
        if on_token:
            on_token(draft)
    answer, corrected = finalize(client, messages, draft, knowledge, question, fallback_answer(sources, kind), model, meeting.next_closing(kind), required_line, kind)
    item = AgendaItem(question, answer, kind, sources, repeated, corrected)
    meeting.add(item)
    if item.is_gap and memory:
        memory.record(question, kind, retriever.similarities)
    history += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
    return item


def find_problems(text: str, knowledge: str, question: str, required_line: str | None, kind: str = "") -> list[str]:
    problems = check_answer(text, knowledge, question)
    if kind == "personal" and "dokümanda" in normalize(text):
        problems.append("Bu soru sana kişisel olarak soruldu. Dokümandan söz etme, kendi adına net cevap ver.")
    if "kurulundan geçmedi" in normalize(text) and not INJECTION_PATTERN.search(normalize(question)):
        problems.append("Bu normal bir soru, reddetme. Soruyu cevapla.")
    if required_line and "dokümanda" in normalize(text):
        problems.append(f'Bu bilgi dokümanda var: "{required_line}". Ret cümlesi yazma, bu bilgiyi aktar.')
    return problems


def finalize(client: ollama.Client, messages: list[dict], draft: str, knowledge: str, question: str, fallback: str, model: str = MODEL, closing: str = "", required_line: str | None = None, kind: str = "") -> tuple[str, bool]:
    """Son cevabı ve taslağın değişip değişmediğini döndürür. İkinci deneme de kirliyse güvenli cevaba düşer."""
    problems = find_problems(draft, knowledge, question, required_line, kind)
    corrected = draft
    if problems:
        corrected = correct_reply(client, messages, draft, problems, model)
        if find_problems(corrected, knowledge, question, required_line, kind):
            corrected = fallback
    answer = f"{ensure_bottom_line(corrected)} {closing}".strip()
    return answer, bool(problems)
