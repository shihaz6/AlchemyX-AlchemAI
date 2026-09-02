from time import perf_counter

try:
    from ..telemetry import log
except ImportError:
    from src.alchemyx.telemetry import log


def usage_tokens(response):
    usage = _get(response, "usage")
    if usage is None:
        return None

    for field in (
        "total_tokens",
        "tokens",
        "input_tokens",
        "prompt_tokens",
        "total",
    ):
        value = _get(usage, field)
        if value is not None:
            return value

    return None


def estimate_tokens(texts):
    return sum(len(text.split()) for text in texts)


def log_voyage_embedding(model, input_type, inputs, response, started):
    _log_block(
        "Voyage Embedding",
        [
            ("model", model),
            ("input_type", input_type),
            ("inputs", len(inputs)),
            *_usage_lines(response, inputs),
            ("duration", f"{perf_counter() - started:.2f}s"),
        ],
    )


def log_voyage_rerank(model, candidates, response, started):
    returned_count = len(_get(response, "results") or [])
    _log_block(
        "Voyage Rerank",
        [
            ("model", model),
            ("candidates", candidates),
            ("returned", returned_count),
            *_usage_lines(response, []),
            ("duration", f"{perf_counter() - started:.2f}s"),
        ],
    )


def _usage_lines(response, estimate_inputs):
    tokens = usage_tokens(response)
    if tokens is not None:
        return [("tokens", tokens)]

    if estimate_inputs:
        return [("tokens_estimate", estimate_tokens(estimate_inputs))]

    return [("tokens", "unavailable")]


def _log_block(title, fields):
    log(f"[{title}]")
    for key, value in fields:
        log(f"{key}={value}")


def _get(value, field):
    if isinstance(value, dict):
        return value.get(field)
    return getattr(value, field, None)
