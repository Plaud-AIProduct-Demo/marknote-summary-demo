import pytest
from fastapi.testclient import TestClient
from marknote.api import router, MarkType
from main import app

def test_mark_note_summary_time():
    client = TestClient(app)
    payload = {
        "summary_id": "test123",
        "scenario": "meeting",
        "language": "zh",
        "mark_time": 60,
        "time_range": 30,
        "content": "[0-60][张三] 这是会议内容1\n[61-120][李四] 这是会议内容2",
        "mark_type": "time"
    }
    response = client.post("/mark_note/summary", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "llm_summary" in data or "error" in data

def test_mark_note_summary_text():
    client = TestClient(app)
    payload = {
        "summary_id": "test456",
        "scenario": "meeting",
        "language": "zh",
        "mark_time": 60,
        "time_range": 30,
        "content": "[0-60][张三] 这是会议内容1",
        "mark_type": "text",
        "notes": "用户补充笔记内容"
    }
    response = client.post("/mark_note/summary", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "llm_summary" in data or "error" in data
