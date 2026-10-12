# rewire/ — sg-urban-spine Silver ↔ TWA ontology mapping

[sg-urban-spine](https://github.com/tetratorus/saas-middleware/tree/sg-urban-spine) keeps a canonical Singapore city model ("Silver") as GeoParquet tables
and publishes a JSON-LD context (`spec/silver/context.jsonld`) so Silver rows can be lifted into The World Avatar (TWA) knowledge graph.
This folder checks that mapping against the real OWL files in this repo (OntoPlot, OntoZoning, OntoPlanningRegulation, OntoBuiltEnv,
all `owl:versionInfo 1`) and holds the corrected version. **No ontology file is changed**, so no version bump is needed.

| File | What it is |
|---|---|
| `check_context.py` | Loads the four OWL files with rdflib (505 terms) and checks a context / `tables.yaml` / mapping. |
| `silver_twa_mapping.yaml` | Authoritative Silver column → TWA property path (most TWA quantities are `om:Measure` nodes, not literals). |
| `context.jsonld` | Corrected drop-in for the spine's `spec/silver/context.jsonld` (only literal-valued terms). |
| `tests/` | pytest: corrected files pass; the spine's v0 context fails with exactly the errors below. |

```bash
pip install rdflib pyyaml pytest
python rewire/check_context.py                                   # 0 problems
python rewire/check_context.py --context <spine>/spec/silver/context.jsonld --tables <spine>/spec/silver/tables.yaml   # 12 problems
pytest rewire/tests
```

## Fixes needed in the spine (`spec/silver/context.jsonld`, `spec/silver/tables.yaml`)

| Silver column / table | v0 mapping | Problem | Correct TWA mapping |
|---|---|---|---|
| `plot_id` | `@id` (global alias) | Every table has its own key; `"P1"` is not an IRI | Drop the alias; IRIs come from `id_bridge` (`source=twa_kg`, `source_id`=IRI) |
| `area_m2` | `ontoplot:hasPlotArea` | ObjectProperty → `om:Area` | `ontoplot:hasPlotArea/om:hasValue/om:hasNumericalValue` (unit `om:squareMetre`) |
| `zone_type` | `ontozoning:hasZone` | Not defined | `ontozoning:hasLandUseType/rdf:type` (class, e.g. `ontozoning:Residential`) |
| `gross_plot_ratio` | `opr:hasMaximumPlotRatio` | Not defined | `^opr:appliesTo/opr:allowsGrossPlotRatio/om:hasValue/om:hasNumericalValue`; null → `opr:isAwaitingDetailedGPREvaluation true` |
| `max_storeys` | `opr:allowsStoreyAggregate` | Not defined; OPR has no storey limit | Leave in spine vocab (gap; candidate new OPR term) |
| `max_height_m` | (unmapped) | — | `opr:allowsBuildingHeight/om:hasValue/om:hasNumericalValue` (`opr:BuildingHeight`, relative to `opr:Datum`) |
| `site_coverage` | `opr:hasMaximumSiteCoverage` | Not defined | `opr:allowsSiteCoverage/om:hasValue/om:hasNumericalValue` |
| `setback_m` | `opr:hasSetback` | Not defined | `opr:requiresSetback/om:hasValue/om:hasNumericalValue` (`opr:Setback`, Front/Rear/Side subclasses) |
| `height_m` | `ontobuiltenv:hasHeight` | Not defined | `bldg:measuredHeight` (CityGML 2.0, what CEAAgent queries) |
| `storeys` | `ontobuiltenv:hasNumberOfFloors` | ObjectProperty → `NumberOfFloors` | `ontobuiltenv:hasNumberOfFloors/ontobuiltenv:hasValue` |
| `use_type` | `ontobuiltenv:hasPropertyUsage` | ObjectProperty → `PropertyUsage` | `ontobuiltenv:hasPropertyUsage/rdf:type` (`Office`, `Hotel`, …; max `hasUsageShare`) |
| `year_built` | (unmapped) | — | `ontobuiltenv:hasConstructionDate/time:hasBeginning/time:inXSDDateTimeStamp` |
| `buildings.iri` | `ontobuiltenv:Building` | Not a class | `bldg:Building` (TWA KG buildings are CityGML 2.0 buildings) |
| `districts.iri` | `ontobuiltenv:District` | Not a class | None (`ontobuiltenv:AdministrativeDistrict` is an admin area, not a morphology district) |
| `zoning.iri` | `ontozoning:Zone` | Exists, but land use attaches to `ontoplot:Plot` | `ontoplot:Plot` |
| Gold `gfa.allowable.allowable_gfa_m2` | (unmapped) | — | `ontoplot:hasMaximumPermittedGFA/om:hasValue/om:hasNumericalValue` |
| Gold building GFA `gfa_m2` | (unmapped) | — | `ontobuiltenv:hasGFA` (float literal) |

A flat JSON-LD context can't express property paths, so the spine should adopt `context.jsonld` from here for literal terms and
`silver_twa_mapping.yaml` (or an R2RML/OBDA rendering of it) for the path-valued columns.

## Gaps found inside TWA (reported, not changed)
- `TheWorldAvatar/Deploy/stacks/Singapore/gfa.obda` uses `plot:hasCalculatedGFA` and `plot:containsBuilding`. Neither is in OntoPlot.
- `building_usage.obda` uses `ontobuiltenv:hasUsageLabel`, which is not in OntoBuiltEnv (the TBox uses `rdfs:label`).
- OntoPlanningRegulation has no storey-limit term, but URA Master Plan regulations use storey limits.
