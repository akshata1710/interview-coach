# Golden set

Human-labeled sessions that the judge is measured against. The headline number is the share of judge scores within ±0.5 of the human score.

## Labeling

Open **http://localhost:5173/label**, enter a labeler name, and score each session. Expect about 2 minutes per session, so roughly an hour for the 30 seeds.

The labeling page shows what the judge sees: the problem, the platform's facts (optimal complexity, test results), the conversation and the final code. It never shows the judge's scores or what a seed was built to test, so your labels stay independent.

**Guidelines that keep labels consistent:**

- **Score from the anchors, not from intuition.** 0, 2 and 4 are defined for every dimension; 1 and 3 sit between them.
- **Score each dimension on its own.** Bad code doesn't lower a prompting score; asking for edge cases counts under Verification only.
- **Score what the session shows.** If the candidate never asked for edge cases, Verification is low, even if the code handles them.
- **Label in one or two sittings.** Your standard drifts across days.
- **Use the notes field** when a score was hard to call. Those are the sessions to discuss if a second person labels.

**Get a second labeler for 10 sessions if you can.** The report then shows how often two humans agree with each other. That's the realistic ceiling for the judge, and it makes the headline number far more credible.

## Measuring the judge

```bash
cd backend && source .venv/bin/activate
python -m evals.run_eval                   # writes golden/REPORT.md and golden/report.json
python -m evals.run_eval --write-baseline  # once you're happy: record the numbers CI compares against
```

The first run makes about 15 API calls per session, roughly 450 for 30 sessions. Results are cached in `golden/cache/` by a hash of the session, rubric, judge code and model, so re-running after changing only labels costs nothing.

**Read the Largest disagreements table in `REPORT.md` before changing anything.** Each row is either a judge mistake (fix the rubric anchors or prompts) or a label you'd score differently on a second look. Change one or the other, never both just to make the number go up.

## The CI gate

`.github/workflows/judge-eval.yml` re-runs the eval when the judge, rubric, eval code or golden set changes. It fails when:

- fewer than 80% of judge scores are within ±0.5 of the human score;
- any one dimension with 5 or more scores falls below 60%;
- the mean absolute error is above 0.75;
- overall agreement drops more than 5 points below `baseline.json`.

All of these live in `thresholds.yaml`. The gate needs an `ANTHROPIC_API_KEY` repository secret. Until 20 sessions are labeled, it reports without failing.

## Adding sessions

- **From the app:** on any scored report, click **Add this session to the golden set**. Ideally someone who hasn't seen the report labels it.
- **Seeds:** `python tools/seed_golden.py` regenerates the 30 seeds. `seed_manifest.json` records what each was built to be (for example, a strong prompter who wrote buggy code), so after labeling you can check whether the judge and you both caught it.
