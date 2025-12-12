def estimate_cost(conversation):
    input_tok = conversation.get("input_tokens", 0)
    output_tok = conversation.get("output_tokens", 0)
    cost = (input_tok/1000)*0.00015 + (output_tok/1000)*0.0006
    return round(cost, 8)
