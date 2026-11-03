import unittest, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.can_protocol import encode, decode, crc8, CanFrame
from src.virtual_can_bus import VirtualCanBus
from src.transmitter_node import TransmitterNode
from src.receiver_node import ReceiverNode
from src.fault_detection import rule_fault_code, add_window_features, FEATURES
from src import seven_segment

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dataset.csv")


class TestProtocol(unittest.TestCase):
    def test_roundtrip(self):
        f = encode(0x101, 92.3, 0.456, 2345, 17)
        self.assertEqual(decode(f), (92.3, 0.456, 2345, 17))
        self.assertEqual(len(f.data), 8)

    def test_crc_known_value(self):
        self.assertEqual(crc8(b"123456789"), 0xF4)   # standard CRC-8 (poly 0x07) check value

    def test_corruption_detected(self):
        f = encode(0x102, 88.0, 0.3, 2000, 1)
        bad = CanFrame(f.can_id, bytes([f.data[0] ^ 0x01]) + f.data[1:])
        with self.assertRaises(ValueError): decode(bad)

    def test_negative_temperature_and_limits(self):
        self.assertEqual(decode(encode(0x103, -5.5, 0.0, 0, 0))[0], -5.5)
        with self.assertRaises(ValueError): encode(0x101, 99999, 0.1, 100, 0)

    def test_invalid_id(self):
        with self.assertRaises(ValueError): CanFrame(0x800, bytes(8))


class TestRules(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(rule_fault_code(90, 0.3), 0)
        self.assertEqual(rule_fault_code(105, 0.3), 101)
        self.assertEqual(rule_fault_code(90, 0.8), 102)
        self.assertEqual(rule_fault_code(110, 1.2), 103)
        self.assertEqual(rule_fault_code(104.9, 0.79), 0)


class TestSevenSegment(unittest.TestCase):
    def test_digits(self):
        self.assertEqual(seven_segment.encode_text("08"), [0x3F, 0x7F])
        self.assertEqual(seven_segment.encode_text("E101")[0], 0x79)

    def test_render_shape(self):
        self.assertEqual(len(seven_segment.render("E101").split("\n")), 3)


class TestBus(unittest.TestCase):
    def test_loss_and_corruption_are_counted(self):
        bus = VirtualCanBus(loss_rate=0.2, corrupt_rate=0.2, seed=1)
        for i in range(500): bus.send(encode(0x101, 90, 0.3, 2000, i))
        self.assertEqual(bus.sent, 500); self.assertGreater(bus.dropped, 50); self.assertEqual(len(bus), 500 - bus.dropped)


class TestDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.df = pd.read_csv(DATA, dtype={"node_id": str})

    def test_schema(self):
        self.assertEqual(list(self.df.columns), ["timestamp", "node_id", "temp_C", "vibration_g", "rpm", "fault_code", "alarm_flag"])

    def test_quality(self):
        self.assertEqual(len(self.df), 15000); self.assertEqual(int(self.df.isna().sum().sum()), 0)
        ts = pd.to_datetime(self.df.timestamp); self.assertTrue(ts.is_monotonic_increasing and ts.is_unique)

    def test_fault_share_in_range(self):
        self.assertTrue(0.02 <= self.df.alarm_flag.mean() <= 0.05)

    def test_alarm_matches_fault_code(self):
        self.assertTrue(((self.df.fault_code != 0).astype(int) == self.df.alarm_flag).all())

    def test_signal_ranges(self):
        self.assertTrue(self.df.rpm.between(600, 4000).all()); self.assertTrue(self.df.vibration_g.between(0, 3).all())


class TestEndToEnd(unittest.TestCase):
    def test_clean_bus_detects_every_fault_row(self):
        bus = VirtualCanBus(); tx = TransmitterNode(bus, DATA); tx.run(); rx = ReceiverNode(bus); rx.run()
        log = pd.DataFrame(rx.log); self.assertEqual(len(log), 15000)
        m = tx.df.merge(log, on="timestamp")
        self.assertTrue((m.fault_code == m.rule_fault_code).all())   # receiver rules reproduce every label on a clean bus
        self.assertTrue((m.alarm_flag == m.rule_alarm).all())
        self.assertEqual(rx.crc_errors, 0); self.assertEqual(rx.missing_frames, 0)

    def test_lossy_bus_is_handled(self):
        bus = VirtualCanBus(loss_rate=0.02, corrupt_rate=0.02, seed=3); TransmitterNode(bus, DATA).run(3000)
        rx = ReceiverNode(bus); rx.run()
        self.assertEqual(rx.crc_errors, bus.corrupted); self.assertGreater(rx.missing_frames, 0)
        self.assertEqual(len(rx.log) + rx.crc_errors, bus.sent - bus.dropped)

    def test_live_features_match_offline(self):
        df = pd.read_csv(DATA, dtype={"node_id": str}).head(200); off = add_window_features(df)
        bus = VirtualCanBus(); TransmitterNode(bus, DATA).run(200); rx = ReceiverNode(bus)
        live = []
        orig = rx._features
        rx._features = lambda t, v, r: (live.append(orig(t, v, r)) or live[-1])
        rx.run()
        np.testing.assert_allclose(np.array(live)[10:, 3], off.temp_mean5.values[10:], atol=0.06)   # payload rounding 0.1 C
        np.testing.assert_allclose(np.array(live)[10:, 5], off.vib_mean5.values[10:], atol=0.002)


if __name__ == "__main__":
    unittest.main()
