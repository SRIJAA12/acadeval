import pytest

from app.services import corpus_matcher as cm
from app.services.corpus_quality import boilerplate_cells, is_template_row


def _row(pid, title, domain, abstract, algorithms="", technologies="", keywords="", **extra):
    return {
        "Project_ID": pid, "Title": title, "Domain": domain, "Sub_Domain": "General",
        "Abstract": abstract, "Algorithms": algorithms, "Technologies": technologies,
        "Frameworks": "", "Tools": "", "Hardware": "", "Dataset_Used": "",
        "Programming_Languages": "", "Keywords": keywords, "Publication_Type": "Journal Article",
        "Notes": "", **extra,
    }


def _install_corpus(rows):
    boiler = boilerplate_cells(rows)
    projects = [cm._project_from_row(r, i, boiler) for i, r in enumerate(rows) if not is_template_row(r)]
    index = cm._build_index(projects)
    for p in projects:
        cm._with_norm(p, index)
    cm._CATALOG, cm._INDEX = projects, index


@pytest.fixture(autouse=True)
def _reset():
    yield
    cm.reset_corpus_cache()


def _corpus():
    rows = [
        _row("FARM", "Smart Loan Advisor for Farmers", "Agriculture",
             "Credit scoring and crop loan advice for small farmers using repayment history",
             "Random Forest", "Python, React", "farmer, loans, credit"),
        _row("CITR", "Citr V9 React Tutorial", "Artificial Intelligence",
             "student project app for Brian Holt's Complete Intro to React",
             "Random Forest", "Git, JavaScript, React"),
        _row("PIZZA", "Pizza Ordering App", "Retail",
             "Online pizza ordering with delivery tracking for restaurants",
             "", "Python, React, Git", "pizza, ordering, delivery"),
    ]
    # Many unrelated projects share the generic stack, so Python/React/Git are common.
    for i in range(60):
        rows.append(_row(f"G{i}", f"Topic {i} Platform", f"Domain{i % 12}",
                         f"Study number {i} about subject{i} and area{i}",
                         "", f"Python, React, Git, Tool{i}", f"subject{i}"))
    return rows


FARMER_TARGET = dict(
    target_id="TARGET",
    target_title="KISAN CASH",
    target_domain="Agriculture",
    target_sub_domain="General",
    target_entities={"technologies": ["Python", "React", "Redis"], "algorithms": ["Random Forest"],
                     "applications": ["farmer loans"]},
    target_abstract="An app giving small farmers credit scoring and crop loan advice",
)


def test_farmer_project_matches_farmer_project_not_stack_twins():
    _install_corpus(_corpus())
    results = cm.find_similar_corpus_projects(**FARMER_TARGET)
    assert results, "expected at least one match"
    assert results[0]["id"] == "FARM"
    ids = [r["id"] for r in results]
    assert "CITR" not in ids
    assert "PIZZA" not in ids


def test_generic_only_overlap_is_not_a_match():
    _install_corpus(_corpus())
    results = cm.find_similar_corpus_projects(
        target_id="T", target_title="Zeta Gadget", target_domain="Unrelated", target_sub_domain="",
        target_entities={"technologies": ["Python", "React", "Git"]},
        target_abstract="something about quokka husbandry",
    )
    assert results == []


def test_generic_entities_are_flagged_and_ranked_last():
    _install_corpus(_corpus())
    results = cm.find_similar_corpus_projects(**FARMER_TARGET)
    detail = results[0]["shared_entities_detail"]
    by_name = {d["name"]: d for d in detail}
    assert by_name["python"]["generic"] is True
    assert by_name["react"]["generic"] is True
    assert detail[0]["generic"] is False or all(d["generic"] for d in detail)


def test_template_rows_are_never_returned():
    rows = _corpus() + [
        _row("FILLER", "Optimization Project 36", "Agriculture",
             "Credit scoring and crop loan advice for small farmers using repayment history",
             "Random Forest", "Python, React", "farmer, loans, credit",
             Publication_Type="Conceptual academic project"),
    ]
    _install_corpus(rows)
    ids = [r["id"] for r in cm.find_similar_corpus_projects(**FARMER_TARGET)]
    assert "FILLER" not in ids
    assert "FARM" in ids


def test_boilerplate_requires_repetition_across_many_domains():
    rows = []
    for i in range(30):  # filler spread over many domains
        rows.append({"Domain": f"D{i % 10}", "Algorithms": "classification, regression"})
    for i in range(30):  # legitimate cluster inside a single domain
        rows.append({"Domain": "Robotics", "Algorithms": "Fast-SLAM, Kalman Filter"})
    boiler = boilerplate_cells(rows, columns=("Algorithms",))
    assert "classification, regression" in boiler["Algorithms"]
    assert "Fast-SLAM, Kalman Filter" not in boiler["Algorithms"]


def test_internal_entity_keys_are_not_matched():
    assert cm._target_entity_set({"sub_domain": "Machine Learning", "_effective_abstract": "x",
                                  "algorithms": ["CNN"]}) == {"cnn"}
