"""Core logic: pobieranie audio z linku i transkrypcja/tłumaczenie przez Gemini."""

import os
import re
import shutil
import subprocess
import tempfile
import uuid

import yt_dlp
from dotenv import load_dotenv
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

MODEL_NAME = "gemini-3.1-flash-lite"
PROMPT = (
    "Transkrybuj to nagranie i przetłumacz mowę na naturalny, płynny język polski "
    "w formie czytelnych akapitów. Zwróć WYŁĄCZNIE gotowe polskie tłumaczenie — "
    "bez oryginalnego tekstu, bez nagłówków, list ani żadnych komentarzy, "
    "tylko czysty tekst podzielony na akapity."
)
TRANSLATE_PROMPT = (
    "Poniżej znajduje się surowy transkrypt nagrania. Przetłumacz go na naturalny, "
    "płynny język polski w formie czytelnych akapitów. Zwróć WYŁĄCZNIE gotowe "
    "polskie tłumaczenie — bez oryginalnego tekstu, bez nagłówków, list ani "
    "żadnych komentarzy, tylko czysty tekst podzielony na akapity.\n\nTranskrypt:\n"
)


def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def extract_youtube_video_id(url: str) -> str | None:
    """Wyciąga 11-znakowe video_id z dowolnego formatu linku YouTube
    (watch?v=, youtu.be/, shorts/)."""
    match = re.search(r"(?:v=|\/|shorts\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None


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
    expected_path = os.path.join(tmp_dir, f"video_transcriber_{output_id}.mp3")

    ydl_opts = {
        "format": "ba[ext=m4a]/ba/b",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }
        ],
        # Node.js do rozwiązywania wyzwań podpisu YouTube (JS challenge).
        "js_runtimes": {"node": {}},
        # Klienci mweb/tv omijają blokadę 403 na serwerowych IP (datacenter).
        # android jako fallback: mweb/tv same w sobie nie zwracały żadnych
        # formatów na obecnej wersji yt-dlp (2026.08.19) nawet lokalnie.
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb", "tv", "android"],
            }
        },
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"Pobieranie audio nie powiodło się:\n{e}")

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


def get_client() -> genai.Client:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Brak GEMINI_API_KEY (ani w st.secrets, ani w .env / zmiennych środowiskowych)."
        )
    return genai.Client(api_key=api_key)


def transcribe_and_translate(audio_path: str) -> str:
    """Wysyła plik audio do Gemini i zwraca transkrypt przetłumaczony na polski."""
    client = get_client()

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


def fetch_youtube_transcript_text(video_id: str) -> str | None:
    """Pobiera gotowe napisy/transkrypcję z YouTube po samym video_id.

    Preferuje polski/angielski, w razie braku bierze dowolny dostępny transkrypt
    (ręczny lub automatycznie wygenerowany). Zwraca None, jeśli wideo nie ma
    żadnych napisów.
    """
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
    except Exception:
        return None

    try:
        transcript = transcript_list.find_transcript(["pl", "en"])
    except Exception:
        try:
            transcript = next(iter(transcript_list))
        except StopIteration:
            return None

    try:
        data = transcript.fetch().to_raw_data()
    except Exception:
        return None

    full_text = " ".join(item["text"] for item in data).strip()
    return full_text or None


def translate_text_with_gemini(text: str) -> str:
    """Tłumaczy/formatuje gotowy transkrypt tekstowy na naturalny polski przez Gemini."""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[TRANSLATE_PROMPT + text],
    )
    return response.text


def transcribe_youtube(url: str) -> str:
    """Pipeline dla YouTube: wyłącznie gotowe napisy (youtube-transcript-api) + Gemini.

    Nie pobiera pliku audio przez yt-dlp (blokada 403 na IP chmurowych) ani nie
    przekazuje URL do Gemini przez Part.from_uri (też zwraca 403 PERMISSION_DENIED
    dla kluczy Google AI Studio).
    """
    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise RuntimeError(f"Nie udało się rozpoznać video_id w linku: {url}")

    transcript_text = fetch_youtube_transcript_text(video_id)
    if not transcript_text:
        raise RuntimeError(
            "Ten film na YouTube nie ma dostępnych napisów/ścieżki transkrypcyjnej."
        )

    return translate_text_with_gemini(transcript_text)


def transcribe_url(url: str) -> str:
    """Pełny pipeline: rozpoznaje platformę i wybiera odpowiednią ścieżkę transkrypcji."""
    if is_youtube_url(url):
        return transcribe_youtube(url)

    audio_path = download_audio(url)
    try:
        return transcribe_and_translate(audio_path)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
