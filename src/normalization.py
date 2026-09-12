import re
import unicodedata
from urllib.parse import quote


def normalize_title(title: str) -> str:
    title = unicodedata.normalize("NFKC", title)
    title = title.casefold()
    title = re.sub(r"\s+", " ", title).strip()

    return quote(title, safe="")


def normalize_genre(genre: str) -> str:
    return genre.casefold().strip()