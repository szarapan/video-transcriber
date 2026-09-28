"""Streamlit UI: wklej link, kliknij Transkrybuj, dostań polski tekst."""

import os

import streamlit as st

from core import transcribe_url

st.set_page_config(page_title="Video Transcriber", page_icon="🎙️")


def get_app_pin() -> str:
    """PIN dostępu: st.secrets w chmurze, w przeciwnym razie zmienna środowiskowa
    (domyślnie "1234", jeśli nic nie ustawiono)."""
    try:
        pin = st.secrets.get("APP_PIN")
        if pin:
            return str(pin)
    except Exception:
        pass
    return os.getenv("APP_PIN", "1234")


def is_authorized() -> bool:
    """Sesja trwała: raz zalogowany PIN zostaje zapisany w st.query_params,
    więc przeżywa odświeżenie strony, uśpienie telefonu i bezczynność —
    w przeciwieństwie do samego st.session_state, który ginie z nową sesją."""
    app_pin = get_app_pin()

    if st.session_state.get("authenticated"):
        return True

    # Autoryzacja przez parametr w URL, np. ...?pin=1234 (wygodne na telefonie).
    if st.query_params.get("pin") == app_pin:
        st.session_state["authenticated"] = True
        return True

    return False


if not is_authorized():
    st.title("🎙️ Video Transcriber")
    st.warning("Ta aplikacja jest chroniona PIN-em. Podaj PIN, aby uzyskać dostęp.")

    with st.form("login_form"):
        pin_input = st.text_input("PIN", type="password")
        login_button = st.form_submit_button("Zaloguj")

    if login_button:
        app_pin = get_app_pin()
        if pin_input == app_pin:
            # Zapisz PIN w URL, żeby logowanie przetrwało odświeżenie/nową sesję.
            st.query_params["pin"] = app_pin
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Nieprawidłowy PIN.")

    st.stop()

st.title("🎙️ Video Transcriber")
st.caption("Wklej link (TikTok / YouTube Shorts / Instagram Reels) i pobierz transkrypt po polsku.")

# Pole z kluczem "video_url_input" trzeba wyczyścić PRZED jego instancjonowaniem
# w tym przebiegu skryptu — inaczej Streamlit rzuca StreamlitWidgetAlreadyInstantiatedError.
if st.session_state.pop("clear_url", False):
    st.session_state["video_url_input"] = ""

with st.form("transcribe_form", clear_on_submit=False):
    url = st.text_input(
        "Link do wideo",
        placeholder="Wklej link z TikTok / YouTube Shorts / Instagram Reels...",
        key="video_url_input",
    )
    col1, col2 = st.columns([3, 1])
    with col1:
        submit_button = st.form_submit_button("Transkrybuj", type="primary")
    with col2:
        clear_button = st.form_submit_button("Wyczyść")

if clear_button:
    st.session_state["clear_url"] = True
    st.session_state["result"] = None
    st.session_state["error"] = None
    st.rerun()

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
