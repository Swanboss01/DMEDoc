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
        self.assertIn(("w_empty", {}), binfile.analyse(b"").warnings)

    def test_all_ff(self):
        r = binfile.analyse(b"\xff" * 512 * 1024)
        self.assertEqual(r.size_hint, "MS42 / MS43 (512 KB)")
        self.assertIn(("w_all_ff", {}), r.warnings)

    def test_partial_flash(self):
        data = b"\x12\x34" * (128 * 1024) + b"\xff" * (256 * 1024)
        r = binfile.analyse(data)
        self.assertTrue(any(k == "w_blocks" for k, _ in r.warnings))

    def test_odd_size(self):
        self.assertTrue(any(k == "w_size" for k, _ in binfile.analyse(b"\x01" * 1000).warnings))

    def test_part_number(self):
        data = b"\x00" * 100 + b"1430844" + b"\x00" * 100
        self.assertIn("1430844", binfile.analyse(data).part_numbers)

    def test_diff(self):
        self.assertEqual(binfile.diff_ranges(b"abcdef", b"abXXef"), [(2, 4)])


class TestDiagnose(unittest.TestCase):
    def test_no_response_explains(self):
        out = diagnose.diagnose_link(NoResponse("x"), None)
        self.assertEqual(out[0].level, "error")
        self.assertTrue(any("12 V" in f.message for f in out))

    def test_translations_complete(self):
        from dmedoc.i18n import STRINGS

        self.assertEqual(set(STRINGS["en"]), set(STRINGS["fr"]))

    def test_french_output(self):
        from dmedoc.i18n import set_lang

        set_lang("fr")
        try:
            out = diagnose.format_findings(diagnose.diagnose_link(NoResponse("x"), None))
            self.assertIn("[ERREUR]", out)
        finally:
            set_lang("en")


class TestSim(unittest.TestCase):
    def test_ok(self):
        from dmedoc.sim import SimState, diagnose_sim

        st = SimState(ignition=True)
        self.assertTrue(st.can_run())
        self.assertEqual(diagnose_sim(st)[0].level, "info")

    def test_power_hides_other_faults(self):
        from dmedoc.sim import SimState, diagnose_sim

        st = SimState(ignition=True, fault_power=True, fault_ews=True)
        self.assertFalse(st.can_run())
        self.assertEqual(len(diagnose_sim(st)), 1)

    def test_multiple_faults(self):
        from dmedoc.sim import SimState, diagnose_sim

        st = SimState(ignition=True, fault_crank=True, fault_ews=True)
        self.assertEqual(len(diagnose_sim(st)), 2)

    def test_critical_blocks_and_comes_first(self):
        from dmedoc.sim import SimState, diagnose_sim

        st = SimState(ignition=True, fault_ews=True, fault_short=True)
        self.assertEqual(st.critical(), ["short"])
        self.assertFalse(st.can_run())
        out = diagnose_sim(st)
        self.assertEqual(len(out), 2)  # the critical cause + the "stopped" notice
        self.assertTrue(all(f.level == "error" for f in out))

    def test_ignition_off(self):
        from dmedoc.sim import SimState, diagnose_sim

        st = SimState(ignition=False, fault_ews=True)
        self.assertFalse(st.can_run())
        self.assertEqual(diagnose_sim(st)[0].level, "info")


if __name__ == "__main__":
    unittest.main()
