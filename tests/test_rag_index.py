from src.rag_index import build_index, query


def test_group_code_join_key_question_surfaces_the_right_grounding():
    col = build_index()
    results = query(col, "what is the real join key for clients", n_results=1)
    assert "group_code" in results[0]["text"]
    assert "ONLY correct join key" in results[0]["text"]


def test_maintenance_code_question_surfaces_real_spec_grounding():
    col = build_index()
    results = query(col, "what does maintenance code 024 mean in the enrollment file", n_results=3)
    combined = " ".join(r["text"] for r in results)
    assert "024" in combined
