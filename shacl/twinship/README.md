# TwinShip SHACL shapes

Closed-world SHACL validation profile for TwinShip vessel component instance data (engines, gensets, propellers, gearboxes, fuels, energy and efficiency systems).

## What the shapes check

- Every component is `ido:partOf` at least one `tws:VesselSystem`.
- Numeric and string data properties have the datatype given by their `rdfs:range` in the ontology, with at most one value per component.
- Coded values use only the documented codes (`0`, `1`). An unknown value is left out; the `-1` marker is not accepted.
- `tws:consume` points to a `tws:Fuel`, and fuels have a label.
- Labels are strings or language-tagged strings, with at most one per language.

## Relation to the ontology

The shapes complement the OWL class restrictions in `model/`; they do not replace them. OWL restrictions are open-world: a missing or extra value is not an error. The shapes check what a concrete dataset actually contains. They are not part of the OWL semantics of the ontology and are not imported by any module.

Shape IRIs use the namespace `https://twin-ship.eu/twinship/shapes#` (prefix `twsh:`). They constrain terms in the ontology namespace `https://twin-ship.eu/twinship#` (prefix `tws:`). `twinship-shapes.ttl` holds the version header.

## Running

Validate with the ontology as the ontology graph and RDFS inference. Without them, `sh:targetClass` and `sh:class` do not match subclass instances (for example a `tws:CPP` is not checked as a `tws:PropellerSystem`).

The build (`scripts/generate_website.sh`, or `uv run python scripts/merge_shapes.py` on its own) merges the files into `build/twinship-shapes.ttl`, which is also published with the website:

```bash
uv run python scripts/merge_shapes.py
uv run pyshacl -s build/twinship-shapes.ttl -e build/twinship-core-complete.ttl -i rdfs <data.ttl>
```

From Python, parse all files into one graph and call `pyshacl.validate(data, shacl_graph=shapes, ont_graph=ontology, inference="rdfs")`.

`tests/test_shapes.py` checks that every term used in the shapes exists in the ontology and that every `sh:datatype` matches the property's `rdfs:range`.

## Scope

The shapes cover vessel components only. There are no shapes yet for the operational-context, operational-modes, weather-conditions, or statistics modules.

Rules that depend on a particular data producer or vessel configuration are not included. They stay in [twinship-data-pipeline](https://github.com/twinship-eu/twinship-data-pipeline). Examples: the closed list of allowed classes, propulsion-chain and PMS connectivity rules, the vessel completeness rules (at least one engine or genset, at least one propeller), and checks that both directions of the symmetric IDO connection properties are stated.

## Origin

Derived from `shacl/` in twinship-data-pipeline at commit `16a7a97`. Changes from that version:

- Shapes moved from `tws:` to the `twsh:` namespace.
- `connections.ttl` and `vessel.ttl` omitted (pipeline-specific).
- Labels accept language tags and several languages.
- `-1` is not accepted as an unknown marker: unknown values are left out of the data. Coded flags allow `0` and `1`, propeller blades must be at least 1 (the 1–7 limit is removed), and fuel density must be positive. `twGearboxShaftGenerator` previously allowed `0` and `1` only; the other coded flags allowed `-1`.
- `GearboxShape` targets `tws:GearboxSystem` (previously its subclasses plus `tws:PTO`, which is not a gearbox in the ontology). `PropellerShape` targets `tws:PropellerSystem` (previously any node with a propeller diameter).
- `ido:partOf` requires at least one `tws:VesselSystem` value, matching the OWL restriction, instead of requiring all values to be vessels. `BoilerShape` now also requires it.
