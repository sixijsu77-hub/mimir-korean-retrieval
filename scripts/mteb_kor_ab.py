"""A/B the `kor` mapping across every Korean task that has a published bm25s baseline."""
import json, sys, time, traceback, mteb
from mteb.models.model_implementations import bm25 as bm25mod

TASKS = sys.argv[1].split(",")
OUT = sys.argv[2]
ORIGINAL = dict(bm25mod._ISO3_TO_LANG)
KEEP = ("main_score","ndcg_at_10","recall_at_10","recall_at_100","map_at_10",
        "mrr_at_10","hit_rate_at_10","precision_at_10")

with open(OUT, "a", encoding="utf-8") as f:
    for name in TASKS:
        for label in ("with_kor", "without_kor"):
            table = dict(ORIGINAL)
            if label == "without_kor":
                table.pop("kor", None)
            bm25mod._ISO3_TO_LANG = table
            t0 = time.time()
            try:
                model = mteb.get_model("mteb/baseline-bm25s")
                tasks = mteb.get_tasks(tasks=[name], languages=["kor"])
                res = mteb.evaluate(model, tasks, overwrite_strategy="always",
                                    show_progress_bar=False)
                for tr in res.task_results:
                    for split, rows in tr.scores.items():
                        for r in rows:
                            rec = {"variant": label, "task": tr.task_name, "split": split,
                                   "hf_subset": r.get("hf_subset"),
                                   "languages": r.get("languages"),
                                   "seconds": round(time.time()-t0, 1),
                                   **{k: r[k] for k in KEEP if k in r}}
                            f.write(json.dumps(rec, ensure_ascii=False)+"\n"); f.flush()
                            print(f"OK {name:40s} {label:12s} ndcg@10={r.get('ndcg_at_10')}",
                                  file=sys.stderr, flush=True)
            except Exception as e:
                rec = {"variant": label, "task": name, "error": f"{type(e).__name__}: {e}"[:300]}
                f.write(json.dumps(rec, ensure_ascii=False)+"\n"); f.flush()
                print(f"FAIL {name:40s} {label:12s} {type(e).__name__}: {str(e)[:90]}",
                      file=sys.stderr, flush=True)
