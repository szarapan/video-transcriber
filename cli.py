"""Prosty skrypt CLI do testu: python cli.py <URL>"""

import sys

from core import transcribe_url


def main() -> None:
    if len(sys.argv) != 2:
        print("Użycie: python cli.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Pobieram i transkrybuję: {url}\n")

    text = transcribe_url(url)

    print("--- TRANSKRYPT (PL) ---\n")
    print(text)


if __name__ == "__main__":
    main()
