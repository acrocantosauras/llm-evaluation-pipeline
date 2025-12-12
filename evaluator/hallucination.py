from transformers import pipeline

nli = pipeline("text-classification", model="roberta-large-mnli", device=-1)

def split_sentences(text):
    return [s.strip() for s in text.replace("\\n"," ").split(". ") if s.strip()]

def hallucination_report(answer, context):
    premise = " ".join([c.get("text","") for c in context.get("chunks",[])])
    sentences = split_sentences(answer)

    supported = 0
    flags = []
    details = []

    for s in sentences:
        out = nli(f"{premise} </s></s> {s}")
        label = out[0]["label"].upper()

        if label in ("ENTAILMENT","LABEL_2"):
            supported += 1
        elif label in ("CONTRADICTION","LABEL_0"):
            flags.append({"sentence": s, "label": "CONTRADICTION"})
        else:
            flags.append({"sentence": s, "label": "UNSUPPORTED"})

        details.append({"sentence": s, "label": label, "score": out[0]["score"]})

    return {
        "fraction_supported": round(supported / len(sentences), 4),
        "flags": flags,
        "details": details
    }
