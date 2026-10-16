"""Append public, evidence-backed modeling events; never reconstruct missing history."""
import argparse, datetime, hashlib, json, re, uuid
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / 'tools/pipeline/modeling_training_config.json'
KINDS = {'intent', 'action_started', 'action_finished', 'inspection', 'user_feedback', 'correction', 'gap'}
STATUSES = {'pending', 'succeeded', 'failed', 'partial', 'interrupted', 'unknown', 'not_applicable'}

def _auto_start_context(root, episode, payload):
    """2026-10-10 (the user wants these trajectories to fine-tune a small 3D-modelling model): every action_started now snapshots, with no manual step,
    (1) the generator script as it is at the start (immutable copy by hash; also kept when the run crashes),
    (2) the reference images it depends on (explicit payload['reference'] list, else art/references/** image files named in the script) and the lock file (audit + structure reading + dimensions + material truth table + detail inventory)
        of that reference directory, as the text stood at that moment,
    (3) parent_action_id = the previous action_finished of the same script in this episode (the version chain; a dataset pair is parent -> child).
    Missing files are skipped silently; nothing here raises."""
    op = payload.get('operation') if isinstance(payload.get('operation'), dict) else {}
    ev = []; sp = op.get('script')
    if sp and Path(sp).is_file():
        ev.append(dict(path=str(sp), role='script_at_start'))
        try: text = Path(sp).read_text(encoding='utf-8', errors='replace')
        except Exception: text = ''
        refs = [Path(x) for x in (payload.get('reference') or []) if Path(x).is_file()]; locks = []
        for c in re.findall(r"art/references/[A-Za-z0-9_\-./]+", text):
            q = PROJECT / c.rstrip('/.')
            if q.is_file() and q.name == 'lock.md': locks.append(q)
            elif q.is_dir() and (q / 'lock.md').exists(): locks.append(q / 'lock.md')
            if q.is_file() and q.suffix.lower() in ('.png', '.jpg', '.jpeg') and not payload.get('reference'): refs.append(q)
        for lk in list(locks):
            if not payload.get('reference'):
                for n in ('reference.png',):
                    if (lk.parent / n).is_file(): refs.append(lk.parent / n)
        seen = set()
        for r in refs[:4]:
            if r not in seen and r.stat().st_size < 12_000_000: seen.add(r); ev.append(dict(path=str(r), role='reference_image'))
        for lk in locks[:1]: ev.append(dict(path=str(lk), role='reference_lock'))
        mods = set(); todo = list(re.findall(r'(?m)^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)', text))                                                  # in-house modules the script needs (tools/pipeline/*.py): snapshot them too, depth 2, so a sample can be replayed later
        for _ in range(2):
            nxt = []
            for mname in todo:
                q = PROJECT / 'tools/pipeline' / (mname + '.py')
                if mname not in mods and mname != 'record_modeling_step' and q.is_file():
                    mods.add(mname)
                    try: nxt += re.findall(r'(?m)^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)', q.read_text(encoding='utf-8', errors='replace'))
                    except Exception: pass
            todo = nxt
        for mname in sorted(mods)[:14]: ev.append(dict(path=str(PROJECT / 'tools/pipeline' / (mname + '.py')), role='kit_at_start'))
        stem = Path(sp).stem; ep_dir = root / 'episodes' / episode; parent = None
        if ep_dir.is_dir():
            for f in sorted(ep_dir.glob('*.json')):
                try: e = json.loads(f.read_text(encoding='utf-8'))
                except Exception: continue
                if e.get('kind') == 'action_finished' and e.get('technical_status') in ('succeeded', 'partial'):
                    scr = None
                    for v in e.get('evidence') or []:
                        if isinstance(v, dict) and v.get('role') == 'actual_script': scr = Path(str(v.get('path'))).stem; break
                    if scr == stem: parent = e.get('action_id')
        if parent and 'parent_action_id' not in payload: payload['parent_action_id'] = parent
    return ev

def append_event(episode, payload):
    import os
    root = Path(os.environ.get('MODELING_DATASET_ROOT') or json.loads(CONFIG.read_text(encoding='utf-8-sig'))['dataset_root'])   # 2026-10-01: F: disk errors - events can be staged elsewhere and merged later
    if not episode or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in episode):
        raise ValueError('episode must be an ASCII slug')
    if payload.get('kind') not in KINDS:
        raise ValueError('invalid event kind')
    if payload.get('technical_status', 'pending') not in STATUSES:
        raise ValueError('invalid technical status')
    # No environment dumps, credentials or complete request headers belong here.
    for forbidden in ('api_key', 'authorization', 'access_token', 'secret', 'password', 'environment_dump'):
        if forbidden in {str(k).lower() for k in payload}:
            raise ValueError('credential-bearing field prohibited')
    target = root / 'episodes' / episode
    target.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    if payload.get('kind') == 'action_started':
        extra = _auto_start_context(root, episode, payload)
        payload['evidence'] = list(payload.get('evidence') or []) + [x for x in extra if x['path'] not in {y.get('path') for y in payload.get('evidence') or []}]
    event = dict(payload)
    event.update(schema_version=2, episode_id=episode,
                 event_id=str(uuid.uuid4()), recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    event.setdefault('technical_status', 'pending')
    event.setdefault('internal_visual_status', 'unreviewed')
    event.setdefault('user_acceptance', 'unreviewed')
    event.setdefault('evidence', [])
    for evidence in event['evidence']:
        p = Path(evidence['path'])
        if not p.is_file():
            raise FileNotFoundError(p)
        h = hashlib.sha256()
        # Store immutable content-addressed snapshots on F, not just mutable D paths.
        with p.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                h.update(block)
        digest = h.hexdigest()
        dest = root / 'evidence' / digest[:2] / (digest + p.suffix.lower())
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            import shutil
            shutil.copy2(p, dest)
        evidence.update(sha256=digest, archived_path=str(dest), bytes=dest.stat().st_size)
    # One immutable JSON per event avoids multi-process append races.
    path = target / (event['recorded_at'].replace(':', '-') + '_' + event['event_id'] + '.json')
    with path.open('x', encoding='utf-8') as f:
        json.dump(event, f, ensure_ascii=False, indent=2)
    return path

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--episode', required=True)
    p.add_argument('--event-file', required=True, help='Reviewed, credential-free public event JSON')
    a = p.parse_args()
    print(append_event(a.episode, json.loads(Path(a.event_file).read_text(encoding='utf-8-sig'))))
