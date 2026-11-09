"""Synergy: Mars Turizm chatbotu. Çalıştırma: streamlit run app.py"""

import subprocess
import sys
from pathlib import Path

import ollama
import streamlit as st

from llm import MODEL, OPTIONS, answer_turn, warm_up
from mascot_state import IDLE_LINES, publish_answer, state_for, write_state
from meeting import Meeting, check_answer, first_sentence
from memory import GapMemory
from notebook import BASE_CSS, HEADER_HTML, NOTEBOOK_CSS, SIGNATURE_HTML, agenda_html, opening_html, question_html
from page_mascot import page_mascot_html
from persona import LINKEDIN_PROMPT, WELCOME
from rag import Retriever

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "mars_turizm.txt"
MEMORY_PATH = ROOT / "memory" / "open_gaps.json"

st.set_page_config(page_title="Synergy", page_icon="🛰️")
st.markdown(BASE_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Doküman ve model hazırlanıyor...")
def load_retriever() -> Retriever:
    retriever = Retriever(DATA_PATH)
    warm_up(retriever.client)
    return retriever


@st.cache_resource
def mascot_holder() -> dict:
    return {"process": None}


def sync_mascot(revealed: bool) -> None:
    """Perde açılınca maskotu çağırır, kapanınca çantasıyla uğurlar."""
    was_revealed = st.session_state.get("was_revealed", False)
    if revealed and not was_revealed:
        holder = mascot_holder()
        if holder["process"] is None or holder["process"].poll() is not None:
            holder["process"] = subprocess.Popen([sys.executable, str(ROOT / "mascot.py")], cwd=ROOT)
    elif was_revealed and not revealed:
        write_state("quit")
    st.session_state.was_revealed = revealed


def linkedin_post(client: ollama.Client, minutes: str, knowledge: str) -> str:
    prompt = LINKEDIN_PROMPT.format(minutes=minutes)
    response = client.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], think=False, options=OPTIONS)
    post = response["message"]["content"].strip()
    # Paylaşım da aynı kurallardan geçer; kirliyse sayısız sabit metne düşer.
    if check_answer(post, knowledge + minutes, ""):
        return "Bugünkü toplantıda bir kez daha gördüm: Asıl soru sorulan soru değil, liderliğin bedelidir. #Vizyon #Sinerji"
    return post


client = ollama.Client()
try:
    retriever = load_retriever()
except (ollama.ResponseError, ConnectionError) as error:
    st.error(f"Ollama'ya ulaşılamadı. Servisin açık olduğundan ve modellerin indirildiğinden emin olun. ({error})")
    st.stop()

knowledge = DATA_PATH.read_text(encoding="utf-8")

if "meeting" not in st.session_state:
    st.session_state.meeting = Meeting()
    st.session_state.memory = GapMemory(MEMORY_PATH)
    st.session_state.memory_started = False
    st.session_state.history = []
    st.session_state.closed = False
    st.session_state.linkedin = ""

meeting: Meeting = st.session_state.meeting
memory: GapMemory = st.session_state.memory


def carried_questions() -> list[str]:
    return [gap.question for gap in memory.carried_gaps()]


def page_mascot_scene(visible: bool) -> str:
    """Giriş, çıkış ve tepkiler yalnızca bir kez oynar; sonraki çizimlerde tekrar etmez."""
    was_visible = st.session_state.get("page_mascot_visible", False)
    st.session_state.page_mascot_visible = visible
    if visible and not was_visible:
        return page_mascot_html("enter")
    if was_visible and not visible:
        return page_mascot_html("exit", "Bir sonraki toplantıya geçiyorum." if st.session_state.closed else "")
    if not visible:
        return ""
    reaction = st.session_state.pop("page_mascot_reaction", None)
    if reaction:
        return page_mascot_html(*reaction)
    return page_mascot_html("idle", idle_line=IDLE_LINES[len(meeting.items) % len(IDLE_LINES)])


