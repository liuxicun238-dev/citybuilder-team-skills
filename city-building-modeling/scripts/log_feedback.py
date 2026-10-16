"""Record what the USER said about a version, verbatim, in one command (2026-10-10).
  D:\\python\\python.exe tools/pipeline/log_feedback.py --episode axis-gate-g01-column --action column-inner-d07 --accept rejected --text "还是不符合" --visual "the collar is a drum of small ruffles; the reference is a few big rounded cloud lobes overhanging the base corners" [--scope "which part was judged"] [--image shot.png ...]
Rules that came out of an outside review of the first dataset (68 'user_rejection' samples: 4 were acceptances, 9 were requests, 12 had no visual content):
  --accept accepted | rejected | partial : a verdict on ONE version. 'next / continue / OK' = accepted. A new instruction or question ('make a flame breathing one', 'where is the pavilion?') is NOT feedback on a version: record it with --accept request (kept as intent, never used as a training label).
  --text   the user's own words, unchanged.
  --visual REQUIRED for rejected / partial (>= 25 characters): what is visibly wrong, concretely, as reference vs model (part, attribute, how it differs). This is what the training answer will be; the user's bare words ('still not right') carry no information on their own.
  --scope  which part / which view the verdict covers (optional for accepted).
  --image  the user's screenshots (copied into the evidence store)."""
import argparse, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from record_modeling_step import append_event
ap = argparse.ArgumentParser(); ap.add_argument('--episode', required=True); ap.add_argument('--action', required=True); ap.add_argument('--accept', required=True, choices=['accepted', 'rejected', 'partial', 'request', 'unreviewed'])
ap.add_argument('--text', required=True); ap.add_argument('--visual', default=''); ap.add_argument('--scope', default=''); ap.add_argument('--image', nargs='*', default=[]); a = ap.parse_args()
if a.accept in ('rejected', 'partial') and len(a.visual.strip()) < 25: sys.exit('REFUSED: a rejection needs --visual (>= 25 chars): say what is visibly wrong, reference vs model. The bare quote is not a training answer.')
ev = [dict(path=p, role='user_screenshot') for p in a.image if pathlib.Path(p).is_file()]
p = append_event(a.episode, dict(kind='user_feedback' if a.accept != 'request' else 'intent', action_id=a.action, source='user', user_request=a.text, user_acceptance=a.accept, visual_description=a.visual, acceptance_scope=a.scope, evidence=ev))
print(p)
