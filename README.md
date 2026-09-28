# Video Transcriber

Wklejasz link (TikTok, YouTube / YouTube Shorts, Instagram Reels i inne — wszystko co wspiera `yt-dlp`), aplikacja pobiera samo audio, wysyła je do Gemini i zwraca gotowy transkrypt przetłumaczony na polski.

## Wymagania

- Python 3
- [ffmpeg](https://ffmpeg.org) — jeśli go nie masz, `core.py` sam spróbuje go zainstalować przez Homebrew
- klucz API do Gemini: https://aistudio.google.com/apikey

## Instalacja (jednorazowo)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Skopiuj `.env.example` do `.env` i wpisz swój klucz:

```
GEMINI_API_KEY=twój_klucz
```

## Uruchomienie

**Aplikacja (Streamlit):**

```bash
./start.sh
```

Otwiera się w przeglądarce pod `http://localhost:8501`. Wklej link, kliknij **Transkrybuj**, poczekaj (~20–40 s), skopiuj tekst przyciskiem kopiowania w bloku z wynikiem.

**Szybki test z terminala (bez UI):**

```bash
source .venv/bin/activate
python cli.py "<URL>"
```

## Jak to działa

1. `yt-dlp` pobiera samo audio z linku jako MP3 do katalogu tymczasowego (platforma rozpoznawana automatycznie po URL — nie trzeba nic wybierać).
2. Plik audio leci do Gemini (`gemini-3.1-flash-lite`) z promptem o transkrypcję + tłumaczenie na polski.
3. Plik tymczasowy jest natychmiast usuwany po otrzymaniu odpowiedzi.

## Uwaga: Instagram

Instagram czasem wymaga zalogowania nawet do publicznych Reelsów (blokada anonimowego pobierania). Jeśli link z Instagrama zwróci błąd — daj znać, można dodać obsługę cookies z przeglądarki (`yt-dlp --cookies-from-browser`).

## Model Gemini

Jeśli w `core.py` (`MODEL_NAME`) pojawi się błąd, że model jest niedostępny lub przeciążony (503), zmień na inny dostępny model flash — listę sprawdzisz przez:

```bash
python -c "
import os
from dotenv import load_dotenv
from google import genai
load_dotenv()
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
for m in client.models.list():
    if 'flash' in m.name.lower():
        print(m.name)
"
```
