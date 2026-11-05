"""
Unit tests for the four-metric scoring layer (objective O2).
Run from the project root:   pytest -v
"""
import os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from solver import score_all, _pad, ARCSolver


# ─── _pad ──────────────────────────────────────────────────────

def test_pad_same_shape_unchanged():
    A, B = _pad([[1, 2], [3, 4]], [[5, 6], [7, 8]])
    assert A.shape == B.shape == (2, 2)
    assert A.tolist() == [[1, 2], [3, 4]]

def test_pad_mismatched_shapes_uses_sentinel():
    A, B = _pad([[1]], [[1, 2], [3, 4]])
    assert A.shape == B.shape == (2, 2)
    # unfilled cells become -1, which can never equal a colour 0-9
    assert A.tolist() == [[1, -1], [-1, -1]]
    assert B.tolist() == [[1, 2], [3, 4]]


# ─── exact ─────────────────────────────────────────────────────

def test_exact_identical_grids():
    g = [[0, 3], [3, 0]]
    assert score_all(g, g)["exact"] == 1.0

def test_exact_one_cell_off():
    assert score_all([[0, 3], [3, 1]], [[0, 3], [3, 0]])["exact"] == 0.0

def test_exact_shape_mismatch():
    assert score_all([[0, 3]], [[0, 3], [3, 0]])["exact"] == 0.0

def test_exact_single_cell():
    assert score_all([[7]], [[7]])["exact"] == 1.0


# ─── cell ──────────────────────────────────────────────────────

def test_cell_identical_is_one():
    g = [[1, 2], [3, 4]]
    assert score_all(g, g)["cell"] == 1.0

def test_cell_one_of_four_wrong():
    s = score_all([[0, 3], [3, 1]], [[0, 3], [3, 0]])
    assert s["cell"] == pytest.approx(0.75)

def test_cell_completely_wrong_is_zero():
    s = score_all([[1, 1], [1, 1]], [[2, 2], [2, 2]])
    assert s["cell"] == 0.0

def test_cell_shape_mismatch_penalised_not_crashed():
    s = score_all([[1]], [[1, 1], [1, 1]])
    assert s["cell"] == pytest.approx(0.25)


# ─── object (non-background cells) ─────────────────────────────

def test_object_identical_is_one():
    g = [[0, 5], [5, 0]]
    assert score_all(g, g)["object"] == 1.0

def test_object_ignores_matching_background():
    # Only the two non-zero cells count; one of them is wrong.
    s = score_all([[0, 5], [3, 0]], [[0, 5], [5, 0]])
    assert s["object"] == pytest.approx(0.5)

def test_object_all_background_falls_back_to_cell():
    s = score_all([[0, 0], [0, 0]], [[0, 0], [0, 0]])
    assert s["object"] == s["cell"] == 1.0


# ─── edit ──────────────────────────────────────────────────────

def test_edit_identical_is_one():
    g = [[1, 2], [3, 4]]
    assert score_all(g, g)["edit"] == 1.0

def test_edit_penalises_differences():
    s = score_all([[0, 3], [3, 1]], [[0, 3], [3, 0]])
    assert s["edit"] == pytest.approx(0.75)

def test_edit_never_negative():
    s = score_all([[1]], [[2, 2, 2], [2, 2, 2], [2, 2, 2]])
    assert s["edit"] >= 0.0


# ─── all four together ─────────────────────────────────────────

def test_perfect_prediction_scores_one_on_every_metric():
    g = [[0, 3], [3, 0]]
    s = score_all(g, g)
    assert s == {"exact": 1.0, "cell": 1.0, "object": 1.0, "edit": 1.0}

def test_metrics_are_ordered_exact_is_strictest():
    # A near-miss: exact collapses to 0 while the continuous metrics do not.
    # This is the measurement-artifact effect the project is auditing.
    s = score_all([[0, 3], [3, 1]], [[0, 3], [3, 0]])
    assert s["exact"] == 0.0
    assert s["cell"] > 0.5 and s["edit"] > 0.5

def test_all_metrics_in_unit_interval():
    for pred, gt in [([[1]], [[2]]), ([[0, 1]], [[1, 0], [0, 1]]), ([[5, 5]], [[5, 5]])]:
        for k, v in score_all(pred, gt).items():
            assert 0.0 <= v <= 1.0, f"{k} out of range"


# ─── H-Flip regression (the bug that made /api/solve report 0) ──

def test_hflip_prediction_scores_exact_one():
    """A horizontally flipped grid that matches ground truth must score exact = 1."""
    test_input = [[3, 0], [0, 3]]
    gt = [[0, 3], [3, 0]]
    hflip = [list(reversed(r)) for r in test_input]
    assert hflip == gt
    assert score_all(hflip, gt)["exact"] == 1.0


# ─── solver strategies ─────────────────────────────────────────

def test_solver_identity_detected():
    solver = ARCSolver(cache_dir="does_not_exist")
    task = {"train": [{"input": [[1, 2]], "output": [[1, 2]]}], "test": [{"input": [[3, 4]]}]}
    pred, name = solver.solve(task)
    assert name == "identity" and pred == [[3, 4]]

def test_solver_symmetry_h_detected():
    solver = ARCSolver(cache_dir="does_not_exist")
    task = {"train": [{"input": [[1, 2]], "output": [[2, 1]]}], "test": [{"input": [[3, 4]]}]}
    pred, name = solver.solve(task)
    assert name == "symmetry_h" and pred == [[4, 3]]

def test_color_map_rejects_unseen_colours():
    """Colours absent from the training map must not be blanked to 0."""
    solver = ARCSolver(cache_dir="does_not_exist")
    task = {"train": [{"input": [[1, 2]], "output": [[2, 1]]}], "test": [{"input": [[3, 4]]}]}
    assert solver._solve_color_map(task["train"], [[3, 4]]) is None

def test_solver_empty_task_fails_cleanly():
    solver = ARCSolver(cache_dir="does_not_exist")
    pred, name = solver.solve({"train": [], "test": []})
    assert pred is None and name == "failed"