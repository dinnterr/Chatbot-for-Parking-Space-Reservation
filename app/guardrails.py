from transformers import pipeline

# for guard rails mechanism
guard_model = pipeline(
    "text-classification",
    model="unitary/toxic-bert",
    top_k=None
)

def guardrail_check(text: str) -> bool:
    result = guard_model(text)[0]

    for r in result:
        label = r["label"].lower()
        score = r["score"]

        # sensitive if toxic / unsafe confidence is high
        if ("toxic" in label or "severe" in label) and score > 0.7:
            return True

    return False