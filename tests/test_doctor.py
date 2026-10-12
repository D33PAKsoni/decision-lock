from decision_lock.doctor import main


def test_doctor_does_not_call_api_or_show_key(monkeypatch, capsys):
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "private-key-sentinel")
    assert main() == 0
    output = capsys.readouterr().out
    assert "private-key-sentinel" not in output
    assert "No network request" in output


def test_doctor_missing_key_has_actionable_error(monkeypatch, capsys):
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert main() == 1
    assert "needs an API key" in capsys.readouterr().out
