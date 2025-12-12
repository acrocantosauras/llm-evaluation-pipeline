from evaluator.relevance import relevance_score

def test_relevance():
    ans = "Ibuprofen can cause stomach upset."
    ctx = {"chunks":[{"text": "Ibuprofen may cause stomach upset."}]}
    assert relevance_score(ans, ctx) > 0.5
