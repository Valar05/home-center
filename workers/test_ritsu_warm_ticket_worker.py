"""Deterministic no-GPU safety tests for Ritsu's local ticket journal."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WORKER = Path(__file__).with_name('ritsu_warm_ticket_worker.py')
spec = importlib.util.spec_from_file_location('ritsu_warm_worker_under_test', WORKER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class JournalSafetyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = module.JOURNAL
        module.JOURNAL = Path(self.temp.name)
        self.ticket = {'ticketId': 'conversation-turn-0001', 'textSha256': '0' * 64}

    def tearDown(self):
        module.JOURNAL = self.original
        self.temp.cleanup()

    def test_completed_ticket_not_replayed(self):
        with patch.object(module, 'dispatch', return_value={'status': 'enqueued', 'relayIds': ['a' * 32]}) as send:
            one = module.process_ticket(self.ticket)
            two = module.process_ticket(self.ticket)
            self.assertEqual(one, two)
            send.assert_called_once()

    def test_crash_before_completion_fails_closed(self):
        module.durable_record(self.ticket['ticketId'], {'phase': 'started', 'textSha256': self.ticket['textSha256']})
        with patch.object(module, 'dispatch') as send:
            result = module.process_ticket(self.ticket)
            self.assertEqual(result['errorCode'], 'AMBIGUOUS_PREVIOUS_ATTEMPT')
            send.assert_not_called()

    def test_same_id_changed_digest_rejected(self):
        module.durable_record(self.ticket['ticketId'], {'phase': 'started', 'textSha256': self.ticket['textSha256']})
        changed = {**self.ticket, 'textSha256': 'f' * 64}
        with self.assertRaisesRegex(RuntimeError, 'different transcript'):
            module.process_ticket(changed)


if __name__ == '__main__':
    unittest.main()
