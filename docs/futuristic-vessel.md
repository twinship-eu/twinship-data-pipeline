# Futuristic vessel data

The futuristic vessel is a synthetic diesel-electric RoRo demonstrator. Its data is public and is the only vessel data in this repository. It shows how the TwinShip ontology covers a diesel-electric propulsion system with green energy and efficiency technologies, and how voyages with weather are represented. The values come from design data and simulation, not from a vessel in operation.

## Input files

All three files are in `data/`.

### `RoRo Futuristic Vessel KG Working File.xlsx`

The vessel's components, one sheet per system type:

| Sheet | Content |
| --- | --- |
| `GENSET (ENGINE + GENERATOR)` | Generator sets |
| `ESS ENERGY STORAGE SYSTEM` | Batteries and DC bus converters |
| `SCR SELECTIVE CATALYTIC REDUCT` | SCR units |
| `PMS MAIN SWITCHBOARD AC` | Power management system |
| `AUXLD AUXILIARY LOAD` | Auxiliary (hotel and ship service) load |
| `OSP SHORE CONNECTION` | Shore power |
| `EM ELECTRIC MOTOR FREQ CONVENT` | Electric motors, frequency converters and motor shafts |
| `CPP CONTROLABLE PITCH PROPELLER` | Propellers |
| `GRS GATE RUDDER SYSTEM`, `TH THRUSTER` | Gate rudders, thrusters |
| `FUEL` | Fuels |
| `WASP WIND ASSIST PROPULSION`, `ALS AIR LUBRICATION SYSTEM`, `DW DYNAMIC WING` | Efficiency enhancement systems |
| `AMMCELL AMMONIA CELL` | Ammonia fuel cell |
| `ALL INFO`, `Engine Parameters` | Column descriptions and data types (the shared schema description) |

Each component sheet has a header row with the `TWINSHIP-…` column names and a row with the data type. `dagster_pipeline/futuristic_extraction.py` reads it and the shared harmonisation library turns it into RDF. The sheet layout differs from the format of other input files, which is why the futuristic vessel has its own extraction code.

### `RoRo Futuristic Vessel Voyages.dat`

A time series of crossings between Rotterdam and Immingham in 2024: 2,928 records, one every 3 hours, as whitespace-separated columns after three header lines (title, column names, a dashed line). `dagster_pipeline/assets/futuristic_voyages.py` reads it.

| Column | Unit | Meaning |
| --- | --- | --- |
| `i` | | Record number (1-based) |
| `Rot/Imm(1/2)` | | Direction: 1 = Rotterdam to Immingham, 2 = Immingham to Rotterdam |
| `dist_trav` | nm | Distance travelled in the crossing |
| `dist_rem` | nm | Distance remaining |
| `Vs_SOG` | kn | Speed over ground |
| `cpp PID` | % | Propeller pitch |
| `draft`, `trim` | m | Draft and trim |
| `Hs` | m | Significant wave height |
| `Tp` | s | Peak wave period |
| `th_wave` | deg | Wave direction (from, relative to north) |
| `beta` | deg | Wave direction relative to the heading |
| `Uw` | m/s | Wind speed |
| `th_wind` | deg | Wind direction (from, relative to north) |
| `b_wind` | deg | Wind direction relative to the heading |
| `propRPM`, `propSHP`, `SHPtot` | rpm, kW, kW | Propeller speed, propeller shaft power, total shaft power |
| `FOC`, `CO2`, `NOx` | ton/h | Fuel consumption and emissions, conventional fuel |
| `FOCbio`, `CO2bio`, `NOxbio` | ton/h | The same for biofuel |
| `FOCNH`, `CO2NH`, `NOxNH` | ton/h | The same for ammonia |

The file does not state its start time, time step, port positions or direction coding. These are constants in `futuristic_voyages.py`:

| Setting | Value | Source |
| --- | --- | --- |
| Record 1 | 2024-01-01 00:00 UTC | Copernicus hindcast start, confirmed by the data provider |
| Time step | 3 hours | As above |
| Ports | Rotterdam (NLRTM) 51.98 N 4.00 E, Immingham (GBIMM) 53.63 N 0.19 W | Approximate public positions |
| Direction coding | 1 and 2 as in the table above | Confirmed by the data provider |

### `RoRo Futuristic Vessel Operational Modes.ttl`

Hand-written RDF with the vessel's operational modes, which the spreadsheet does not contain yet:

- 4 **engine modes** per genset (`FV-GN-1` and `FV-GN-2`, linked with `tws:hasEngineMode`), each with lower and upper power bounds, and `tws:twEngineModeCount` on the gensets.
- 4 **engine speed bins**, 3 **draft modes** and 3 **trim modes**: ordinal bins without numeric ranges.
- `owl:AllDifferent` statements declaring the individuals in each group distinct.

**All values are placeholders**: the mode count of 4 and all power bounds (0.0 kW) are not real data, and the bins have no ranges yet. Query results involving engine modes or bins only show the structure. The real values are to come from the statistical model (engine modes) and the engine-propeller combinator diagram (speed bins), ideally through the spreadsheet.