with st.sidebar:
    st.subheader("Oturum")
    show_panel = st.toggle("Paneli göster", value=False)
    # Karakter tektir: Ya sayfanın kenarında ya masaüstünde durur.
    on_desktop = show_panel and st.toggle("Maskotu masaüstüne çıkar", value=False)
    sync_mascot(on_desktop)
    if show_panel:
        st.markdown("**KPI**")
        st.metric("Toplantı verimi", f"{meeting.efficiency}/100")
        for label, value in meeting.metrics().items():
            st.metric(label, value)
        st.metric("Devreden açık madde", len(memory.carried_gaps()))
        if memory.gaps:
            st.markdown("**Açık veri gap'leri**")
            for gap in memory.gaps:
                st.caption(gap.question)
    if st.button("Toplantıyı kapat", disabled=not meeting.items, use_container_width=True):
        with st.spinner("Tutanak hazırlanıyor..."):
            st.session_state.linkedin = linkedin_post(client, meeting.minutes(carried_questions()), knowledge)
        st.session_state.closed = True
        write_state("closed")
    if st.button("Yeni oturum", use_container_width=True):
        if show_panel:
            write_state("quit")
        st.session_state.clear()
        st.rerun()
    if st.button("Hafızayı sıfırla", use_container_width=True):
        if show_panel:
            write_state("quit")
        memory.reset()
        st.session_state.clear()
        st.rerun()

page_mascot_visible = show_panel and not on_desktop and not st.session_state.closed
mascot_slot = st.empty()
if scene := page_mascot_scene(page_mascot_visible):
    mascot_slot.markdown(scene, unsafe_allow_html=True)

if show_panel:
    st.markdown(NOTEBOOK_CSS + HEADER_HTML, unsafe_allow_html=True)
else:
    st.title("Synergy")
    st.caption("Mars Turizm dijital çalışanı")

if show_panel:
    st.markdown(opening_html(WELCOME), unsafe_allow_html=True)
else:
    with st.chat_message("assistant"):
        st.markdown(WELCOME)

for number, item in enumerate(meeting.items, start=1):
    if show_panel:
        st.markdown(agenda_html(number, item, newest=number == len(meeting.items)), unsafe_allow_html=True)
        continue
    with st.chat_message("user"):
        st.markdown(item.question)
    with st.chat_message("assistant"):
        st.markdown(item.answer)
        if item.sources:
            with st.expander("Kaynak satırlar"):
                for line in item.sources:
                    st.markdown(f"- {line}")

placeholder_text = "Yeni gündem maddesi yazın" if show_panel else "Sorunuzu yazın"
if question := st.chat_input(placeholder_text, key="question", disabled=st.session_state.closed):
    if show_panel:
        st.markdown(question_html(len(meeting.items) + 1, question), unsafe_allow_html=True)
    else:
        with st.chat_message("user"):
            st.markdown(question)
    with st.container() if show_panel else st.chat_message("assistant"):
        if not st.session_state.memory_started:
            memory.start_meeting()
            st.session_state.memory_started = True
        placeholder = st.empty()
        write_state("thinking", "...")
        if page_mascot_visible:
            mascot_slot.markdown(page_mascot_html("thinking", "..."), unsafe_allow_html=True)
        item = answer_turn(client, retriever, knowledge, question, meeting, st.session_state.history, memory, placeholder.markdown)
        placeholder.markdown(item.answer)
    publish_answer(item)
    if page_mascot_visible:
        st.session_state.page_mascot_reaction = (state_for(item), first_sentence(item.answer))
    st.rerun()

if st.session_state.closed:
    st.divider()
    minutes = meeting.minutes(carried_questions())
    st.markdown(minutes)
    st.subheader("LinkedIn paylaşımı")
    st.info(st.session_state.linkedin)
    if show_panel:
        st.markdown(SIGNATURE_HTML, unsafe_allow_html=True)
    st.download_button("Tutanağı indir", minutes, file_name="toplanti_tutanagi.md")
