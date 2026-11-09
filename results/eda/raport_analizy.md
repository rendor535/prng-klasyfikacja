# Analiza opisowa przygotowanego zbioru PRNG

Przeanalizowano **44 664** rekordów (31 117 odrębnych nazw po normalizacji).

## Zmienna docelowa

- Południe: 21 564 (48,28%).
- Północ: 23 100 (51,72%).
- Granica podziału: **52,00°N** (umowna).

## Charakterystyki ilościowe

| Atrybut | Min | Średnia | Mediana | Max |
|---|---:|---:|---:|---:|
| Szerokość geograficzna (°N) | 49,03 | 52,05 | 52,06 | 54,83 |
| Długość geograficzna (°E) | 14,14 | 19,73 | 19,90 | 24,13 |
| Długość nazwy (znaki) | 2,00 | 9,19 | 8,00 | 40,00 |
| Liczba wyrazów | 1,00 | 1,18 | 1,00 | 5,00 |

## Powtarzające się nazwy

- Nazwy występujące więcej niż raz: **5 137 grup**.
- Nazwy występujące w obu klasach: **2 289 grup**.
- Powtórzone identyfikatory PRNG: **0**.

Powtarzających się nazw nie usunięto: mogą oznaczać różne miejscowości. Przy walidacji modeli należy grupować obserwacje po `nazwa_grupa`, aby identyczne nazwy nie trafiły jednocześnie do treningu i testu.

## Końcówki -ów oraz -owo

| Końcówka | Razem | Południe | Północ |
|---|---:|---:|---:|
| -ów | 4164 | 3370 | 794 |
| -owo | 2750 | 140 | 2610 |

## Pliki z wykresami

01 — liczebność klas; 02 — szerokość geograficzna; 03 — długość nazw; 04 — liczba wyrazów; 05 — boxplot długości; 06 — końcówki 3-znakowe; 07 — końcówki -ów i -owo; 08 — województwa (jeżeli są dostępne).

Współrzędne służą jedynie do etykietowania i analizy opisowej, a nie jako cechy wejściowe przyszłych modeli.
