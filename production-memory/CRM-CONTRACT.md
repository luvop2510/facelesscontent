# CRM interchange v1

This is a local bridge contract, not a connected CRM API. `library.py` reads JSON files and writes SQLite. It makes no network requests, posts nothing, and schedules nothing. All file paths in the catalog are relative to the workspace; IDs are stable within that workspace.

## Commands

Run from the workspace root with Python 3 (standard library only):

```sh
python3 production-memory/scripts/library.py init
python3 production-memory/scripts/library.py scan
python3 production-memory/scripts/library.py stats
python3 production-memory/scripts/library.py search --channel tiny-diff-club --kind audio --text voice
python3 production-memory/scripts/library.py search-notes --channel tiny-diff-club --kind lesson --text timing
python3 production-memory/scripts/library.py annotate /absolute/path/annotation.json
python3 production-memory/scripts/library.py import-crm /absolute/path/crm-events.json
python3 production-memory/scripts/library.py report
python3 production-memory/scripts/library.py export --output /absolute/path/library-export.json
python3 -m unittest discover -s production-memory/tests -v
```

Global `--workspace PATH` and optional `--db PATH` precede the subcommand. The default workspace is derived from the script location, default database is `production-memory/data/library.sqlite3`. A database refuses another workspace root. Existing databases are opened without schema writes so readers can inspect the last committed inventory during a scan; writes use a 30-second busy timeout. Output is JSON; invalid input returns exit status 1 and an error on stderr. Initialize/scan before importing references to channels and episodes.

## File inventory and channel dashboard

`export` produces `schema_version: 1` and these arrays:

- `channels`: `id` is the stable folder name, including case-sensitive `PaxBuildsAI`. `folder`, `profile_json` (complete parsed channel.json serialized as JSON text), `instructions` (complete AGENTS.md), `present`. Parse `profile_json` for current character, voice, brand, handles, links and channel-specific acceptance notes. Do not treat proposed handles as live account IDs.
- `episodes`: `id` = `<channel-folder>/<reels-subfolder>`, `channel_id`, `folder`, `status: "unverified"`, `present`. Status is deliberately never inferred from names, exports or production metadata. Inspect the indexed production manifests or explicit CRM records for actual workflow state.
- `assets`: `id` = truncated SHA256 of relative path; `channel_id`, nullable `episode_id`, `path`, `kind`, `sha256`, `bytes`, `mtime_ns`, `present`, `scope`, `rights`. Each occurrence has its own asset row. Identical file contents share a blob. `scope` defaults to the owning channel, `rights` defaults to `unknown`; technical deduplication does not grant cross-channel reuse.
- `blobs`: content `sha256`, `bytes`. Files remain at their original locations; the catalog stores no media bytes and is not a media backup.
- `documents`: `asset_id`, `body` for supported text files up to 2 MiB, including episode manifests, captions, scripts, guidelines and source code. Larger files still have asset rows. Text is searchable with `search`.
- `annotations`, `posts`, `metric_snapshots`, `comments`: original imported objects as described below.

The fixed inventory covers the eight channel folders listed in root AGENTS.md. Episodes are direct `reels/` subdirectories; references in `references/<episode>` associate when that episode exists. Legacy production elsewhere is still indexed as channel assets with null episode. Kinds are `reference`, `sfx`, `audio`, `video`, `graphic`, `document`, `source`; these are path/extension classifications, not verified creative judgments. Reference paths take precedence over media extension. `search` queries file paths/document bodies. `search-notes` retrieves annotation payloads with the same channel/kind/text/limit filters.

Scanning reads files without moving them. It skips symlinks, hidden files/directories and directories named `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.cache`, `cache`, `frames`, `render-frames`, `render_frames`, `rendered-frames`, `tmp`, `temp`. Results list excluded directories and per-file errors; inspect those before treating an inventory as complete. Existing rows are marked absent when files disappear, preserving historical relationships. Changed size/mtime triggers rehashing; unchanged size+mtime reuses the hash. This is an incremental catalog, not forensic verification against deliberate timestamp manipulation. Keep source-clock verification separate.

## CRM inbound event envelope

Only the following keys are accepted. Export is a richer dashboard snapshot and is **not** itself an inbound event file.

