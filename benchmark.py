import json
import time

from evaluator.pipeline import EvaluationPipeline


def run_bench(n=5):
    with open("examples/conversation.json") as f:
        convo = json.load(f)
    with open("examples/context.json") as f:
        ctx = json.load(f)
    p = EvaluationPipeline()
    t0 = time.time()
    for _ in range(n):
        p.evaluate(convo, ctx)
    print("Avg time per iteration:", (time.time() - t0) / n)


if __name__ == "__main__":
    run_bench()
