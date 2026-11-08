"""Wstępne przygotowanie nazw polskich miejscowości z arkusza PRNG (XLSX).

Uruchomienie:
    python -m src.prepare_data --input data/raw/prng.xlsx
    python -m src.prepare_data --input data/raw/prng.xlsx --sheet "NGRP" --latitude-boundary 52
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

LOG = logging.getLogger("prng")

# Przykład: 50°43'05" 16°39'17"; dopuszczalne również N/S/E/W.
DMS = re.compile(
    r"(\d{1,3})\s*[°º]\s*(\d{1,2})\s*['′’]\s*(\d{1,2}(?:[.,]\d+)?)\s*[\"″”]?\s*([NSEW])?",
    re.IGNORECASE,
)

# Nagłówki XLSX zgodne z udostępnionym przykładem PRNG.
ALIASES = {
    "identyfikator PRNG": "id_prng",
    "nazwa główna": "nazwa",
    "kategoria obiektu": "kategoria",
    "rodzaj obiektu": "rodzaj",
    "status nazwy": "status",
    "rodzaj reprezentacji": "reprezentacja",
    "współrzędne geograficzne": "wspolrzedne",
    "województwo": "wojewodztwo",
}
REQUIRED = set(ALIASES) - {"województwo"}


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return unicodedata.normalize("NFC", str(value).replace("\u00a0", " ")).strip()


def normalize_header(value: object) -> str:
    return " ".join(normalize_text(value).casefold().split())


def parse_dms_pair(value: object) -> tuple[float | None, float | None]:
    """Zwraca (latitude, longitude) w stopniach dziesiętnych.

    W zbiorze PRNG dotyczącym Polski pierwsza liczba to N, druga E.
    Jeżeli kierunki podano jawnie, stosowane są ich znaki.
    Sekundy równe 60 są poprawnie przeliczane, nie obcinane.
    """
    text = normalize_text(value)
    matches = list(DMS.finditer(text))
    if len(matches) != 2:
        return None, None
    coords = []
    for m in matches:
        deg, minutes = int(m.group(1)), int(m.group(2))
        seconds = float(m.group(3).replace(",", "."))
        direction = (m.group(4) or "").upper()
        if minutes > 59 or seconds > 60 or seconds < 0:
            return None, None
        decimal = deg + minutes / 60 + seconds / 3600
        if direction in {"S", "W"}:
            decimal *= -1
        coords.append(decimal)
    lat, lon = coords
    # Zabezpieczenie przed przypadkowym importem danych spoza Polski.
    if not (48.0 <= lat <= 56.0 and 13.0 <= lon <= 25.0):
        return None, None
    return lat, lon


def choose_sheet(path: Path, requested: str | None) -> tuple[str, int]:
    """Odnajduje arkusz i wiersz nagłówka (również przy wierszach tytułowych)."""
    book = pd.ExcelFile(path)
    sheets = [requested] if requested is not None else book.sheet_names
    candidates = []
    for sheet in sheets:
        if sheet not in book.sheet_names:
            raise ValueError(f"Brak arkusza {sheet!r}. Dostępne: {book.sheet_names}")
        preview = pd.read_excel(book, sheet_name=sheet, header=None, nrows=25, dtype=str)
        for row_index, row in preview.iterrows():
            labels = {normalize_header(v) for v in row.tolist()}
            score = sum(normalize_header(k) in labels for k in REQUIRED)
            if score == len(REQUIRED):
                candidates.append((sheet, int(row_index)))
                break
    if not candidates:
        raise ValueError(
            "Nie znaleziono arkusza z wymaganymi kolumnami PRNG. "
            f"Sprawdź XLSX i nazwy kolumn: {', '.join(sorted(REQUIRED))}"
        )
    return candidates[0]


def load_prng(path: Path, sheet: str | None) -> tuple[pd.DataFrame, str]:
    sheet_name, header_row = choose_sheet(path, sheet)
    LOG.info("Arkusz: %s; wiersz nagłówków: %s", sheet_name, header_row + 1)
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row, dtype=str)
    mapping = {normalize_header(k): v for k, v in ALIASES.items()}
    df.columns = [mapping.get(normalize_header(k), normalize_text(k)) for k in df.columns]
    return df, sheet_name


def filter_and_transform(df: pd.DataFrame, boundary: float) -> tuple[pd.DataFrame, dict]:
    audit: dict = {"rows_original": int(len(df)), "boundary_latitude": boundary}

    def filtered(field: str, permitted: set[str], metric: str) -> None:
        nonlocal df
        mask = df[field].map(lambda s: normalize_text(s).casefold() in permitted)
        df = df.loc[mask].copy()
        audit[metric] = int(len(df))

    filtered("kategoria", {"miejscowość"}, "rows_after_category")
    filtered("reprezentacja", {"punkt główny"}, "rows_after_main_point")
    filtered("status", {"urzędowa"}, "rows_after_official_status")
    filtered("rodzaj", {"miasto", "wieś"}, "rows_after_city_village")

    df["nazwa"] = df["nazwa"].map(normalize_text)
    df["id_prng"] = df["id_prng"].map(normalize_text)
    df = df[(df["nazwa"] != "") & (df["id_prng"] != "")].copy()
    audit["rows_after_nonempty"] = int(len(df))

    pairs = df["wspolrzedne"].map(parse_dms_pair)
    df["latitude"] = [p[0] for p in pairs]
    df["longitude"] = [p[1] for p in pairs]
    bad_coords = df["latitude"].isna() | df["longitude"].isna()
    audit["rows_invalid_coordinates"] = int(bad_coords.sum())
    df = df.loc[~bad_coords].copy()

    # Deduplikacja obiektów, nie nazw: różne miejscowości mogą mieć tę samą nazwę.
    audit["rows_duplicate_prng_id"] = int(df.duplicated(subset=["id_prng"]).sum())
    df = df.drop_duplicates(subset=["id_prng"], keep="first")
    df["nazwa_grupa"] = df["nazwa"].str.casefold().str.replace(r"\s+", " ", regex=True)
    df["dlugosc_nazwy"] = df["nazwa"].str.len()
    for count in (2, 3, 4):
        df[f"koncowka_{count}"] = df["nazwa"].str.casefold().str[-count:]
    df["czy_ow"] = df["nazwa"].str.casefold().str.endswith("ów").astype(int)
    df["czy_owo"] = df["nazwa"].str.casefold().str.endswith("owo").astype(int)
    df["liczba_wyrazow"] = df["nazwa"].str.split().str.len()
    df["klasa"] = df["latitude"].map(lambda lat: "polnoc" if lat >= boundary else "poludnie")

    audit["rows_final"] = int(len(df))
    audit["class_counts"] = {k: int(v) for k, v in Counter(df["klasa"]).items()}
    audit["name_groups"] = int(df["nazwa_grupa"].nunique())
    audit["repeated_name_groups"] = int((df["nazwa_grupa"].value_counts() > 1).sum())
    audit["ambiguous_name_groups"] = int((df.groupby("nazwa_grupa")["klasa"].nunique() > 1).sum())
    if len(df):
        audit["latitude_summary"] = {k: float(v) for k, v in df["latitude"].agg(["min", "median", "mean", "max"]).items()}

    cols = ["id_prng", "nazwa", "nazwa_grupa", "rodzaj", "latitude", "longitude", "klasa",
            "dlugosc_nazwy", "liczba_wyrazow", "koncowka_2", "koncowka_3", "koncowka_4", "czy_ow", "czy_owo"]
    if "wojewodztwo" in df.columns:
        cols.insert(4, "wojewodztwo")
    return df[cols].sort_values(["nazwa_grupa", "id_prng"]).reset_index(drop=True), audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Ścieżka do oryginalnego XLSX PRNG")
    parser.add_argument("--sheet", default=None, help="Nazwa arkusza (domyślnie autodetekcja)")
    parser.add_argument("--output", type=Path, default=Path("data/processed/miejscowosci.csv"))
    parser.add_argument("--audit", type=Path, default=Path("results/audyt.json"))
    parser.add_argument("--latitude-boundary", type=float, default=52.0,
                        help="Granica północ/południe (domyślnie 52.0 stopnie N)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if not args.input.is_file():
        parser.error(f"Nie znaleziono pliku: {args.input}")
    frame, sheet_name = load_prng(args.input, args.sheet)
    cleaned, audit = filter_and_transform(frame, args.latitude_boundary)
    if cleaned.empty:
        raise SystemExit("Po filtracji brak rekordów. Sprawdź status/rodzaje obiektów w XLSX.")
    audit["input_file"] = args.input.name
    audit["input_sheet"] = sheet_name
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(args.output, index=False, encoding="utf-8-sig")
    args.audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.info("Zapisano %s rekordów: %s", len(cleaned), args.output)
    LOG.info("Audyt: %s", args.audit)
    LOG.info("Klasy: %s", audit["class_counts"])


if __name__ == "__main__":
    main()
