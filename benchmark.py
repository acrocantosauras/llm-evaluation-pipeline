import time, json
from evaluator.pipeline import EvaluationPipeline

def run_bench(n=5):
    convo = json.load(open("examples/conversation.json"))
    ctx = json.load(open("examples/context.json"))
    p = EvaluationPipeline()
    t0 = time.time()
    for _ in range(n):
        p.evaluate(convo, ctx)
    print("Avg time:", (time.time() - t0) / n)

if __name__ == "__main__":
    run_bench()
