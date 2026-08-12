"""Three code eras of MTEB's Korean BM25 handling, run inside mteb 2.18.16.

  le_2_14_1  stopwords="en", stemmer_language="english" hardcoded for every language
  2_14_2     `kor` absent from _ISO3_TO_LANG -> word split, no stopwords, freq stopwords
  ge_2_18_12 `kor` -> (None, None, "char") -> character unigram, freq stopwords

Only the language table and the two explicit kwargs change; the task loader, the
scoring engine and the metrics are mteb's own throughout.
"""
import json, sys, time, mteb
from mteb.models.model_implementations import bm25 as bm25mod

TASKS, OUT = sys.argv[1].split(","), sys.argv[2]
ORIGINAL = dict(bm25mod._ISO3_TO_LANG)
KEEP = ("main_score","ndcg_at_10","recall_at_10","recall_at_100","map_at_10",
        "mrr_at_10","hit_rate_at_10","precision_at_10")
ERAS = {
    "le_2_14_1":  (True,  {"stopwords": "en", "stemmer_language": "english"}),
    "2_14_2":     (False, {}),
    "ge_2_18_12": (True,  {}),
}
with open(OUT, "a", encoding="utf-8") as f:
    for name in TASKS:
        for era, (keep_kor, kw) in ERAS.items():
            table = dict(ORIGINAL)
            if not keep_kor:
                table.pop("kor", None)
            bm25mod._ISO3_TO_LANG = table
            t0 = time.time()
            try:
                model = mteb.get_model("mteb/baseline-bm25s", **kw)
                tasks = mteb.get_tasks(tasks=[name], languages=["kor"])
                res = mteb.evaluate(model, tasks, overwrite_strategy="always",
                                    show_progress_bar=False)
                for tr in res.task_results:
                    for split, rows in tr.scores.items():
                        for r in rows:
                            rec = {"era": era, "task": tr.task_name, "split": split,
                                   "hf_subset": r.get("hf_subset"),
                                   "seconds": round(time.time()-t0, 1),
                                   **{k: r[k] for k in KEEP if k in r}}
                            f.write(json.dumps(rec, ensure_ascii=False)+"\n"); f.flush()
                            print(f"OK {name:34s} {era:11s} {r.get('hf_subset')} "
                                  f"ndcg={r.get('ndcg_at_10')}", file=sys.stderr, flush=True)
            except Exception as e:
                f.write(json.dumps({"era": era, "task": name,
                                    "error": f"{type(e).__name__}: {e}"[:300]}, ensure_ascii=False)+"\n")
                print(f"FAIL {name:34s} {era:11s} {type(e).__name__}: {str(e)[:80]}",
                      file=sys.stderr, flush=True)
