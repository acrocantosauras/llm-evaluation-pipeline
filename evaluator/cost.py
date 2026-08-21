def estimate_cost(conversation):
    input_tok = conversation.get("input_tokens", 0)
    output_tok = conversation.get("output_tokens", 0)

    price_in = 0.00015
    price_out = 0.0006

    cost = (input_tok / 1000) * price_in + (output_tok / 1000) * price_out
    return round(cost, 8)
