import json
from evaluator.pipeline import EvaluationPipeline

def main():
    convo = json.load(open("examples/conversation.json"))
    ctx = json.load(open("examples/context.json"))
    p = EvaluationPipeline()
    print(json.dumps(p.evaluate(convo, ctx), indent=2))

if __name__ == "__main__":
    main()
