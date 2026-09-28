"""Core logic: pobieranie audio z linku i transkrypcja/tłumaczenie przez Gemini."""

import os
import shutil
import subprocess
import tempfile
import uuid

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL_NAME = "gemini-3.1-flash-lite"
PROMPT = (
    "Transkrybuj to nagranie i przetłumacz mowę na naturalny, płynny język polski "
    "w formie czytelnych akapitów. Zwróć WYŁĄCZNIE gotowe polskie tłumaczenie — "
    "bez oryginalnego tekstu, bez nagłówków, list ani żadnych komentarzy, "
    "tylko czysty tekst podzielony na akapity."
)


def ensure_ffmpeg() -> None:
    """Sprawdza czy ffmpeg jest dostępny, a jeśli nie - instaluje go przez Homebrew."""
    if shutil.which("ffmpeg"):
        return

    if not shutil.which("brew"):
        raise RuntimeError(
            "ffmpeg nie jest zainstalowany, a Homebrew też nie jest dostępne. "
            "Zainstaluj ffmpeg ręcznie: https://ffmpeg.org/download.html"
        )

    print("ffmpeg nie znaleziony — instaluję przez Homebrew...")
    subprocess.run(["brew", "install", "ffmpeg"], check=True)

    if not shutil.which("ffmpeg"):
        raise RuntimeError("Instalacja ffmpeg przez Homebrew nie powiodła się.")


def download_audio(url: str) -> str:
    """Pobiera samo audio z linku (TikTok/YouTube/Instagram) jako MP3 do katalogu tymczasowego.

    Zwraca ścieżkę do pobranego pliku MP3.
    """
    ensure_ffmpeg()

    tmp_dir = tempfile.gettempdir()
    output_id = uuid.uuid4().hex
    output_template = os.path.join(tmp_dir, f"video_transcriber_{output_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Pobieranie audio nie powiodło się:\n{result.stderr}")

    expected_path = os.path.join(tmp_dir, f"video_transcriber_{output_id}.mp3")
    if not os.path.exists(expected_path):
        raise RuntimeError(
            f"Nie znaleziono pobranego pliku audio (oczekiwano: {expected_path})."
        )

    return expected_path


def get_api_key() -> str | None:
    """Pobiera klucz API: st.secrets w chmurze (Streamlit Community Cloud),
    w przeciwnym razie zmienne środowiskowe / plik .env (lokalnie)."""
    try:
        import streamlit as st

        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return os.environ.get("GEMINI_API_KEY")


def transcribe_and_translate(audio_path: str) -> str:
    """Wysyła plik audio do Gemini i zwraca transkrypt przetłumaczony na polski."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Brak GEMINI_API_KEY (ani w st.secrets, ani w .env / zmiennych środowiskowych)."
        )

    client = genai.Client(api_key=api_key)

    uploaded_file = client.files.upload(file=audio_path)
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[PROMPT, uploaded_file],
        )
    finally:
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

    return response.text


def transcribe_url(url: str) -> str:
    """Pełny pipeline: pobiera audio z linku, transkrybuje i usuwa plik tymczasowy."""
    audio_path = download_audio(url)
    try:
        return transcribe_and_translate(audio_path)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
