"""Validate sg-urban-spine JSON-LD context / Silver mapping against the TWA OWL files in this repository.

  python rewire/check_context.py                      # check rewire/context.jsonld + rewire/silver_twa_mapping.yaml
  python rewire/check_context.py --context X.jsonld   # check another context (e.g. the spine's spec/silver/context.jsonld)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import rdflib
import yaml
from rdflib.namespace import OWL, RDF

ROOT = Path(__file__).resolve().parents[1]
OWL_FILES = ["ontology/ontoplot/OntoPlot.owl", "ontology/ontozoning/OntoZoning.owl",
             "ontology/ontoplanningregulation/OntoPlanningRegulation.owl", "ontology/ontobuiltenv/OntoBuiltEnv.owl"]
TWA_PREFIX = "https://www.theworldavatar.com/kg/"


def load_terms() -> dict[str, str]:
    """IRI -> 'class' | 'object' | 'datatype' for every term declared in the four TWA ontologies."""
    g = rdflib.Graph()
    for f in OWL_FILES:
        g.parse(ROOT / f)
    kinds = {}
    for kind, t in (("class", OWL.Class), ("object", OWL.ObjectProperty), ("datatype", OWL.DatatypeProperty)):
        for s in g.subjects(RDF.type, t):
            if isinstance(s, rdflib.URIRef):
                kinds.setdefault(str(s), kind)
    return kinds


def expand(curie: str, prefixes: dict) -> str:
    curie = curie.lstrip("^")
    p, _, local = curie.partition(":")
    return prefixes[p] + local if p in prefixes and not curie.startswith("http") else curie


def check_context(ctx: dict, terms: dict) -> list[str]:
    """Return problems: TWA IRIs that do not exist, or literal-valued terms bound to object properties/classes."""
    c = ctx["@context"]
    prefixes = {k: v for k, v in c.items() if isinstance(v, str) and v.endswith(("/", "#"))}
    errors = []
    for col, v in c.items():
        if col.startswith("@") or col in prefixes:
            continue
        iri_or_curie = v["@id"] if isinstance(v, dict) else v
        if iri_or_curie.startswith("@"):
            if iri_or_curie == "@id":
                errors.append(f"{col}: aliased to @id globally; hub keys differ per table, use id_bridge IRIs instead")
            continue
        iri = expand(iri_or_curie, prefixes)
        if not iri.startswith(TWA_PREFIX):
            continue
        kind = terms.get(iri)
        if kind is None:
            errors.append(f"{col}: {iri_or_curie} is not defined in the TWA ontologies")
        elif col[:1].islower() and kind != "datatype":
            errors.append(f"{col}: {iri_or_curie} is an owl:{'ObjectProperty' if kind == 'object' else 'Class'}, "
                          "cannot carry a literal column value")
    return errors


def check_tables(tables: dict, terms: dict) -> list[str]:
    errors = []
    for name, t in tables["tables"].items():
        iri = t.get("iri")
        if iri and iri.startswith(TWA_PREFIX) and terms.get(iri) != "class":
            errors.append(f"tables.{name}.iri: {iri} is not a class in the TWA ontologies")
    return errors


def check_mapping(m: dict, terms: dict) -> list[str]:
    prefixes, external = m["prefixes"], set(m.get("external", []))
    errors = []

    def term(curie, want, where):
        if curie is None or curie.lstrip("^").split(":")[0] in external:
            return
        iri = expand(curie, prefixes)
        if terms.get(iri) not in want:
            errors.append(f"{where}: {curie} expected {'/'.join(want)}, found {terms.get(iri)}")

    sections = [(f"tables.{n}", t.get("class"), t["columns"]) for n, t in m["tables"].items()]
    sections += [(f"gold.{n}", None, cols) for n, cols in m.get("gold", {}).items()]
    for where, cls, cols in sections:
        term(cls, {"class"}, f"{where}.class")
        for col, spec in cols.items():
            path = spec.get("path") or []
            for i, step in enumerate(path):
                last = i == len(path) - 1
                term(step, {"datatype"} if last else {"object"}, f"{where}.{col}.path[{i}]")
            term(spec.get("value_class"), {"class"}, f"{where}.{col}.value_class")
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--context", default=here / "context.jsonld")
    ap.add_argument("--tables", default=None, help="spine spec/silver/tables.yaml")
    ap.add_argument("--mapping", default=here / "silver_twa_mapping.yaml")
    a = ap.parse_args(argv)
    terms = load_terms()
    errors = check_context(json.loads(Path(a.context).read_text()), terms)
    if a.tables:
        errors += check_tables(yaml.safe_load(Path(a.tables).read_text()), terms)
    errors += check_mapping(yaml.safe_load(Path(a.mapping).read_text()), terms)
    for e in errors:
        print("FAIL", e)
    print(f"{len(errors)} problem(s); {len(terms)} TWA terms loaded")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
