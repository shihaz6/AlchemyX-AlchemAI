import sys
from pathlib import Path


def test_streamlit_backend_import_contract():
    project_root = Path(__file__).parents[1]
    sys.path.insert(0, str(project_root / "src" / "alchemyx"))
    import backend_adapter

    assert callable(backend_adapter.run_research)
    assert callable(backend_adapter.search_archive)
    assert callable(backend_adapter.create_system)


def test_chat_arrow_renders_fake_backend_result(monkeypatch):
    project_root = Path(__file__).parents[1]
    sys.path.insert(0, str(project_root / "src" / "alchemyx"))
    import backend_adapter

    calls = []

    def fake_run_research(question):
        calls.append(question)
        return {
            "answer": f"Answer for {question}",
            "iterations": 1,
            "stop_reason": "sufficient_evidence",
            "sufficient": True,
            "sources_retrieved": 0,
            "steps": [],
            "sources": [],
        }

    monkeypatch.setattr(backend_adapter, "run_research", fake_run_research)

    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(project_root / "app" / "streamlit_app.py").run()
    app.text_area[0].set_value("What is in the archive?")
    app.button[0].click().run()

    assert not app.exception
    assert app.session_state.research_question == "What is in the archive?"

    app.text_area[0].set_value("What happened next?")
    app.button[0].click().run()

    assert not app.exception
    assert app.session_state.research_question == "What happened next?"
    assert calls == ["What is in the archive?", "What happened next?"]


def test_empty_question_is_rejected():
    project_root = Path(__file__).parents[1]
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(project_root / "app" / "streamlit_app.py").run()
    app.button[0].click().run()

    assert not app.exception
    assert any("Please enter a question" in item.value for item in app.warning)


def test_backend_failure_is_rendered(monkeypatch):
    project_root = Path(__file__).parents[1]
    sys.path.insert(0, str(project_root / "src" / "alchemyx"))
    import backend_adapter

    def fail(_question):
        raise RuntimeError("backend test failure")

    monkeypatch.setattr(backend_adapter, "run_research", fail)

    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(project_root / "app" / "streamlit_app.py").run()
    app.text_area[0].set_value("Trigger failure")
    app.button[0].click().run()

    assert any("backend test failure" in item.message for item in app.exception)


def test_archive_search_uses_adapter(monkeypatch):
    project_root = Path(__file__).parents[1]
    sys.path.insert(0, str(project_root / "src" / "alchemyx"))
    import backend_adapter

    calls = []

    def search(query, top_k=5):
        calls.append((query, top_k))
        return [
            {
                "source_doc": "archive.md",
                "chunk_index": 2,
                "score": 0.91,
                "rank_score": 0.91,
                "score_type": "rank_score",
                "text": "Archive evidence.",
            }
        ]

    monkeypatch.setattr(backend_adapter, "search_archive", search)

    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(project_root / "app" / "streamlit_app.py").run()
    app.radio[0].set_value("Explore Archive").run()
    app.text_input[0].set_value("archive evidence")
    app.button[0].click().run()

    assert not app.exception
    assert calls == [("archive evidence", 5)]
