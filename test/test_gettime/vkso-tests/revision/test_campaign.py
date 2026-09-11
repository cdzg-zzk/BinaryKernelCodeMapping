import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from campaign import PARAMETERS, digest, freeze_protocol, pending


class CampaignTest(unittest.TestCase):
    def test_mixed_load_parameters_and_tools_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tool = root / 'reader'
            tool.write_bytes(b'original executable')
            args = SimpleNamespace(**dict.fromkeys(PARAMETERS, 1))
            frozen = freeze_protocol(root, args, {'reader': tool})
            self.assertEqual(frozen, freeze_protocol(root, args, {'reader': tool}))
            args.rate = 2
            with self.assertRaisesRegex(ValueError, 'changed'):
                freeze_protocol(root, args, {'reader': tool})
            args.rate = 1
            tool.write_bytes(b'changed executable')
            with self.assertRaisesRegex(ValueError, 'changed'):
                freeze_protocol(root, args, {'reader': tool})

    def test_completion_marker_cannot_hide_changed_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            step = {'index': 0}
            plan = {'steps': [step]}
            (root / 'plan.json').write_text(json.dumps(plan))
            (root / 'protocol.json').write_text('{}')
            output = root / 'step-000'
            output.mkdir()
            values = output / 'measurements.csv'
            values.write_text('original evidence')
            record = dict(step=step, boot_id='boot-a', plan_sha256=digest(root / 'plan.json'),
                          protocol_sha256=digest(root / 'protocol.json'), measurements_sha256=digest(values))
            (output / 'complete.json').write_text(json.dumps(record))
            self.assertIsNone(pending(root, plan))
            values.write_text('truncated evidence')
            with self.assertRaisesRegex(ValueError, 'measurements'):
                pending(root, plan)


if __name__ == '__main__':
    unittest.main()
