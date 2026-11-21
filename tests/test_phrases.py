"""Reusable phrases memory + clipboard history."""
from src.models.phrases import save_phrase, search_phrases, list_top, seed_if_empty, count_phrases, delete_phrase
from src.models.clipboard_history import add_clip, list_clips, clear_clips
def test_seed_loads():
    assert seed_if_empty() >= 20 and count_phrases() >= 20
    assert any("ألم" in r["text"] for r in search_phrases("complaint", "ألم"))
    assert any("تسوس" in r["text"] for r in search_phrases("diagnosis", "تسوس"))
    assert any("حشوة" in r["text"] for r in search_phrases("procedure", "حشوة"))
def test_save_dedupes_and_counts():
    pid = save_phrase("complaint", "TEST_UNIQUE_PHRASE_XYZ ألم اختبار")
    assert pid
    save_phrase("complaint", "TEST_UNIQUE_PHRASE_XYZ ألم اختبار")
    rows = search_phrases("complaint", "TEST_UNIQUE_PHRASE_XYZ")
    assert rows and rows[0]["usage_count"] >= 2
    assert save_phrase("complaint", "ab") is None  # too short
    delete_phrase(pid)
def test_top_ordered_by_usage():
    save_phrase("symptom", "TEST_TOP_PHRASE_XYZ تورم اختبار")
    save_phrase("symptom", "TEST_TOP_PHRASE_XYZ تورم اختبار")
    save_phrase("symptom", "TEST_TOP_PHRASE_XYZ تورم اختبار")
    top = list_top("symptom", 10)
    assert any(r["text"] == "TEST_TOP_PHRASE_XYZ تورم اختبار" for r in top)
    rows = search_phrases("symptom", "TEST_TOP_PHRASE_XYZ")
    delete_phrase(rows[0]["id"])
def test_clipboard_history():
    clear_clips()
    assert add_clip("first clip test") is True
    assert add_clip("first clip test") is None  # consecutive duplicate
    add_clip("second clip test")
    clips = list_clips(20)
    assert [c["text"] for c in clips][:2] == ["second clip test", "first clip test"]
    clear_clips(); assert list_clips() == []
