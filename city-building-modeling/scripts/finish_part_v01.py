"""Hand-over gate for the training data (2026-10-10; the user fine-tunes a small model on these trajectories to give it 3D-modelling ability).
Run before every report to the user about a part:   D:\\python\\python.exe tools/pipeline/finish_part_v01.py --episode <episode id> [--no-build]
It checks the LATEST version of the episode and prints PASS / WARN / FAIL lines:
  FAIL (exit 1)  the latest action_finished has no archived generator script, no .blend, no render  |  the matching action_started has no reference image snapshot  |  no internal inspection (issues / next_change) was written for the latest version
  WARN           the version has a parent but the parent has neither an inspection nor a user_feedback (so the pair parent -> child has no stated reason and will NOT become a code_edit sample)
                 the reference lock snapshot is missing  |  a user_feedback is recorded for the parent but not for the latest version's acceptance (fine while the user has not answered)
Then rebuilds vlm-sft-v02 and code-sft-v01 and prints which samples this episode contributed, so a part that silently falls out of the datasets is noticed at once.
Record user words with tools/pipeline/log_feedback.py (verbatim), inspections with record_modeling_step.py (or the generator's own append_event call)."""
import argparse, json, pathlib, subprocess, sys, collections
import os
PRJ = pathlib.Path(__file__).resolve().parents[2]; ROOT = pathlib.Path(os.environ.get('MODELING_DATASET_ROOT') or r'G:/城市建造游戏/training-data')
ap = argparse.ArgumentParser(); ap.add_argument('--episode', required=True); ap.add_argument('--no-build', action='store_true'); a = ap.parse_args()
ep = ROOT / 'episodes' / a.episode
if not ep.is_dir(): print('FAIL episode folder not found', ep); sys.exit(1)
EV = []
for f in sorted(ep.glob('*.json')):
    try: EV.append(json.loads(f.read_text(encoding='utf-8')))
    except Exception: pass
EV.sort(key=lambda e: e.get('recorded_at', ''))
fails = []; warns = []; ok = []
fin = [e for e in EV if e['kind'] == 'action_finished' and e.get('technical_status') in ('succeeded', 'partial')]
if not fin: print('FAIL no successful action_finished in', a.episode); sys.exit(1)
last = fin[-1]; aid = last['action_id']; roles = collections.Counter(v.get('role') for v in last.get('evidence') or [] if isinstance(v, dict))
for need, label in (('actual_script', 'generator script'), ('editable_model', '.blend model'), ('actual_render', 'rendered views')):
    (ok if roles.get(need) else fails).append(f'latest version {aid}: {label} {"archived x%d" % roles[need] if roles.get(need) else "MISSING"}')
st = next((e for e in EV if e['kind'] == 'action_started' and e.get('action_id') == aid), None)
if st is None: fails.append(f'{aid}: no action_started event (parameters unknown)')
else:
    sr = collections.Counter(v.get('role') for v in st.get('evidence') or [] if isinstance(v, dict))
    (ok if sr.get('reference_image') else fails).append(f'{aid}: reference image snapshot {"x%d" % sr["reference_image"] if sr.get("reference_image") else "MISSING (pass reference=[...] in the action_started payload or name art/references/<dir>/reference.png in the script)"}')
    (ok if sr.get('reference_lock') else warns).append(f'{aid}: reference lock (structure reading / dimensions / material truth) snapshot {"present" if sr.get("reference_lock") else "missing - the lock.md of the reference folder is not named in the script"}')
    (ok if st.get('parent_action_id') else warns).append(f'{aid}: parent version {st.get("parent_action_id") or "none (first run of this script in the episode)"}')
    par = st.get('parent_action_id')
    if par:
        has_reason = any(e['kind'] in ('inspection', 'user_feedback') and e.get('action_id') == par for e in EV)
        (ok if has_reason else warns).append(f'parent {par}: stated reason for the change {"recorded" if has_reason else "MISSING - no inspection or user_feedback for the parent, so parent->child is not a training pair"}')