```json
{
  "schema_version": 1,
  "posts": [
    {
      "id": "crm:instagram:account-a:post-123",
      "channel_id": "tiny-diff-club",
      "episode_id": "tiny-diff-club/02-reference-recreation",
      "platform": "instagram",
      "account_id": "account-a",
      "format": "reel",
      "organic": true,
      "published_at": "2026-11-16T08:00:00Z",
      "pattern": "mistake-reveal-fix",
      "url": "https://example.com/post-123",
      "campaign_id": "trial-01"
    }
  ],
  "metric_snapshots": [
    {
      "id": "crm:instagram:post-123:2026-11-17T08:00Z",
      "post_id": "crm:instagram:account-a:post-123",
      "observed_at": "2026-11-17T08:00:00Z",
      "metric_definition": "instagram-reels-insights-v2026-11",
      "metrics": {"views": 1200, "likes": 50, "comments": 0, "shares": null},
      "source": "CRM export"
    }
  ],
  "comments": [
    {
      "id": "crm:comment-789:v1",
      "post_id": "crm:instagram:account-a:post-123",
      "observed_at": "2026-11-17T08:00:00Z",
      "text": "Can you show the fix?",
      "topic": "follow-up-request"
    }
  ],
  "annotations": [
    {
      "id": "review:tiny-diff-club:02:v1",
      "channel_id": "tiny-diff-club",
      "episode_id": "tiny-diff-club/02-reference-recreation",
      "kind": "edit_review",
      "body": {"observation": "Inspect the actual delivered encode before adding a verified lesson", "status": "unreviewed"}
    }
  ]
}
```

All arrays are optional. `id` must be a nonempty stable string. Use source-system IDs with namespaces; never regenerate IDs randomly on every sync. Records are immutable: identical ID+payload retries insert nothing, while changed content under an existing ID rejects the **entire import transaction**. Supply a new revision ID for corrections; this version does not collapse revisions or delete previous events. Avoid silently correcting timestamps or identities on old records. Downstream consumers must interpret revisions explicitly.

Posts require all fields shown through `published_at`; extra descriptive fields are retained in the raw payload. `organic` must be a JSON boolean. Keep platform/account/format vocabularies consistent because cohorts match these values exactly. Channel and episode IDs must exist, and the episode must belong to that channel. Publication is asserted by an explicit imported post record, not verified against a platform in this version. Import only confirmed posts.

Metric snapshots may include `metric_definition`, a nonempty versioned identifier for the platform metric meanings and collection methodology (for example, `instagram-reels-insights-v2026-11`). Missing definition IDs are accepted as provisional history, but cannot produce performance candidates. The adapter should maintain a definition registry explaining exactly what each field measures. Differing definition IDs never share a report baseline.

Metric snapshots and comments require `id`, `post_id`, `observed_at`; observations must follow or equal publication. Timestamps require an explicit timezone, preferably UTC `Z`. Metrics require a `metrics` object. Supported keys: `views`, `likes`, `comments`, `shares`, `saves`, `reach`, `impressions`, `watch_time_seconds`, `completion_rate`, `retention_rate`. Values are finite nonnegative numbers or null; rates are fractions between 0 and 1. Missing, null and zero remain distinct. The CRM adapter must map the platform's meanings explicitly; total and average watch time are not interchangeable. Unknown extra metric keys are rejected instead of silently guessed.

Comments require `text`. Store only what is useful for production; the default example omits user identity. This version does not compute sentiment or infer demographic facts.

Annotations require `id`, `channel_id`, `kind`, `body`; `episode_id` is optional. Supported kinds: `reference_audit`, `beat_sheet`, `edit_review`, `pattern`, `experiment`, `lesson`. `body` must be a JSON object, so it can carry timed beats, source asset IDs/hashes, evaluation evidence, rights, cue layers and uncertainty. The CLI validates relational ownership and kind, not the creative body schema. Use the skill's beat-sheet format for authored audits. `annotate` accepts one annotation object or an array; it wraps the import envelope automatically. Annotating a file does not mutate its original asset/rights row.

## Performance candidate report

The report chooses one latest observation per post in each window (ties use lexically greatest snapshot ID): [24,48), [72,96), [168,192) hours after publication. Other observations remain stored. Baselines compare the same **channel + platform + account + format + organic flag + age window + metric definition** and exclude the candidate itself. At least three peer posts are required to calculate views lift. Median baseline of zero yields unknown lift, not infinity. A lift of at least 2 produces `candidate_for_test: true`; this is an initial heuristic, not statistical significance or proof of what caused performance.

Engagement per view is computed only when views > 0 and likes/comments/shares/saves are all known. Views remain platform-defined. No cross-platform aggregate rank is produced. The report provides observations to plan experiments across other channels, preserving each channel's brand and cast. It never publishes, changes production defaults or automatically promotes a pattern. CRM adapters, scheduled collection, retention curves, experiment assignment, semantic retrieval and automatic editing are future integration work.
