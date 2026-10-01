import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import requests
from services import public_player_cache as cache
from routers import players
from fastapi import HTTPException


class PublicCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"DOTASENSE_PUBLIC_CACHE_DIR":self.temp.name})
        self.environment.start()
        self.snapshots = patch.object(cache, "SNAPSHOTS", Path(self.temp.name) / "bundle")
        self.snapshots.start()
        self.addCleanup(self.snapshots.stop)
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.temp.cleanup)

    def payload(self):
        return {"profile":{"account_id":123}, "recent_matches":[{"match_id":"456", "position":2,"position_source":"user_confirmed","role_name":"private","role_source":"user_confirmed"}],
                "training":{"secret":"private"},"coach":{"private":"derived"},"data_stage":"deep"}

    def test_persists_only_public_fields_and_no_client_labels(self):
        original = self.payload()
        cache.save(original, 1000)
        restored = cache.load(123, 1001)
        self.assertNotIn("training", restored["data"])
        self.assertNotIn("coach", restored["data"])
        row = restored["data"]["recent_matches"][0]
        self.assertEqual(row["position"], 0)
        self.assertEqual(row["role_source"], "unknown")
        self.assertEqual(original["recent_matches"][0]["role_name"], "private")
        self.assertIsNone(cache.load(124, 1001))

    def test_expiry_future_timestamp_and_account_mismatch_are_rejected(self):
        cache.save(self.payload(), 1000)
        self.assertIsNone(cache.load(123, 1000 + 86401))
        self.assertIsNone(cache.load(123, 999))
        path = Path(self.temp.name) / '123.json'
        record = json.loads(path.read_text());record['data']['profile']['account_id'] = 999
        path.write_text(json.dumps(record))
        self.assertIsNone(cache.load(123, 1001))

    def test_http_error_preserves_valid_stale_data_and_negative_cache(self):
        response = Mock(status_code=429)
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        key = '/players/123:[]'
        with patch.dict(os.environ,{"OPENDOTA_API_KEY":""}), patch.object(players, '_cache', {key:{'time':500,'data':{'rank_tier':80}}}), patch.object(players,'_upstream_failures',{}), patch('routers.players.time.time',return_value=1000), patch('routers.players.requests.get',return_value=response) as get:
            first = players._cached_get('/players/123', attempts=1)
            second = players._cached_get('/players/123', attempts=1)
        self.assertEqual(first[0], {'rank_tier':80})
        self.assertIn('缓存数据', first[1])
        self.assertEqual(first, second)
        self.assertEqual(get.call_count, 1)

    def test_failure_without_any_public_record_remains_503(self):
        with patch('routers.players._fetch_player_sources', return_value=({'recent':None}, ['HTTP 429'])):
            with self.assertRaises(HTTPException) as error:
                players._player_quick_payload(123, 20)
        self.assertEqual(error.exception.status_code, 503)

    def test_bundled_default_cold_read_preserves_receipt_and_has_unique_matches(self):
        bundle = Path(players.__file__).resolve().parents[1] / 'snapshots/public_players'
        with patch.object(cache,'SNAPSHOTS',bundle), patch('routers.players._fetch_player_sources',return_value=({'recent':None},['HTTP 429'])), patch('routers.players.training_state',return_value={'marker':'current client only'}):
            result = players._player_dashboard_payload(894447460,50)
            saved = cache.load(894447460)
        self.assertEqual(len(result['recent_matches']),50)
        self.assertEqual(len({row['match_id'] for row in result['recent_matches']}),50)
        self.assertEqual(result['public_evidence']['fetched_at'],saved['fetched_at'])
        self.assertTrue(result['public_evidence']['stale'])
        self.assertEqual(result['training']['marker'],'current client only')
        self.assertEqual(result['profile']['username'],'vinceybb')

    def test_quick_does_not_replace_fifty_record_receipt_with_twenty(self):
        payload = self.payload();payload['recent_matches']=[{'match_id':str(i)} for i in range(1,51)]
        cache.save(payload, 1000)
        payload['data_stage']='quick';payload['recent_matches']=payload['recent_matches'][:20]
        cache.save(payload,1001)
        self.assertEqual(len(cache.load(123,1001)['data']['recent_matches']),50)
        self.assertEqual(cache.load(123,1001)['fetched_at'],1000)


if __name__ == '__main__': unittest.main()
