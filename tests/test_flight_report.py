import json
import tempfile
import unittest
from pathlib import Path
from plugins.flight_report.python.src.generate_report import read_session, summarize, generate


class FlightReportTests(unittest.TestCase):
    def _session(self, directory):
        directory = Path(directory)
        meta = {'session_id':'test-001', 'aircraft_type':'Su-25T','completed':True}
        (directory / 'metadata.json').write_text(json.dumps(meta), encoding='utf-8')
        with (directory / 'telemetry.jsonl').open('w', encoding='utf-8') as f:
            for i in range(3):
                packet = {'protocol':'scaf.telemetry','version':1,'type':'aircraft.state', 'sequence':i+1,'timestamp':i*.2, 'aircraft':{'type':'Su-25T'},'data': {'speed_mps':100+i,'altitude_m':1000+i*10,'fuel_internal_kg':500-i,'acceleration_g':{'y':1+i}, 'position':{'lat_deg':44.0+i*.0001,'lon_deg':-1.0}}}
                f.write(json.dumps({'received_at_utc':'2026-11-15T00:00:00Z','packet':packet})+'\n')

    def test_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._session(tmp)
            meta, rows, quality = read_session(Path(tmp))
            summary = summarize(meta, rows, quality)
            self.assertEqual(summary['record_count'],3)
            self.assertAlmostEqual(summary['duration_s'],.4)
            self.assertAlmostEqual(summary['fuel_used_kg'],2)
            self.assertAlmostEqual(summary['max_normal_g'],3)
            self.assertEqual(quality['sequence_gaps'],0)

    def test_missing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._session(tmp)
            path = Path(tmp) / 'telemetry.jsonl'
            obj = json.loads(path.read_text(encoding='utf-8').splitlines()[0])
            obj['packet']['data'] = {'speed_mps':None}
            path.write_text(json.dumps(obj)+'\n', encoding='utf-8')
            meta, rows, quality = read_session(Path(tmp))
            summary = summarize(meta, rows, quality)
            self.assertIsNone(summary['max_normal_g'])
            self.assertIsNone(summary['fuel_used_kg'])

    def test_report_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._session(tmp)
            pdf, summary = generate(Path(tmp))
            self.assertTrue(pdf.is_file())
            self.assertTrue(pdf.stat().st_size > 1000)
            self.assertTrue((pdf.parent/'telemetry.csv').exists())
            self.assertTrue((pdf.parent/'summary.json').exists())


if __name__ == '__main__':
    unittest.main()