sk = collections.Counter(v.get('role') for v in (st or {}).get('evidence') or [] if isinstance(v, dict))
(ok if sk.get('kit_at_start') else warns).append(f'{aid}: in-house kit modules snapshotted x{sk.get("kit_at_start", 0)}' + ('' if sk.get('kit_at_start') else ' (script imports none, or the run predates the snapshot)'))
scr_txt = ''
for v in (st or {}).get('evidence') or []:
    if isinstance(v, dict) and v.get('role') == 'script_at_start' and v.get('archived_path'):
        try: scr_txt = pathlib.Path(v['archived_path']).read_text(encoding='utf-8', errors='replace')
        except Exception: pass
import re
if scr_txt:
    bad_paths = [m for m in re.findall(r"[\"'][A-Za-z]:[/\\][^\"']*", scr_txt) if 'art/references' not in m.replace('\\', '/') or True][:3]
    (warns if bad_paths else ok).append(f'{aid}: portability {"drive-letter paths in the script: " + str(bad_paths[:2]) + " (use Path(__file__).resolve().parents[2])" if bad_paths else "no absolute drive paths"}')
for e in EV:                                                                                                                                      # a rejection without a visual description is not a training answer
    if e['kind'] == 'user_feedback' and e.get('user_acceptance') in ('rejected', 'partial') and e.get('action_id') in (aid, (st or {}).get('parent_action_id')):
        vd = (e.get('visual_description') or e.get('acceptance_scope') or '').strip()
        (ok if len(vd) >= 25 else warns).append(f'user rejection of {e.get("action_id")}: visual description {"present" if len(vd) >= 25 else "MISSING - log it with log_feedback.py --visual (what is visibly wrong, reference vs model)"}')
insp = [e for e in EV if e['kind'] == 'inspection' and e.get('action_id') == aid]
if not insp: fails.append(f'{aid}: no internal inspection event (write issues[] and next_change with record_modeling_step.py BEFORE reporting)')
else:
    i = insp[-1]; tc = i.get('thumbnail_check') or []
    if not tc: fails.append(f'{aid}: inspection has no thumbnail_check (the 3 most prominent features of the reference and yes/no for each: [{{"feature":"...","present":true}}] x3, SKILL.md 6d item 00)')
    elif len(tc) < 3: fails.append(f'{aid}: thumbnail_check has only {len(tc)} features (need 3)')
    elif any(not t.get('present') for t in tc if isinstance(t, dict)): fails.append(f'{aid}: thumbnail_check has a NO ({[t.get("feature") for t in tc if isinstance(t, dict) and not t.get("present")]}) - keep working, do not hand over')
    else: ok.append(f'{aid}: thumbnail_check 3/3 present')
    (ok if i.get('issues') else warns).append(f'{aid}: inspection has {len(i.get("issues") or [])} issues'); (ok if i.get('next_change') else warns).append(f'{aid}: inspection next_change {"present" if i.get("next_change") else "missing"}')
for m in ok: print('PASS', m)
for m in warns: print('WARN', m)
for m in fails: print('FAIL', m)
if not a.no_build:
    for scr in ('build_vlm_dataset_v02.py', 'build_code_dataset_v01.py'):
        r = subprocess.run([sys.executable, str(PRJ / 'tools/pipeline' / scr)], capture_output=True, text=True, encoding='utf-8', errors='replace')
        line = (r.stdout.strip().splitlines() or [''])[-1]; print('BUILD', scr, 'ok' if r.returncode == 0 else 'FAILED', line[:160])
    for name, d in (('vlm-sft-v02', ROOT / 'datasets/vlm-sft-v02'), ('code-sft-v01', ROOT / 'datasets/code-sft-v01')):
        mp = d / 'meta.jsonl'
        if not mp.exists(): continue
        rows = [json.loads(l) for l in mp.read_text(encoding='utf-8').splitlines() if l.strip()]; mine = [r_ for r_ in rows if str(r_.get('family', '')).startswith(a.episode + '/')]
        c = collections.Counter((r_['file'], r_.get('label')) for r_ in mine)
        print('DATASET', name, f'{len(mine)} samples from {a.episode}:', dict(c) if c else 'NONE - this episode is not reaching the dataset (see noref_families.json / unmapped.json)')
        if not mine: warns.append(f'{name}: nothing from {a.episode}')
print('RESULT', 'FAIL - do not hand over' if fails else ('PASS with warnings' if warns else 'PASS'))
sys.exit(1 if fails else 0)
