import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('library', Path(__file__).resolve().parents[1] / 'scripts/library.py')
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)

class LibraryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for channel in ['tiny-diff-club', 'PaxBuildsAI']:
            base = self.root / channel
            (base/'brand').mkdir(parents=True)
            (base/'brand/channel.json').write_text(json.dumps({'display_name':channel,'voice':{'status':'selected'}}))
            (base/'AGENTS.md').write_text('Keep voice local')
            (base/'reels/demo').mkdir(parents=True)
            (base/'reels/demo/production.json').write_text('{"state":"draft"}')
            (base/'reels/demo/movie.mp4').write_bytes(b'duplicate bytes')
        (self.root/'tiny-diff-club/reels/demo/frames').mkdir()
        (self.root/'tiny-diff-club/reels/demo/frames/001.png').write_bytes(b'frame')
        (self.root/'tiny-diff-club/escape').symlink_to('/tmp', target_is_directory=True)
        self.con = lib.connect(self.root/'data/library.sqlite3', self.root)
        lib.scan(self.con, self.root)

    def tearDown(self):
        self.con.close()
        self.temp.cleanup()

    def post(self, pid='p', channel='tiny-diff-club', platform='instagram', account='a'):
        return {'id':pid,'channel_id':channel,'episode_id':channel+'/demo','platform':platform,'account_id':account,'format':'reel','organic':True,'published_at':'2026-11-01T00:00:00Z'}

    def metric(self, pid='p', views=100, suffix=''):
        return {'id':'m'+pid+suffix,'post_id':pid,'observed_at':'2026-11-02T00:00:00Z','metric_definition':'platform-insights-v1','metrics':{'views':views,'likes':0,'comments':None}}

    def test_scan_idempotence_dedup_and_missing(self):
        before = lib.export(self.con)
        result = lib.scan(self.con, self.root)
        self.assertEqual(result['hashed'],0)
        self.assertEqual(before, lib.export(self.con))
        movies = list(self.con.execute("SELECT sha256 FROM assets WHERE kind='video'"))
        self.assertEqual(movies[0][0],movies[1][0])
        self.assertFalse(list(self.con.execute("SELECT * FROM assets WHERE path LIKE '%001.png'")))
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM posts').fetchone()[0],0)
        (self.root/'tiny-diff-club/reels/demo/movie.mp4').unlink()
        lib.scan(self.con, self.root)
        self.assertEqual(self.con.execute("SELECT present FROM assets WHERE path='tiny-diff-club/reels/demo/movie.mp4'").fetchone()[0],0)

    def test_atomic_import_idempotence_and_null(self):
        payload = {'schema_version':1,'posts':[self.post()], 'metric_snapshots':[self.metric(views=0)]}
        lib.import_crm(self.con,payload)
        self.assertEqual(lib.import_crm(self.con,payload)['metric_snapshots'],0)
        metrics = lib.export(self.con)['metric_snapshots'][0]['metrics']
        self.assertEqual(metrics['views'],0)
        self.assertIsNone(metrics['comments'])
        self.assertNotIn('shares',metrics)
        conflict = self.metric(views=20)
        with self.assertRaises(ValueError):
            lib.import_crm(self.con,{'schema_version':1,'posts':[self.post('new')],'metric_snapshots':[conflict]})
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM posts').fetchone()[0],1)

    def test_channel_scope_and_invalid_metrics(self):
        wrong = self.post()
        wrong['episode_id'] = 'PaxBuildsAI/demo'
        with self.assertRaises(ValueError): lib.import_crm(self.con,{'schema_version':1,'posts':[wrong]})
        lib.import_crm(self.con,{'schema_version':1,'posts':[self.post()]})
        for value in [-1, True, float('nan')]:
            with self.assertRaises(ValueError): lib.import_crm(self.con,{'schema_version':1,'metric_snapshots':[self.metric(views=value)]})

    def test_report_comparison_and_latest_window(self):
        posts = [self.post(str(i)) for i in range(4)] + [self.post('x',platform='x'),self.post('pax',channel='PaxBuildsAI')]
        metrics = [self.metric(str(i),views=400 if i==3 else 100) for i in range(4)] + [self.metric('x',1000000),self.metric('pax',1000000)]
        lib.import_crm(self.con,{'schema_version':1,'posts':posts,'metric_snapshots':metrics})
        result = lib.report(self.con)['candidates']
        winner = next(x for x in result if x['post_id']=='3')
        self.assertEqual(winner['views_lift'],4)
        self.assertTrue(winner['candidate_for_test'])
        self.assertEqual(winner['baseline_peer_count'],3)
        self.assertIsNone(winner['engagement_per_view'])
        self.assertFalse(next(x for x in result if x['post_id']=='x')['candidate_for_test'])
        late = self.metric('3',800,'later'); late['observed_at']='2026-11-02T01:00:00Z'
        lib.import_crm(self.con,{'schema_version':1,'metric_snapshots':[late]})
        result = lib.report(self.con)['candidates']
        self.assertEqual(sum(x['post_id']=='3' for x in result),1)
        self.assertEqual(next(x for x in result if x['post_id']=='3')['views'],800)

    def test_metric_definitions_do_not_mix(self):
        posts = [self.post(str(i)) for i in range(4)]
        metrics = [self.metric(str(i), 400 if i==3 else 100) for i in range(4)]
        metrics[3]['metric_definition']='platform-insights-v2'
        lib.import_crm(self.con, {'schema_version':1,'posts':posts,'metric_snapshots':metrics})
        winner=next(x for x in lib.report(self.con)['candidates'] if x['post_id']=='3')
        self.assertEqual(winner['baseline_peer_count'],0)
        self.assertFalse(winner['candidate_for_test'])

    def test_latest_snapshot_tie_is_deterministic_and_unversioned_is_provisional(self):
        posts=[self.post(str(i)) for i in range(4)]
        metrics=[self.metric(str(i), 100) for i in range(4)]
        tie=self.metric('3',400,'z'); tie.pop('metric_definition')
        metrics.append(tie)
        lib.import_crm(self.con,{'schema_version':1,'posts':posts,'metric_snapshots':list(reversed(metrics))})
        record=next(x for x in lib.report(self.con)['candidates'] if x['post_id']=='3')
        self.assertEqual(record['snapshot_id'],tie['id'])
        self.assertTrue(record['provisional'])
        self.assertFalse(record['candidate_for_test'])

    def test_read_connection_during_write_transaction(self):
        self.con.execute('BEGIN IMMEDIATE')
        self.con.execute("UPDATE channels SET instructions='pending write' WHERE id='tiny-diff-club'")
        reader=lib.connect(self.root/'data/library.sqlite3',self.root)
        self.assertEqual(reader.execute("SELECT instructions FROM channels WHERE id='tiny-diff-club'").fetchone()[0], 'Keep voice local')
        reader.close()
        self.con.rollback()

    def test_annotations_and_workspace_guard(self):
        annotation = {'id':'a1','channel_id':'tiny-diff-club','episode_id':'tiny-diff-club/demo','kind':'beat_sheet','body':{'beats':[{'start_s':0,'end_s':2,'emotion':'surprise'}]}}
        lib.import_crm(self.con, {'schema_version':1,'annotations':[annotation]})
        self.assertEqual(lib.export(self.con)['annotations'][0],annotation)
        with self.assertRaises(ValueError): lib.connect(self.root/'data/library.sqlite3',self.root/'other')

if __name__=='__main__': unittest.main()
