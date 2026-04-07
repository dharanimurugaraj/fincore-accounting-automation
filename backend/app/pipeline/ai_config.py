# AI Model Configuration and Rates
# Rates are $/1M tokens

AI_MODELS = {
    "OpenAI": [
        {"name": "GPT-4o-mini (2024-07-18)", "input": 0.15, "output": 0.60, "context": 128000},
        {"name": "GPT-4o-mini", "input": 0.15, "output": 0.60, "context": 128000},
        {"name": "GPT-4.1 Nano", "input": 0.10, "output": 0.40, "context": 1047576},
        {"name": "Text Embedding 3 Large", "input": 0.13, "output": 0, "context": 8192},
        {"name": "gpt-oss-safeguard-20b", "input": 0.075, "output": 0.30, "context": 131072},
        {"name": "GPT-5 Nano", "input": 0.05, "output": 0.40, "context": 400000},
        {"name": "gpt-oss-120b", "input": 0.039, "output": 0.19, "context": 131072},
        {"name": "gpt-oss-20b", "input": 0.03, "output": 0.11, "context": 131072},
        {"name": "GPT-4.5 (Preview)", "input": 0, "output": 0, "context": 128000}, # Prices not specified in list
        {"name": "o1-preview", "input": 0, "output": 0, "context": 128000},
    ],
    "Anthropic": [
        {"name": "Claude Opus 4.6", "input": 5.00, "output": 25.00, "context": 1000000},
        {"name": "Claude Opus 4.1", "input": 15.00, "output": 75.00, "context": 200000},
        {"name": "Claude Sonnet 4.6", "input": 3.00, "output": 15.00, "context": 1000000},
        {"name": "Claude 3.7 Sonnet", "input": 3.00, "output": 15.00, "context": 200000},
        {"name": "Claude 3.5 Haiku", "input": 0.80, "output": 4.00, "context": 200000},
        {"name": "Claude 3 Haiku", "input": 0.25, "output": 1.25, "context": 200000},
    ],
    "Google": [
        {"name": "Gemini 1.5 Flash", "input": 0.075, "output": 0.30, "context": 1000000}, # Standard pricing
        {"name": "Gemini 1.5 Pro", "input": 1.25, "output": 5.00, "context": 2000000},
        {"name": "Gemma 3 27B (free)", "input": 0, "output": 0, "context": 131072},
        {"name": "Gemma 3 12B (free)", "input": 0, "output": 0, "context": 32768},
    ],
    "Meta": [
        {"name": "Llama 3.3 70B Instruct", "input": 0.10, "output": 0.32, "context": 131072},
        {"name": "Llama 4 Scout", "input": 0.08, "output": 0.30, "context": 327680},
        {"name": "Llama 3.2 3B Instruct", "input": 0.051, "output": 0.34, "context": 80000},
        {"name": "Llama 3.1 8B Instruct", "input": 0.02, "output": 0.05, "context": 131072},
    ]
}

def get_model_rate(model_name: str) -> dict:
    """ Finds input/output rates for a model name. """
    for provider, models in AI_MODELS.items():
        for m in models:
            if m["name"].lower() in model_name.lower():
                return m
    return {"input": 0.1, "output": 0.4} # Default fallback
