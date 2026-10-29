import unittest

from dmedoc import binfile, diagnose
from dmedoc.ds2 import DS2Error, NoResponse, build_frame, parse_frame, xor_checksum


class TestDS2(unittest.TestCase):
    def test_ident_request_frame(self):
        self.assertEqual(build_frame(0x12, bytes([0x00])), bytes([0x12, 0x04, 0x00, 0x16]))

    def test_roundtrip(self):
        f = build_frame(0x12, bytes([0xA0, 1, 2, 3]))
        self.assertEqual(parse_frame(f), (0x12, bytes([0xA0, 1, 2, 3])))

    def test_bad_checksum(self):
        f = bytearray(build_frame(0x12, bytes([0xA0])))
        f[-1] ^= 0xFF
        with self.assertRaises(DS2Error):
            parse_frame(bytes(f))

    def test_bad_length(self):
        with self.assertRaises(DS2Error):
            parse_frame(bytes([0x12, 0x09, 0xA0, 0x00]))

    def test_xor(self):
        self.assertEqual(xor_checksum(b"\x12\x04\x00"), 0x16)


class TestBin(unittest.TestCase):
    def test_empty(self):
        self.assertIn("Fichier vide.", binfile.analyse(b"").warnings)

    def test_all_ff(self):
        r = binfile.analyse(b"\xff" * 512 * 1024)
        self.assertEqual(r.size_hint, "MS42 / MS43 (512 Ko)")
        self.assertTrue(any("0xFF" in w for w in r.warnings))

    def test_partial_flash(self):
        data = b"\x12\x34" * (128 * 1024) + b"\xff" * (256 * 1024)
        r = binfile.analyse(data)
        self.assertTrue(any("blocs" in w for w in r.warnings))

    def test_odd_size(self):
        self.assertTrue(any("Taille inhabituelle" in w for w in binfile.analyse(b"\x01" * 1000).warnings))

    def test_part_number(self):
        data = b"\x00" * 100 + b"1430844" + b"\x00" * 100
        self.assertIn("1430844", binfile.analyse(data).part_numbers)

    def test_diff(self):
        self.assertEqual(binfile.diff_ranges(b"abcdef", b"abXXef"), [(2, 4)])


class TestDiagnose(unittest.TestCase):
    def test_no_response_explains(self):
        out = diagnose.diagnose_link(NoResponse("x"), None)
        self.assertEqual(out[0].level, "ERREUR")
        self.assertTrue(any("alimentation" in f.message for f in out))


if __name__ == "__main__":
    unittest.main()
