"""Lightweight correlation and timing helpers for one research execution."""
from contextvars import ContextVar
from time import perf_counter

_research_run_id = ContextVar("research_run_id", default="unknown")

def set_run_id(run_id):
    return _research_run_id.set(run_id)

def reset_run_id(token):
    _research_run_id.reset(token)

def log(message):
    print(f"[run {_research_run_id.get()}] {message}")

class Timer:
    def __init__(self, label):
        self.label = label

    def __enter__(self):
        self.started = perf_counter()
        return self

    def __exit__(self, exc_type, exc, traceback):
        log(f"{self.label}: {perf_counter() - self.started:.2f}s")
