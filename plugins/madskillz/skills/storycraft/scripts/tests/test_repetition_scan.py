import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import repetition_scan as rs


def test_tokenize_lowercases_and_splits_words():
    assert rs.tokenize("Jacob nodded, then JACOB ran!") == ["jacob", "nodded", "then", "jacob", "ran"]


def test_find_repeated_ngrams_flags_filler_beat():
    text = "And Jacob nodded. " * 3 + "The wind blew softly over the quiet hills."
    grams = rs.find_repeated_ngrams(text, min_count=3)
    assert any(g["ngram"] == "and jacob nodded" and g["count"] >= 3 for g in grams)


def test_find_repeated_ngrams_clean_text_is_clean():
    text = "A goblin sneezed. The kettle wept. Stars argued about nothing in particular."
    assert rs.find_repeated_ngrams(text, min_count=3) == []


def test_find_crutches_flags_banned_phrase_even_below_default_threshold():
    text = "She nodded. He nodded once more."
    crutches = rs.find_crutches(text, banned=["nodded"], min_count=4)
    assert any(c["phrase"] == "nodded" and c["banned"] for c in crutches)


def test_chapter_opening_similarity_detects_same_opening():
    a = "The sun rose over the marsh. Grendel woke up grumpy."
    b = "The sun rose over the marsh. Then something else entirely happened."
    sims = rs.chapter_opening_similarity([a, b], sentences=1, threshold=0.5)
    assert sims and sims[0]["a"] == 0 and sims[0]["b"] == 1


def test_scan_returns_all_three_sections():
    report = rs.scan(["And Jacob nodded. " * 3], banned=["nodded"])
    assert set(report) == {"repeated_ngrams", "crutches", "similar_openings"}


def test_find_crutches_banned_uses_word_boundaries():
    # "and" must NOT be counted inside "sand"/"candy"
    crutches = rs.find_crutches("The sand and the candy and the band.", banned=["and"], min_count=99)
    hit = [c for c in crutches if c["phrase"] == "and"]
    assert hit and hit[0]["count"] == 2 and hit[0]["banned"]


def test_find_crutches_filters_function_word_stopwords():
    text = "the the the the the of of of of of really really really really really"
    phrases = {c["phrase"] for c in rs.find_crutches(text, min_count=4)}
    assert "the" not in phrases and "of" not in phrases   # grammatical stopwords filtered
    assert "really" in phrases                            # genuine crutch word kept
