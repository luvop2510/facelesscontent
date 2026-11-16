#!/usr/bin/env python3
"""Local, file-backed production inventory and CRM interchange. Python stdlib only."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import statistics
import stat as file_stat
import sys
from datetime import datetime, timezone

CHANNELS = ['jensen-needs-job', 'bot-with-receipts', 'channel-three', 'patch-builds-ai',
            'tiny-diff-club', 'PaxBuildsAI', 'drakobuildsai', 'griff-ai-class']
SKIP = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.cache', 'cache',
        'frames', 'render-frames', 'render_frames', 'rendered-frames', 'tmp', 'temp'}
TEXT = {'.json', '.md', '.txt', '.js', '.mjs', '.py', '.html', '.css', '.srt', '.vtt', '.csv', '.yaml', '.yml'}
MEDIA = {'.mp4', '.mov', '.mkv', '.webm', '.m4v'}
AUDIO = {'.wav', '.mp3', '.aac', '.flac', '.m4a', '.ogg'}
IMAGE = {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.heic'}
METRICS = {'views', 'likes', 'comments', 'shares', 'saves', 'reach', 'impressions', 'watch_time_seconds', 'completion_rate', 'retention_rate'}
KINDS = {'reference_audit', 'beat_sheet', 'edit_review', 'pattern', 'experiment', 'lesson'}

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

def stable(value):
    return hashlib.sha256(value.encode()).hexdigest()[:24]

def utc(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string with timezone')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp requires timezone')
    return result.astimezone(timezone.utc)

def connect(db, workspace):
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=30000')
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'meta' in tables:
        metadata = dict(con.execute('SELECT key,value FROM meta'))
        if metadata.get('workspace') != str(workspace):
            con.close()
            raise ValueError('database belongs to a different workspace')
        if metadata.get('schema_version') != '1':
            con.close()
            raise ValueError('unsupported database schema version')
        expected = {'channels', 'episodes', 'blobs', 'assets', 'documents', 'annotations', 'posts', 'metric_snapshots', 'comments'}
        if not expected.issubset(tables):
            con.close()
            raise ValueError('database schema is incomplete')
        return con
    con.executescript((Path(__file__).resolve().parents[1] / 'schema.sql').read_text())
    con.execute("INSERT INTO meta VALUES('workspace',?)", (str(workspace),))
    con.execute("INSERT INTO meta VALUES('schema_version','1')")
    con.commit()
    return con

def classify(path):
    parts = {p.lower() for p in path.parts}
    if 'references' in parts:
        return 'reference'
    if path.suffix.lower() in AUDIO:
        if 'sfx' in parts or 'sound-effects' in parts:
            return 'sfx'
        return 'audio'
    if path.suffix.lower() in MEDIA:
        return 'video'
    if path.suffix.lower() in IMAGE:
        return 'graphic'
    return 'document' if path.suffix.lower() in TEXT else 'source'

def scan(con, workspace):
    counts = {'files': 0, 'hashed': 0, 'excluded_dirs': [], 'errors': []}
    with con:
        for channel in CHANNELS:
            base = workspace / channel
            if base.is_symlink() or not base.is_dir():
                con.execute('UPDATE channels SET present=0 WHERE id=?', (channel,))
                con.execute('UPDATE assets SET present=0 WHERE channel_id=?', (channel,))
                con.execute('UPDATE episodes SET present=0 WHERE channel_id=?', (channel,))
                continue
            profile = base / 'brand/channel.json'
            agents = base / 'AGENTS.md'
            # Do not follow metadata symlinks either.
            raw = json.loads(profile.read_text()) if profile.is_file() and not profile.is_symlink() else {}
            instructions = agents.read_text() if agents.is_file() and not agents.is_symlink() else ''
            con.execute('INSERT INTO channels VALUES(?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET profile_json=excluded.profile_json,instructions=excluded.instructions,present=1',
                        (channel, channel, canonical(raw), instructions))
            con.execute('UPDATE assets SET present=0 WHERE channel_id=?', (channel,))
            con.execute('UPDATE episodes SET present=0 WHERE channel_id=?', (channel,))
            episodes = {}
            reels = base / 'reels'
            if reels.is_dir() and not reels.is_symlink():
                for episode in sorted(reels.iterdir()):
                    if episode.is_dir() and not episode.is_symlink():
                        eid = channel + '/' + episode.name
                        episodes[episode.name] = eid
                        con.execute('INSERT INTO episodes(id,channel_id,folder,present) VALUES(?,?,?,1) ON CONFLICT(id) DO UPDATE SET present=1',
                                    (eid, channel, episode.relative_to(workspace).as_posix()))
            for root, dirs, names in os.walk(base, followlinks=False):
                for directory in list(dirs):
                    p = Path(root) / directory
                    if directory in SKIP or directory.startswith('.') or p.is_symlink():
                        counts['excluded_dirs'].append(p.relative_to(workspace).as_posix())
                        dirs.remove(directory)
                for name in sorted(names):
                    path = Path(root) / name
                    if name.startswith('.') or path.is_symlink():
                        continue
                    try:
                        relative = path.relative_to(workspace)
                        stat = path.stat()
                        if not file_stat.S_ISREG(stat.st_mode):
                            continue
                        old = con.execute('SELECT * FROM assets WHERE path=?', (relative.as_posix(),)).fetchone()
                        if old and old['bytes'] == stat.st_size and old['mtime_ns'] == stat.st_mtime_ns:
                            sha = old['sha256']
                        else:
                            digest = hashlib.sha256()
                            with path.open('rb') as source:
                                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                                    digest.update(chunk)
                            sha = digest.hexdigest()
                            after = path.stat()
                            if (after.st_size, after.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
                                raise ValueError('file changed during scan; retry')
                            counts['hashed'] += 1
                        con.execute('INSERT OR IGNORE INTO blobs VALUES(?,?)', (sha, stat.st_size))
                        parts = relative.parts
                        eid = episodes.get(parts[2]) if len(parts) > 2 and parts[1] in {'reels', 'references'} else None
                        aid = stable(relative.as_posix())
                        con.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,1,?,?) ON CONFLICT(id) DO UPDATE SET sha256=excluded.sha256,bytes=excluded.bytes,mtime_ns=excluded.mtime_ns,present=1,episode_id=excluded.episode_id,kind=excluded.kind',
                                    (aid, channel, eid, relative.as_posix(), classify(relative), sha, stat.st_size, stat.st_mtime_ns, channel, 'unknown'))
                        if path.suffix.lower() in TEXT and stat.st_size <= 2 * 1024 * 1024:
                            con.execute('INSERT OR REPLACE INTO documents VALUES(?,?)', (aid, path.read_text(errors='replace')))
                        else:
                            con.execute('DELETE FROM documents WHERE asset_id=?', (aid,))
                        counts['files'] += 1
                    except (OSError, ValueError) as error:
                        counts['errors'].append({'path': str(path.relative_to(workspace)), 'error': str(error)})
    return counts

def required(item, keys):
    for key in keys:
        if key not in item or item[key] is None or item[key] == '':
            raise ValueError('missing field ' + key)

def scoped(con, item, episode_required=False):
    required(item, ['id', 'channel_id'] + (['episode_id'] if episode_required else []))
    if item.get('episode_id'):
        row = con.execute('SELECT channel_id FROM episodes WHERE id=?', (item['episode_id'],)).fetchone()
        if not row or row[0] != item['channel_id']:
            raise ValueError('episode must belong to channel')

def immutable(con, table, item, columns):
    raw = canonical(item)
    old = con.execute('SELECT payload_json FROM ' + table + ' WHERE id=?', (item['id'],)).fetchone()
    if old:
        if old[0] != raw:
            raise ValueError('conflicting immutable ' + table + ' id: ' + item['id'])
        return 0
    con.execute('INSERT INTO ' + table + '(' + ','.join(columns) + ',payload_json) VALUES(' + ','.join('?' for _ in range(len(columns)+1)) + ')',
                tuple(item.get(key) for key in columns) + (raw,))
    return 1

def import_crm(con, payload):
    if not isinstance(payload, dict):
        raise ValueError('CRM envelope must be an object')
    if payload.get('schema_version') != 1:
        raise ValueError('schema_version must equal 1')
    accepted = {'schema_version', 'posts', 'metric_snapshots', 'comments', 'annotations'}
    if set(payload) - accepted:
        raise ValueError('unsupported import keys: ' + ','.join(sorted(set(payload) - accepted)))
    counts = {}
    with con:
        for table in ['annotations', 'posts', 'metric_snapshots', 'comments']:
            items = payload.get(table, [])
            if not isinstance(items, list):
                raise ValueError(table + ' must be an array')
            counts[table] = 0
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError('records must be objects')
                required(item, ['id'])
                if not isinstance(item['id'], str):
                    raise ValueError('id must be a string')
                if table == 'annotations':
                    scoped(con, item)
                    required(item, ['kind', 'body'])
                    if not isinstance(item['body'], dict):
                        raise ValueError('annotation body must be an object')
                    if item['kind'] not in KINDS:
                        raise ValueError('unsupported annotation kind')
                    columns = ['id', 'channel_id', 'episode_id', 'kind']
                elif table == 'posts':
                    scoped(con, item, True)
                    columns = ['id', 'channel_id', 'episode_id', 'platform', 'account_id', 'format', 'organic', 'published_at']
                    required(item, columns)
                    if type(item['organic']) is not bool:
                        raise ValueError('organic must be boolean')
                    utc(item['published_at'])
                else:
                    columns = ['id', 'post_id', 'observed_at']
                    required(item, columns)
                    observed = utc(item['observed_at'])
                    post = con.execute('SELECT published_at FROM posts WHERE id=?', (item['post_id'],)).fetchone()
                    if not post or observed < utc(post[0]):
                        raise ValueError('snapshot/comment must reference a post and follow publication')
                    if table == 'metric_snapshots':
                        required(item, ['metrics'])
                        if 'metric_definition' in item and (not isinstance(item['metric_definition'], str) or not item['metric_definition'].strip()):
                            raise ValueError('metric_definition must be a nonempty versioned definition ID')
                        if not isinstance(item['metrics'], dict) or set(item['metrics']) - METRICS:
                            raise ValueError('unsupported metrics')
                        for key, value in item['metrics'].items():
                            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                                raise ValueError('metrics must be nonnegative finite numbers or null')
                            if key.endswith('_rate') and value is not None and value > 1:
                                raise ValueError('rates must be between 0 and 1')
                    else:
                        required(item, ['text'])
                counts[table] += immutable(con, table, item, columns)
    return counts

def export(con):
    result = {'schema_version': 1}
    for table in ['channels', 'episodes', 'blobs', 'assets', 'documents', 'annotations', 'posts', 'metric_snapshots', 'comments']:
        rows = [dict(row) for row in con.execute('SELECT * FROM ' + table + ' ORDER BY 1')]
        if table in {'annotations', 'posts', 'metric_snapshots', 'comments'}:
            rows = [json.loads(row['payload_json']) for row in rows]
        result[table] = rows
    return result

def report(con):
    # Select one observation per post and age window; never compare raw totals across platforms.
    observations = {}
    for row in con.execute('SELECT payload_json FROM metric_snapshots'):
        item = json.loads(row[0])
        postrow = con.execute('SELECT payload_json FROM posts WHERE id=?', (item['post_id'],)).fetchone()
        post = json.loads(postrow[0])
        age = (utc(item['observed_at']) - utc(post['published_at'])).total_seconds() / 3600
        window = next((label for low, high, label in [(24,48,'24-48h'),(72,96,'72-96h'),(168,192,'7-8d')] if low <= age < high), None)
        views = item['metrics'].get('views')
        if window is None or views is None:
            continue
        key = (post['id'], window)
        if key not in observations or (utc(item['observed_at']), item['id']) > (utc(observations[key][1]['observed_at']), observations[key][1]['id']):
            observations[key] = (post, item, age)
    groups = {}
    for (postid, window), (post, item, age) in observations.items():
        cohort = (post['channel_id'], post['platform'], post['account_id'], post['format'], post['organic'], window, item.get('metric_definition', ''))
        groups.setdefault(cohort, []).append((post, item, age))
    candidates = []
    for cohort, rows in sorted(groups.items()):
        for post, item, age in rows:
            # Candidate excluded from its baseline.
            peers = [other[1]['metrics']['views'] for other in rows if other[0]['id'] != post['id']]
            baseline = statistics.median(peers) if peers else None
            views = item['metrics']['views']
            lift = views / baseline if baseline and len(peers) >= 3 and cohort[6] else None
            metrics = item['metrics']
            engagement = sum(metrics[k] for k in ('likes','comments','shares','saves')) / views if views > 0 and all(metrics.get(k) is not None for k in ('likes','comments','shares','saves')) else None
            candidates.append({'post_id': post['id'], 'channel_id': cohort[0], 'platform': cohort[1], 'account_id': cohort[2], 'format': cohort[3], 'organic': cohort[4], 'age_window': cohort[5], 'metric_definition': cohort[6] or None, 'provisional': not bool(cohort[6]), 'age_hours': age, 'snapshot_id': item['id'], 'views': views, 'baseline_peer_count': len(peers), 'baseline_median_views': baseline, 'views_lift': lift, 'engagement_per_view': engagement, 'candidate_for_test': lift is not None and lift >= 2, 'pattern': post.get('pattern'), 'interpretation': 'Observed association; validate with a channel-specific experiment.'})
    return {'candidates': candidates, 'notes': ['One latest snapshot per post per age window. Baseline excludes candidate; at least three comparable peers required.', 'Windows: [24,48), [72,96), [168,192) hours. Platform, account, format, organic status and channel must match.', 'Unversioned metric definitions are provisional and cannot produce candidate_for_test. Differing metric_definition IDs never share baselines.', 'Views are platform-defined. Missing metrics remain unknown. No automatic cross-channel promotion or causal attribution.']}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--db', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ['init', 'scan', 'stats', 'report']:
        sub.add_parser(command)
    out = sub.add_parser('export'); out.add_argument('--output', required=True, type=Path)
    imp = sub.add_parser('import-crm'); imp.add_argument('input', type=Path)
    ann = sub.add_parser('annotate'); ann.add_argument('input', type=Path)
    notes = sub.add_parser('search-notes'); notes.add_argument('--channel'); notes.add_argument('--kind'); notes.add_argument('--text', default=''); notes.add_argument('--limit', type=int, default=30)
    search = sub.add_parser('search'); search.add_argument('--channel'); search.add_argument('--kind'); search.add_argument('--text', default=''); search.add_argument('--limit', type=int, default=30)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    db = args.db.resolve() if args.db else workspace / 'production-memory/data/library.sqlite3'
    try:
        con = connect(db, workspace)
        if args.command == 'init': result = {'database': str(db), 'schema_version': 1}
        elif args.command == 'scan': result = scan(con, workspace)
        elif args.command == 'stats':
            result = {table: con.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in ['channels','episodes','assets','blobs','documents','annotations','posts','metric_snapshots','comments']}
            result['present_assets'] = con.execute('SELECT COUNT(*) FROM assets WHERE present=1').fetchone()[0]
        elif args.command == 'export':
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(export(con), indent=2, ensure_ascii=False) + '\n')
            result = {'output': str(args.output.resolve())}
        elif args.command in {'import-crm', 'annotate'}:
            payload = json.loads(args.input.read_text())
            if args.command == 'annotate': payload = {'schema_version':1, 'annotations': payload if isinstance(payload, list) else [payload]}
            result = import_crm(con, payload)
        elif args.command == 'report': result = report(con)
        elif args.command == 'search-notes':
            if not 1 <= args.limit <= 500: raise ValueError('limit must be 1..500')
            result = [json.loads(row[0]) for row in con.execute('SELECT payload_json FROM annotations WHERE (? IS NULL OR channel_id=?) AND (? IS NULL OR kind=?) AND payload_json LIKE ? ORDER BY id LIMIT ?', (args.channel, args.channel, args.kind, args.kind, '%'+args.text+'%', args.limit))]
        else:
            if not 1 <= args.limit <= 500: raise ValueError('limit must be 1..500')
            result = [dict(row) for row in con.execute('SELECT a.* FROM assets a LEFT JOIN documents d ON d.asset_id=a.id WHERE a.present=1 AND (? IS NULL OR a.channel_id=?) AND (? IS NULL OR a.kind=?) AND (a.path LIKE ? OR d.body LIKE ?) ORDER BY a.path LIMIT ?',
                        (args.channel,args.channel,args.kind,args.kind,'%'+args.text+'%','%'+args.text+'%',args.limit))]
        print(json.dumps(result, indent=2, ensure_ascii=False))
        con.close()
        return 0
    except (ValueError, OSError, sqlite3.Error, TypeError) as error:
        print(json.dumps({'error':str(error)}), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
