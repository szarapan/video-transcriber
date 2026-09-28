"""Streamlit UI: wklej link, kliknij Transkrybuj, dostań polski tekst."""

import streamlit as st

from core import transcribe_url

st.set_page_config(page_title="Video Transcriber", page_icon="🎙️")

st.title("🎙️ Video Transcriber")
st.caption("Wklej link (TikTok / YouTube Shorts / Instagram Reels) i pobierz transkrypt po polsku.")

with st.form("transcribe_form", clear_on_submit=False):
    url = st.text_input(
        "Link do wideo",
        placeholder="Wklej link z TikTok / YouTube Shorts / Instagram Reels...",
    )
    submit_button = st.form_submit_button("Transkrybuj", type="primary")

if submit_button:
    if not url.strip():
        st.warning("Proszę podać link do wideo.")
    else:
        with st.spinner("Pobieram audio i tłumaczę..."):
            try:
                st.session_state["result"] = transcribe_url(url)
                st.session_state["error"] = None
            except Exception as e:
                st.session_state["result"] = None
                st.session_state["error"] = str(e)

if st.session_state.get("error"):
    st.error(st.session_state["error"])

if st.session_state.get("result"):
    st.text_area("Transkrypt (PL)", value=st.session_state["result"], height=400)
    st.code(st.session_state["result"], language=None)
    st.caption("Użyj ikony kopiowania w prawym górnym rogu bloku powyżej, żeby skopiować tekst.")
