"""Panel açılınca devreye giren kurul dosyası görünümü. Renkler maskotla aynı paletten gelir."""

from html import escape

from meeting import AgendaItem, first_sentence

BASE_CSS = """<style>
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"] { display: none; }
</style>"""

# Windows'un kendi fontları kullanılır; demoda internet gerekmez.
NOTEBOOK_CSS = """<style>
:root { --navy: #1f2d45; --paper: #fbfaf7; --red: #c8323c; --gold: #8a7440; --gold-light: #d9b45b; --serif: Cambria, Georgia, serif; --sans: "Segoe UI", sans-serif; }
.stApp, [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background: var(--paper); }
[data-testid="stMainBlockContainer"] { max-width: 780px; padding-top: 48px; color: var(--navy); font-family: var(--sans); }
[data-testid="stMainBlockContainer"] p, [data-testid="stMainBlockContainer"] li { color: var(--navy); }
[data-testid="stMainBlockContainer"] h1, [data-testid="stMainBlockContainer"] h2, [data-testid="stMainBlockContainer"] h3 { color: var(--navy); font-family: var(--serif); font-weight: 400; }
[data-testid="stSidebar"] { background: var(--navy); }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #e8ecf3; }
[data-testid="stSidebar"] strong { color: var(--gold-light); letter-spacing: .14em; font-weight: 400; }
[data-testid="stSidebar"] [data-testid="stMetricLabel"] p { color: #aab6c9; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #ffffff; font-family: var(--serif); }
[data-testid="stSidebar"] button { background: transparent; border: 1px solid #4a5b78; color: #e8ecf3; border-radius: 2px; }
[data-testid="stSidebar"] button:hover { border-color: var(--gold-light); color: var(--gold-light); }
[data-testid="stSidebar"] button:disabled, [data-testid="stSidebar"] button:disabled p { color: #728098; }
[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"] span { border: none; color: #aab6c9; }
[data-testid="stChatInput"] { max-width: 780px; margin: auto; border: 1px solid var(--navy); border-radius: 2px; background: #ffffff; }
[data-testid="stAlert"] > div { background: #f3efe4; border-radius: 2px; color: var(--navy); }
[data-testid="stAlert"] p { color: var(--navy); font-family: var(--serif); }
[data-testid="stDownloadButton"] button { background: transparent; border: 1px solid var(--navy); color: var(--navy); border-radius: 2px; }
.nb-title { font-family: var(--serif); font-size: 2.7rem; line-height: 1.15; }
.nb-subtitle { font-size: .82rem; letter-spacing: .16em; color: var(--gold); border-bottom: 1.5px solid var(--navy); padding-bottom: 12px; margin-bottom: 8px; }
.nb-item { padding: 22px 0 18px; border-bottom: 1px solid #ddd8ca; }
.nb-number { display: block; font-size: .8rem; letter-spacing: .13em; color: var(--gold); }
.nb-question { font-family: var(--serif); font-size: 1.45rem; line-height: 1.3; }
.nb-answer { font-size: 1.03rem; line-height: 1.65; margin-top: 10px; padding-left: 14px; border-left: 3px solid var(--red); }
.nb-answer strong { font-weight: 600; }
.nb-footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 12px; }
.nb-note { font-size: .78rem; color: #6d7482; }
.nb-result { flex: none; display: flex; align-items: center; gap: 12px; }
.nb-score { font-family: var(--serif); font-size: 1.05rem; white-space: nowrap; }
.nb-score small { font-family: var(--sans); font-size: .68rem; letter-spacing: .12em; color: var(--gold); margin-right: 5px; }
.nb-stamp { font-size: .76rem; letter-spacing: .1em; padding: 3px 10px; border: 1px solid currentColor; white-space: nowrap; }
.nb-new .nb-result { animation: nb-appear .45s ease-out; }
.nb-red { color: var(--red); } .nb-green { color: #2f6b4f; } .nb-blue { color: var(--navy); } .nb-gray { color: #6d7482; }
.nb-signature { font-family: var(--serif); font-style: italic; font-size: 1.35rem; text-align: right; margin: 26px 0 4px; }
.nb-signature span { display: inline-block; min-width: 190px; border-top: 1px solid var(--navy); padding-top: 6px; }
@keyframes nb-appear { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }
</style>"""

HEADER_HTML = '<div class="nb-title">Synergy</div><div class="nb-subtitle">YÖNETİM KURULU GÜNDEMİ</div>'
SIGNATURE_HTML = '<div class="nb-signature"><span>Synergy</span></div>'


def question_html(number: int, question: str) -> str:
    return f'<div class="nb-question"><span class="nb-number">MADDE {number:02d}</span>{escape(question)}</div>'


def _answer_html(answer: str) -> str:
    """İlk cümle karar olarak vurgulanır. Model çıktısı HTML olarak yorumlanmaz."""
    decision = first_sentence(answer)
    clean = answer.replace("**", "").strip()
    rest = clean.split(decision, 1)[-1].strip()
    return f"<strong>Bottom line: {escape(decision)}</strong> {escape(rest)}"


def opening_html(text: str) -> str:
    return f'<div class="nb-item"><span class="nb-number">AÇILIŞ NOTU</span><div class="nb-answer">{_answer_html(text)}</div></div>'


def agenda_html(number: int, item: AgendaItem, newest: bool = False) -> str:
    text, tone = item.stamp
    note = f"Dipnot: {escape(' · '.join(item.sources))}" if item.sources else "Dipnot: Kaynak satır yok."
    new_class = " nb-new" if newest else ""
    return (
        f'<div class="nb-item{new_class}">{question_html(number, item.question)}'
        f'<div class="nb-answer">{_answer_html(item.answer)}</div>'
        f'<div class="nb-footer"><span class="nb-note">{note}</span><span class="nb-result">'
        f'<span class="nb-score"><small>KPI</small>{item.score}/100</span>'
        f'<span class="nb-stamp nb-{tone}">{escape(text)}</span></span></div></div>'
    )
