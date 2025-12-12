from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

def relevance_score(answer: str, context: dict) -> float:
    ctx_text = " ".join([c.get("text", "") for c in context.get("chunks", [])])
    emb_a = model.encode(answer, convert_to_tensor=True)
    emb_c = model.encode(ctx_text, convert_to_tensor=True)
    score = util.cos_sim(emb_a, emb_c).item()
    return round((score + 1) / 2, 4)
