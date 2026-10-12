import importlib.util
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_context", HERE.parent / "check_context.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
TERMS = cc.load_terms()


def _load(p):
    return json.loads(p.read_text()) if p.suffix == ".jsonld" else yaml.safe_load(p.read_text())


def test_corrected_context_and_mapping_validate():
    assert cc.check_context(_load(HERE.parent / "context.jsonld"), TERMS) == []
    assert cc.check_mapping(_load(HERE.parent / "silver_twa_mapping.yaml"), TERMS) == []


def test_spine_v0_context_has_exactly_the_reported_errors():
    errs = cc.check_context(_load(HERE / "fixtures/spine_context_v0.jsonld"), TERMS)
    bad = sorted(e.split(":")[0] for e in errs)
    assert bad == sorted(["plot_id", "area_m2", "zone_type", "gross_plot_ratio", "max_storeys", "site_coverage",
                          "setback_m", "height_m", "storeys", "use_type"])


def test_spine_v0_tables_bad_class_iris():
    errs = cc.check_tables(_load(HERE / "fixtures/spine_tables_v0.yaml"), TERMS)
    assert sorted(e.split(".")[1] for e in errs) == ["buildings", "districts"]


def test_mapping_paths_use_real_terms():
    T = "https://www.theworldavatar.com/kg/"
    assert TERMS[T + "ontoplanningregulation/allowsGrossPlotRatio"] == "object"
    assert TERMS[T + "ontobuiltenv/hasGFA"] == "datatype"
    assert TERMS[T + "ontoplot/hasMaximumPermittedGFA"] == "object"
    assert T + "ontozoning/hasZone" not in TERMS
