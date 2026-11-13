# Five-minute SmartFlow AI demonstration

## Before the presentation

Run `python -m streamlit run app.py` from the project directory. Open the printed
local URL, select **NS Rush** in the sidebar, keep the default signal settings and
click sidebar **Load Saved Model**. This loads a genuine previously trained model;
call it a saved run, never a new live training run. Confirm the saved analytics and
comparison charts load. Have `results/training_charts.png` and
`results/comparison_charts.png` available as an offline fallback.

The included experiment is 1,000 episodes on NS Rush. To rehearse a tiny new run
without replacing it, use separate CLI output/model paths documented in README.
In-app training and comparison replace the corresponding default result files.
Back up `models/` and `results/` if you want to retain the bundled experiment.

## Minute 1 — introduction

Open **Overview**. Say: “A fixed equal timing plan cannot respond to uneven arrivals.
Our objective is to reduce accumulated queues while keeping signal transitions
safe. This is a small educational simulator, not a deployed traffic controller.”
Point out the six demand scenarios and clarify that Heavy is intentionally beyond
capacity. Explain that negative percentage results are displayed honestly.

## Minute 2 — RL architecture

Select **RL Explanation**. Explain the four queue buckets, phase and exact timing
state. Action 0 keeps green, action 1 requests a switch. Show the reward equation:
each queued vehicle costs 0.1 per second and a switch costs 0.5. Explain that the
Bellman update uses learned future values, and the environment masks unsafe actions.
Emphasize that no longer-queue switching rule substitutes for Q-learning.

## Minute 3 — training and learning

Select **Learning Analytics**. State explicitly: “These are the recorded results
of our completed 1,000-episode training run.” Show raw and rolling reward,
served-vehicle waiting, queues, epsilon and throughput; inspect a Q-table row.
Discuss first/last 100 reward means (−1384.677 and −371.261) as diagnostics.

For a live training demonstration, go to **Train RL Agent**, choose **Training
episodes = 10** and **Training episode seconds = 60**, then **Start Training**.
Watch actual episode progress and metrics. This creates a genuinely new, small
model and replaces default artifacts; do it after presenting the bundled results
or use the saved fallback. A short run is not expected to outperform fixed timing.
For a five-minute assessment, showing the saved run plus explaining the real
training controls is safer than retraining the full experiment on stage.

## Minute 4 — live simulation

Select **Live Traffic Simulation** and choose **Trained Q-Learning** under
**Controller**. Click **Step Forward**, then **Start**, then **Pause**. Observe
queue counts, vehicle IDs, elapsed time and yellow/all-red transitions. Click
**Resume**, adjust **Simulation speed**, then **Reset**. Reset clears the live
episode but preserves the trained model. Changing scenario/controller starts a
new live episode deliberately. Vehicles shown correspond to actual queues;
recent departure labels represent served records, not decorative motion.

Select **Fixed-Time** to demonstrate its repeated 15-second greens. The trained
controller acts greedily from the loaded Q-table and does not learn during playback.
The sidebar's seed gives repeatable arrivals for equal scenario/configuration.

For the enhanced control-center view, highlight the selected legal Q-value in
the **AI decision monitor**. Explain that the current preview belongs to the
current state; **Last executed** records the preceding decision and earned reward.
Click its expander to inspect that exact state. Demonstrate a paused **Step Forward**
updating all four queue lines. **Resume** is available only when paused.
Enable **Synchronized comparison** to watch fixed-time and learned controllers on
the same saved in-memory arrival trace. This playback does not replace saved
evaluation files. Toggle **Animate vehicle movements** off if needed; motion
interpolates real vehicle records and is not a physical traffic model.

## Minute 5 — fair comparison

Select **Performance Comparison**. Review saved results first. Explain 20 unseen
seeds per scenario, equal duration, identical pre-generated traffic and no learning
during evaluation. NS Rush mean queue: 29.346 → 12.113, reduction 58.73%; completed
wait: 24.860 → 10.228 seconds; throughput: 312.60 → 342.40 vehicles. Show Balanced
queue worsening by 19.63% as a generalization limitation, not an error to hide.

To demonstrate a new comparison, retain the original model, choose **NS Rush**
only, set **Evaluation seeds per scenario = 3**, **First unseen seed = 200000**,
then click **Run Comparison**. Results will differ from the saved 20-seed run.
Use **Export Evaluation Results** for the actual new CSV. Explain remaining queues
and the paired-difference standard error. Finish on **Project Information** and
show editable team details and report downloads.

## Fallbacks and troubleshooting

- Missing model: click sidebar **Load Saved Model**; if the file is absent, train
  with the CLI or dashboard. The app never silently supplies an untrained RL policy.
- Slow training: show saved history/charts and identify them as a prior run.
- Broken saved file: preserve it for diagnosis, retrain into a new path, and load
  only a valid structured NPZ model. Do not relabel invented numbers as results.
- Port busy: launch `python -m streamlit run app.py --server.port 8502` and use the
  new printed URL.
- Internet unavailable: all simulation and training work locally after dependencies
  are installed; the reports' external reference links are optional during demo.

Rehearse timed playback and exports in a real browser using the validation checklist.
