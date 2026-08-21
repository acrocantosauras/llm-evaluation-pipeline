import json

from evaluator.pipeline import EvaluationPipeline


def main():
    with open("examples/conversation.json") as f:
        convo = json.load(f)
    with open("examples/context.json") as f:
        ctx = json.load(f)
    pipeline = EvaluationPipeline()
    print(json.dumps(pipeline.evaluate(convo, ctx), indent=2))


if __name__ == "__main__":
    main()