`vessel_rdf_graph` adds the file to the futuristic vessel's graph, so it is validated with SHACL and stored in the `components` graph together with the components.

## How the voyages are built

A crossing runs from a record with `dist_trav` = 0 to a record with `dist_rem` = 0. The file holds 266 complete crossings (133 in each direction) of 11 records each, 180 nm in total.

- **Voyage**: one per crossing, with departure and arrival port, estimated start and end time, total distance and mean speed.
- **Waypoint**: one per record, with time and position. The position is interpolated linearly between the two ports from `dist_trav`.
- **Voyage leg**: one between each pair of consecutive waypoints (10 per voyage, 18 nm each), with distance, speed and the wind and wave conditions of its start record.

Only columns with a matching ontology property are converted: time and position, `Vs_SOG`, `Uw` (converted to knots) and `th_wind`, `Hs` and `th_wave`. Propeller pitch, draft, trim, `Tp`, `beta`, `b_wind`, propeller speed and power, fuel consumption and emissions are not converted.

### Known issues in the data

- **Timing**: the timestamps follow the 3-hour weather steps, so a crossing spans 30 hours although 180 nm at the file's constant 18 knots takes 10. The file's own timing is kept and not corrected. Start and end times are therefore *estimated* times (`twVoyageEstimatedStartTime`, `twVoyageEstimatedEndTime`).
- **Heading**: `beta + th_wave` implies a heading of 135° for direction 1 and 315° for direction 2, while the rhumb line from Rotterdam to Immingham is about 303° (and 123° in reverse). The stated direction coding is kept; the pipeline logs a warning for every run.
- **Unfinished crossing**: the last two records (2927 and 2928) start a crossing that does not end in the file and are skipped, with a warning.

## In GraphDB

The pipeline loads everything into the repository `futuristic-vessel`, in three named graphs:

| Named graph | Content | Written by |
| --- | --- | --- |
| `https://twin-ship.eu/graphs/futuristic-vessel/ontology` | The TwinShip ontology | `graphdb_upload` |
| `https://twin-ship.eu/graphs/futuristic-vessel/components` | The vessel and its components, and the operational modes (placeholders) | `graphdb_upload` |
| `https://twin-ship.eu/graphs/futuristic-vessel/voyages` | Voyages, legs, waypoints, ports and weather | `futuristic_voyage_upload` |

Individuals have IRIs under `https://twin-ship.eu/individuals/futuristic-vessel/`. The vessel is `…/FV-RR-1`, and voyage individuals are named `Voyage-0001`, `Voyage-0001-Leg01`, `Voyage-0001-WP01`, `Voyage-0001-Leg01-Wind` and so on, and `Port-NLRTM`, `Port-GBIMM`.

Queries without `FROM` or `GRAPH` see all three graphs and the triples GraphDB infers. A query restricted with `FROM <graph>` loses the inferred triples unless it also adds `FROM <http://www.ontotext.com/implicit>`.

The voyage data is about 60,000 triples, against about 350 for the components and operational modes. Keeping time series like this in the knowledge graph works for this small synthetic dataset, but does not scale to vessels with high-frequency sensor data. The named graphs are a temporary structure until the time series moves to a time-series database queried through a virtual knowledge graph (OBDA).

## Visual graphs

`docs/visual-graphs/` has four SPARQL `CONSTRUCT` queries for GraphDB's Visual Graph:

| Query | Shows |
| --- | --- |
| `01-components.rq` | The vessel, its components (`ido:partOf`) and how they connect (`ido:connectedTo`) |
| `02-component-details.rq` | 01 plus component types (without the generic AC, DC and ESD), direct physical connections, fuels and where they connect, and the gensets' engine modes. Technical values appear in the node details. |
| `03-voyages.rq` | A few voyages (default 3; change the `LIMIT`) with their ports and legs |
| `04-voyage-weather.rq` | A voyage with its legs and each leg's wind and wave conditions (about 40 nodes per voyage) |

Queries 01 and 02 read only explicit triples (`FROM <http://www.ontotext.com/explicit>`) to keep inferred types and properties out of the picture.

To use one: log in to the GraphDB Workbench as `twinship-developer` (see *Logging in* in the README), select the `futuristic-vessel` repository, open *Explore → Visual graph → Create graph config*, set *Start with* to *Graph query results* and paste the query. Graph configs cannot be imported, so each one has to be created by hand.

Creating a graph config needs write access: for a read-only user such as `futuristic-vessel-user`, the Workbench does not let you edit the query. Configs are saved per user, so a config created as `twinship-developer` is listed only for that user.

## Provenance and licence

The data is licensed CC BY 4.0 (see `REUSE.toml`).

The weather columns of the voyage file (`Hs`, `Tp`, `th_wave`, `Uw`, `th_wind`) are sampled from a Copernicus hindcast. Attribution: *Generated using E.U. Copernicus Marine Service Information. Contains modified Copernicus Climate Change Service information 2024.* Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains.

The voyage conversion was ported from the `twinship-futuristic-vessel` generator; the pipeline's output matches it triple for triple, apart from the IRIs (`tests/test_futuristic_voyages.py`).
