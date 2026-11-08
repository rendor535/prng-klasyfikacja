# Klasyfikacja położenia polskich miejscowości na podstawie nazw

Porównanie regresji logistycznej, k-NN i Random Forest na nazwach miejscowości z PRNG.

## Struktura

```text
prng-klasyfikacja/
├── data/
│   ├── raw/               # tu umieść prng.xlsx
│   └── processed/         # oczyszczony CSV
├── src/
│   ├── __init__.py
│   └── prepare_data.py    # pierwszy etap: import, walidacja i cechy
├── tests/
│   └── test_prepare_data.py
├── notebooks/             # analiza rozkładów i wykresy (kolejny etap)
├── results/               # audyt i przyszłe wyniki modeli
├── .gitignore
├── requirements.txt
└── README.md
```

## Uruchomienie – Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Umieść pobrany PRNG XLSX w data/raw/prng.xlsx
python -m src.prepare_data --input data/raw/prng.xlsx
python -m unittest discover -s tests -v
```

Jeśli PowerShell blokuje aktywację, można bez aktywowania uruchomić:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.prepare_data --input data/raw/prng.xlsx
```

Dla konkretnej nazwy arkusza:

```powershell
python -m src.prepare_data --input data/raw/prng.xlsx --sheet "NAZWA_ARKUSZA"
```

Wyniki: `data/processed/miejscowosci.csv` (UTF-8 z BOM, separator `,`) i `results/audyt.json`.

## Przyjęte decyzje metodologiczne

- Zostają tylko `kategoria obiektu = miejscowość`, `rodzaj reprezentacji = punkt główny`, `status nazwy = urzędowa`, `rodzaj obiektu = miasto` albo `wieś`.
- Współrzędne WGS84 są używane **wyłącznie do ustalenia klasy**, nie jako cechy modelu.
- `latitude >= 52.0` oznacza `polnoc`, poniżej oznacza `poludnie`. To umowna granica eksperymentu, nie oficjalna granica geograficzna Polski.
- Zachowujemy osobne miejscowości o identycznych nazwach; usuwamy tylko powielone `id_prng`.
- Dla przyszłego podziału trening/test należy grupować po `nazwa_grupa` (np. `GroupShuffleSplit` lub `StratifiedGroupKFold`), żeby identyczne nazwy nie trafiły po obu stronach.
- TF-IDF i wszelkie transformacje uczone na danych mają być dopasowywane **dopiero na treningu** (Pipeline), aby zapobiec wyciekowi danych.
- Skrypt wypisuje i zapisuje liczby rekordów po każdym filtrze, liczbę niepoprawnych współrzędnych, rozkład klas i liczbę nazw przypisanych do obu klas.
- Filtr geograficzny jest kontrolą przybliżonego zakresu współrzędnych Polski; nie zastępuje geometrycznej granicy państwa.
- Przed właściwymi eksperymentami przeanalizuj bilans klas i poprawność dopasowania filtrów do pełnego pliku.

## Źródło

Państwowy Rejestr Nazw Geograficznych (PRNG), Główny Urząd Geodezji i Kartografii: https://www.geoportal.gov.pl/
