import unittest
import pandas as pd
from src.prepare_data import parse_dms_pair, filter_and_transform


class TestPRNG(unittest.TestCase):
    def test_dms(self):
        lat, lon = parse_dms_pair('50°43\'05" 16°39\'17"')
        self.assertAlmostEqual(lat, 50 + 43 / 60 + 5 / 3600)
        self.assertAlmostEqual(lon, 16 + 39 / 60 + 17 / 3600)

    def test_seconds_60(self):
        lat, lon = parse_dms_pair('52°06\'58" 22°29\'60"')
        self.assertAlmostEqual(lon, 22.5)

    def test_bad_coords(self):
        self.assertEqual(parse_dms_pair('90°00\'00" 0°00\'00"'), (None, None))

    def test_filter(self):
        frame = pd.DataFrame([
            {'id_prng':'1', 'nazwa':'Kraków', 'kategoria':'miejscowość', 'reprezentacja':'punkt główny', 'status':'urzędowa', 'rodzaj':'miasto', 'wspolrzedne':'50°03\'00" 19°56\'00"'},
            {'id_prng':'2', 'nazwa':'Darłowo', 'kategoria':'miejscowość', 'reprezentacja':'punkt główny', 'status':'urzędowa', 'rodzaj':'miasto', 'wspolrzedne':'54°25\'00" 16°25\'00"'},
            {'id_prng':'3', 'nazwa':'Osiedle', 'kategoria':'miejscowość', 'reprezentacja':'punkt główny', 'status':'urzędowa', 'rodzaj':'część miasta', 'wspolrzedne':'50°00\'00" 19°00\'00"'},
        ])
        cleaned, audit = filter_and_transform(frame, 52.0)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(set(cleaned['klasa']), {'polnoc','poludnie'})
        self.assertEqual(audit['rows_after_city_village'], 2)


if __name__ == '__main__':
    unittest.main()
