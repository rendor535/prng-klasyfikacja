"""Analiza opisowa danych przygotowanych przez src.prepare_data.

Uruchomienie z katalogu projektu:
    python -m src.analyze_data
    python -m src.analyze_data --input data/processed/miejscowosci.csv --audit results/audyt.json

Wyniki: results/eda/ (PNG, CSV, TXT i raport Markdown).
Moduł NIE wykonuje treningu ani nie wykorzystuje współrzędnych jako predyktorów.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

REQUIRED = {
    'id_prng', 'nazwa', 'nazwa_grupa', 'rodzaj', 'latitude', 'longitude',
    'klasa', 'dlugosc_nazwy', 'liczba_wyrazow', 'koncowka_2', 'koncowka_3',
    'koncowka_4', 'czy_ow', 'czy_owo',
}


def chart_style() -> None:
    plt.rcParams.update({
        'figure.figsize': (10, 5.5), 'figure.dpi': 120,
        'savefig.dpi': 180, 'axes.grid': True, 'axes.axisbelow': True,
        'grid.alpha': 0.2, 'font.size': 10,
    })


def save_chart(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)


def bar_labels(ax, bars) -> None:
    for bar in bars:
        value = bar.get_height()
        ax.annotate(f'{value:,.0f}'.replace(',', ' '),
                    (bar.get_x() + bar.get_width() / 2, value),
                    xytext=(0, 4), textcoords='offset points',
                    ha='center', va='bottom', fontsize=9)


def describe(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    stat = df[cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    return stat.rename(columns={'count': 'liczba', 'mean': 'srednia', 'std': 'odch_std',
                                'min': 'minimum', '25%': 'q1', '50%': 'mediana',
                                '75%': 'q3', 'max': 'maksimum'}).round(4)


def main() -> None:
    ap = argparse.ArgumentParser(description='Analiza eksploracyjna miejscowości PRNG')
    ap.add_argument('--input', type=Path, default=Path('data/processed/miejscowosci.csv'))
    ap.add_argument('--audit', type=Path, default=Path('results/audyt.json'))
    ap.add_argument('--output-dir', type=Path, default=Path('results/eda'))
    ap.add_argument('--top', type=int, default=15, help='Liczba najczęstszych końcówek na wykresie')
    args = ap.parse_args()
    if args.top < 1:
        ap.error('--top musi być dodatnie')
    if not args.input.is_file():
        ap.error(f'Brak CSV: {args.input}; uruchom wcześniej python -m src.prepare_data')

    df = pd.read_csv(args.input, dtype={'id_prng': 'string', 'nazwa': 'string',
                                       'nazwa_grupa': 'string'}, encoding='utf-8-sig')
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f'W CSV brakuje kolumn: {sorted(missing)}')
    if df.empty:
        raise ValueError('Plik CSV nie zawiera rekordów')
    for c in ['latitude', 'longitude', 'dlugosc_nazwy', 'liczba_wyrazow', 'czy_ow', 'czy_owo']:
        df[c] = pd.to_numeric(df[c], errors='raise')
    if df[list(REQUIRED)].isna().any().any():
        raise ValueError('W kolumnach wymaganych występują braki danych')
    if not set(df['klasa'].unique()).issubset({'polnoc', 'poludnie'}):
        raise ValueError('Nieznane etykiety klas')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    chart_style()
    out = args.output_dir

    stats = describe(df, ['latitude', 'longitude', 'dlugosc_nazwy', 'liczba_wyrazow'])
    stats.to_csv(out / 'statystyki_opisowe.csv', encoding='utf-8-sig')
    counts = df['klasa'].value_counts().reindex(['poludnie', 'polnoc'], fill_value=0)
    class_table = pd.DataFrame({'liczba': counts, 'procent': (counts / len(df) * 100).round(2)})
    class_table.to_csv(out / 'liczebnosc_klas.csv', encoding='utf-8-sig')
    for n in [2, 3, 4]:
        freq = df[f'koncowka_{n}'].value_counts().rename_axis('koncowka').reset_index(name='liczba')
        freq.to_csv(out / f'koncowki_{n}.csv', index=False, encoding='utf-8-sig')
    by_class = pd.crosstab(df['koncowka_3'], df['klasa']).reindex(columns=['poludnie', 'polnoc'], fill_value=0)
    by_class['razem'] = by_class.sum(axis=1)
    by_class.to_csv(out / 'koncowki_3_wg_klasy.csv', encoding='utf-8-sig')

    name_size = df.groupby('nazwa_grupa').size()
    name_nclass = df.groupby('nazwa_grupa')['klasa'].nunique()
    repeated = int((name_size > 1).sum())
    ambiguous = int((name_nclass > 1).sum())
    duplicates = int(df.duplicated('id_prng').sum())
    group_summary = {
        'liczba_rekordow': int(len(df)), 'liczba_nazw_unikalnych': int(name_size.size),
        'nazwy_powtarzajace_sie_grupy': repeated,
        'nazwy_obie_klasy_grupy': ambiguous,
        'rekordy_należące_do_powtarzajacych_sie_nazw': int(name_size[name_size > 1].sum()),
        'rekordy_należące_do_nazw_w_obu_klasach': int(name_size[name_nclass > 1].sum()),
        'powtorzone_id_prng': duplicates,
    }
    (out / 'powtarzalnosc_nazw.json').write_text(
        json.dumps(group_summary, indent=2, ensure_ascii=False), encoding='utf-8')
    # Zachowujemy nazwy powtarzalne: są to odrębne miejscowości.
    name_size.sort_values(ascending=False).head(30).rename('liczba').to_csv(
        out / 'najczestsze_nazwy.csv', encoding='utf-8-sig')
    amb = df[df['nazwa_grupa'].isin(name_nclass[name_nclass > 1].index)]
    (amb.groupby('nazwa_grupa')['klasa'].value_counts().unstack(fill_value=0)
        .reindex(columns=['poludnie', 'polnoc'], fill_value=0)
        .to_csv(out / 'nazwy_w_obu_klasach.csv', encoding='utf-8-sig'))

    # 01. Liczebności klas
    fig, ax = plt.subplots()
    bars = ax.bar(['Południe', 'Północ'], counts.values)
    bar_labels(ax, bars)
    ax.set(title='Liczba miejscowości według klasy geograficznej', ylabel='Liczba rekordów')
    ax.set_ylim(top=max(counts.max() * 1.12, 1))
    save_chart(fig, out / '01_liczebnosc_klas.png')

    # 02. Histogram szerokości geograficznej wraz z granicą klas
    fig, ax = plt.subplots()
    ax.hist(df['latitude'], bins=45, edgecolor='white')
    boundary = 52.0
    if args.audit.exists():
        audit = json.loads(args.audit.read_text(encoding='utf-8'))
        boundary = float(audit.get('boundary_latitude', boundary))
    ax.axvline(boundary, linestyle='--', linewidth=2, label=f'Granica: {boundary:g}°N')
    ax.set(title='Rozkład szerokości geograficznej', xlabel='Szerokość geograficzna (°N)', ylabel='Liczba rekordów')
    ax.legend()
    save_chart(fig, out / '02_histogram_szerokosci.png')

    # 03. Histogram długości nazw
    fig, ax = plt.subplots()
    length = df['dlugosc_nazwy']
    ax.hist(length, bins=range(int(length.min()), int(length.max()) + 2), edgecolor='white')
    ax.set(title='Rozkład długości nazw miejscowości', xlabel='Liczba znaków', ylabel='Liczba rekordów')
    save_chart(fig, out / '03_histogram_dlugosci_nazw.png')

    # 04. Histogram liczby wyrazów
    fig, ax = plt.subplots()
    words = df['liczba_wyrazow'].value_counts().sort_index()
    bars = ax.bar(words.index.astype(str), words.values)
    bar_labels(ax, bars)
    ax.set(title='Liczba wyrazów w nazwach miejscowości', xlabel='Liczba wyrazów', ylabel='Liczba rekordów')
    save_chart(fig, out / '04_liczba_wyrazow.png')

    # 05. Wykres pudełkowy długości nazwy w obu klasach
    fig, ax = plt.subplots()
    box_data = [df.loc[df['klasa'].eq(k), 'dlugosc_nazwy'] for k in ['poludnie', 'polnoc']]
    ax.boxplot(box_data, tick_labels=['Południe', 'Północ'], showfliers=False)
    ax.set(title='Długość nazw w podziale na klasy (bez rysowania odstających)', ylabel='Liczba znaków')
    save_chart(fig, out / '05_boxplot_dlugosci_nazw.png')

    # 06. Najczęstsze końcówki 3-znakowe
    common = df['koncowka_3'].value_counts().head(args.top).sort_values()
    fig, ax = plt.subplots()
    ax.barh(common.index, common.values)
    ax.set(title=f'{args.top} najczęstszych końcówek 3-znakowych', xlabel='Liczba rekordów', ylabel='Końcówka')
    save_chart(fig, out / '06_najczestsze_koncowki_3.png')

    # 07. -ów i -owo: udział klas i liczebność
    data = []
    for col, title in [('czy_ow', '-ów'), ('czy_owo', '-owo')]:
        sample = df.loc[df[col].eq(1)]
        n = len(sample)
        data.append({'koncowka': title, 'liczba': n,
                     'poludnie': int(sample['klasa'].eq('poludnie').sum()),
                     'polnoc': int(sample['klasa'].eq('polnoc').sum())})
    suffix_table = pd.DataFrame(data).set_index('koncowka')
    suffix_table.to_csv(out / 'koncowki_ow_owo.csv', encoding='utf-8-sig')
    fig, ax = plt.subplots()
    suffix_table[['poludnie', 'polnoc']].rename(
        columns={'poludnie': 'Południe', 'polnoc': 'Północ'}).plot.bar(ax=ax, rot=0)
    ax.set(title='Końcówki -ów i -owo według klasy', xlabel='Końcówka', ylabel='Liczba miejscowości')
    ax.legend(title='Klasa')
    save_chart(fig, out / '07_ow_owo_wg_klasy.png')

    # 08. Województwa (jeśli dostępne)
    if 'wojewodztwo' in df.columns and df['wojewodztwo'].notna().any():
        voiv = pd.crosstab(df['wojewodztwo'], df['klasa']).reindex(columns=['poludnie', 'polnoc'], fill_value=0)
        voiv.to_csv(out / 'wojewodztwa_wg_klasy.csv', encoding='utf-8-sig')
        fig, ax = plt.subplots(figsize=(11, 7))
        voiv.sort_values(by=['poludnie', 'polnoc']).rename(
            columns={'poludnie': 'Południe', 'polnoc': 'Północ'}).plot.barh(ax=ax, stacked=True)
        ax.set(title='Liczba miejscowości według województwa i klasy', xlabel='Liczba miejscowości', ylabel='Województwo')
        save_chart(fig, out / '08_wojewodztwa.png')

    # Raport zawiera tylko wartości policzone z faktycznego CSV.
    def fmt(value: float) -> str:
        return f'{value:.2f}'.replace('.', ',')

    report = [
        '# Analiza opisowa przygotowanego zbioru PRNG', '',
        f'Przeanalizowano **{len(df):,}** rekordów ({name_size.size:,} odrębnych nazw po normalizacji).'.replace(',', ' '),
        '', '## Zmienna docelowa', '',
        f'- Południe: {counts["poludnie"]:,} ({fmt(class_table.loc["poludnie", "procent"])}%).'.replace(f'{counts["poludnie"]:,}', f'{counts["poludnie"]:,}'.replace(',', ' ')),
        f'- Północ: {counts["polnoc"]:,} ({fmt(class_table.loc["polnoc", "procent"])}%).'.replace(f'{counts["polnoc"]:,}', f'{counts["polnoc"]:,}'.replace(',', ' ')),
        f'- Granica podziału: **{fmt(boundary)}°N** (umowna).',
        '', '## Charakterystyki ilościowe', '',
        '| Atrybut | Min | Średnia | Mediana | Max |', '|---|---:|---:|---:|---:|',
    ]
    for c, label in [('latitude', 'Szerokość geograficzna (°N)'), ('longitude', 'Długość geograficzna (°E)'),
                     ('dlugosc_nazwy', 'Długość nazwy (znaki)'), ('liczba_wyrazow', 'Liczba wyrazów')]:
        r = stats.loc[c]
        report.append(f'| {label} | {fmt(r["minimum"])} | {fmt(r["srednia"])} | {fmt(r["mediana"])} | {fmt(r["maksimum"])} |')
    report.extend([
        '', '## Powtarzające się nazwy', '',
        f'- Nazwy występujące więcej niż raz: **{repeated:,} grup**.'.replace(',', ' '),
        f'- Nazwy występujące w obu klasach: **{ambiguous:,} grup**.'.replace(',', ' '),
        f'- Powtórzone identyfikatory PRNG: **{duplicates}**.',
        '', 'Powtarzających się nazw nie usunięto: mogą oznaczać różne miejscowości. '
        'Przy walidacji modeli należy grupować obserwacje po `nazwa_grupa`, '
        'aby identyczne nazwy nie trafiły jednocześnie do treningu i testu.',
        '', '## Końcówki -ów oraz -owo', '',
        '| Końcówka | Razem | Południe | Północ |', '|---|---:|---:|---:|',
    ])
    for suffix, r in suffix_table.iterrows():
        report.append(f'| {suffix} | {int(r["liczba"])} | {int(r["poludnie"])} | {int(r["polnoc"])} |')
    report.extend(['', '## Pliki z wykresami', '',
                   '01 — liczebność klas; 02 — szerokość geograficzna; 03 — długość nazw; '
                   '04 — liczba wyrazów; 05 — boxplot długości; 06 — końcówki 3-znakowe; '
                   '07 — końcówki -ów i -owo; 08 — województwa (jeżeli są dostępne).',
                   '', 'Współrzędne służą jedynie do etykietowania i analizy opisowej, '
                   'a nie jako cechy wejściowe przyszłych modeli.'])
    (out / 'raport_analizy.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    print(f'Gotowe. Przeanalizowano {len(df)} rekordów. Wyniki: {out.resolve()}')
    print('Nazwy powtarzalne:', repeated, '| Nazwy w obu klasach:', ambiguous)


if __name__ == '__main__':
    main()
