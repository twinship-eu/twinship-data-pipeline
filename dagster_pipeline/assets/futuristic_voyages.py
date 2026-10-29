"""Voyage data for the futuristic vessel (patch, to be reworked for other input).

Reads the futuristic vessel's voyage time series (Rotterdam-Immingham, 2024,
one record per 3 h) and adds voyages, legs, waypoints, ports and weather to the
futuristic vessel's GraphDB repository, next to its components.

Ported from twinship-futuristic-vessel (fv2rdf/dat_io.py, voyage_model.py,
voyage_builder.py). Only columns with an existing ontology property are mapped:
position/time -> WayPoint, Vs_SOG -> leg speed, Uw/th_wind -> WindCondition,
Hs/th_wave -> WaveCondition (Hs as sea height). Propulsion, fuel, draft, trim
and Tp columns have no matching property and are not emitted.
"""

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from dagster import AssetExecutionContext, Config, MetadataValue, asset
from rdflib import RDF, RDFS, Graph, Literal
from rdflib.namespace import XSD

from dagster_pipeline.assets.harmonisation import graphdb_upload, vessel_partitions_def
from dagster_pipeline.resources import GraphDBClient
from twinship_harmonisation.constants import TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import create_twinship_uri
from twinship_harmonisation.utils import bind_namespaces

VOYAGE_NAMESPACE = "futuristic-vessel"
VESSEL_ID = "FV-RR-1"

# Dataset context the voyage file does not carry itself. Start time and 3 h
# step: Copernicus hindcast, record 1 = 2024-01-01 00:00 (confirmed by K.).
# Direction coding (column Rot/Imm, 1/2): K., email 2026-10-09. Port
# coordinates are approximate public values.
VOYAGE_START = datetime(2024, 1, 1, tzinfo=UTC)
VOYAGE_STEP_HOURS = 3

MS_TO_KNOTS = 1.943844
# Beyond this the file's implied heading contradicts the stated direction.
HEADING_TOLERANCE_DEG = 45

# Column order of the voyage file; the irregular header text is not parsed.
COLUMNS = [
    "i", "dir", "dist_trav", "dist_rem", "vs_sog", "cpp_pid", "draft", "trim",
    "hs", "tp", "th_wave", "beta", "uw", "th_wind", "b_wind",
    "prop_rpm", "prop_shp", "shp_tot",
    "foc", "co2", "nox", "foc_bio", "co2_bio", "nox_bio", "foc_nh", "co2_nh", "nox_nh",
]  # fmt: skip
HEADER_LINES = 3  # title, column names, dashed rule


@dataclass(frozen=True)
class Port:
    code: str
    name: str
    lat: float
    lon: float


PORTS = {
    "NLRTM": Port("NLRTM", "Rotterdam", 51.98, 4.0),
    "GBIMM": Port("GBIMM", "Immingham", 53.63, -0.19),
}
DIRECTION = {1: ("NLRTM", "GBIMM"), 2: ("GBIMM", "NLRTM")}


@dataclass
class Crossing:
    number: int  # 1-based sequence in the file
    direction: int
    departure: Port
    arrival: Port
    records: list[dict[str, float]] = field(default_factory=list)

    @property
    def total_nm(self) -> float:
        first = self.records[0]
        return first["dist_trav"] + first["dist_rem"]


# =============================================================================
# Reading and voyage logic
# =============================================================================


def read_records(path: str | Path) -> list[dict[str, float]]:
    """Return one dict per data row of the voyage file, keyed by COLUMNS."""
    records: list[dict[str, float]] = []
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if line_no <= HEADER_LINES or not line.strip():
                continue
            parts = line.split()
            if len(parts) != len(COLUMNS):
                raise ValueError(
                    f"{path}:{line_no}: expected {len(COLUMNS)} columns, got {len(parts)}"
                )
            records.append(dict(zip(COLUMNS, map(float, parts), strict=True)))
    return records


def record_time(i: float) -> datetime:
    """Record i (1-based) is the weather at start + step * (i - 1)."""
    return VOYAGE_START + timedelta(hours=VOYAGE_STEP_HOURS * (int(i) - 1))


def split_crossings(
    records: list[dict[str, float]],
) -> tuple[list[Crossing], list[dict[str, float]]]:
    """Group records into crossings (dist_trav == 0 .. dist_rem == 0).

    Returns (complete crossings, trailing records of an unfinished crossing).
    """
    crossings: list[Crossing] = []
    current: Crossing | None = None
    for rec in records:
        if rec["dist_trav"] == 0:
            direction = int(rec["dir"])
            dep, arr = DIRECTION[direction]
            current = Crossing(len(crossings) + 1, direction, PORTS[dep], PORTS[arr])
        if current is None:
            raise ValueError(
                f"record {int(rec['i'])} precedes the first departure (dist_trav != 0)"
            )
        current.records.append(rec)
        if rec["dist_rem"] == 0:
            crossings.append(current)
            current = None
    return crossings, (current.records if current else [])


def interpolate(dep: Port, arr: Port, fraction: float) -> tuple[float, float]:
    """Linear lat/lon interpolation; over ~180 nm indistinguishable from a rhumb line."""
    return dep.lat + (arr.lat - dep.lat) * fraction, dep.lon + (arr.lon - dep.lon) * fraction


def rhumb_bearing(dep: Port, arr: Port) -> float:
    """Constant-heading (loxodrome) bearing in degrees true."""
    lat1, lat2 = math.radians(dep.lat), math.radians(arr.lat)
    dlon = math.radians(arr.lon - dep.lon)
    dpsi = math.log(math.tan(math.pi / 4 + lat2 / 2) / math.tan(math.pi / 4 + lat1 / 2))
    return math.degrees(math.atan2(dlon, dpsi)) % 360


def implied_heading(rec: dict[str, float]) -> float:
    """Heading implied by beta = heading - wave direction (directions are 'from')."""
    return (rec["beta"] + rec["th_wave"]) % 360


def angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


# =============================================================================
# RDF
# =============================================================================


def _iri(local: str):
    return create_twinship_uri(local, VOYAGE_NAMESPACE)


def _dec(value: float, places: int) -> Literal:
    return Literal(Decimal(f"{value:.{places}f}"), datatype=XSD.decimal)


def _ts(dt: datetime) -> Literal:
    return Literal(dt.strftime("%Y-%m-%dT%H:%M:%SZ"), datatype=XSD.dateTime)


def build_voyage_graph(records: list[dict[str, float]]) -> tuple[Graph, list[str]]:
    """Build the voyage graph; returns (graph, warnings)."""
    g = bind_namespaces(Graph())
    warnings: list[str] = []

    crossings, leftover = split_crossings(records)
    if leftover:
        warnings.append(
            "skipped unfinished trailing crossing: records "
            f"{int(leftover[0]['i'])}-{int(leftover[-1]['i'])}"
        )

    for port in PORTS.values():
        iri = _iri(f"Port-{port.code}")
        g.add((iri, RDF.type, TWINSHIP.Port))
        g.add((iri, RDFS.label, Literal(port.name)))

    mismatched: dict[tuple[str, str], list[int]] = {}
    for crossing in crossings:
        _add_crossing(g, crossing)
        expected = rhumb_bearing(crossing.departure, crossing.arrival)
        if angle_diff(expected, implied_heading(crossing.records[0])) > HEADING_TOLERANCE_DEG:
            key = (crossing.departure.code, crossing.arrival.code)
            mismatched.setdefault(key, []).append(crossing.number)

    for (dep, arr), numbers in mismatched.items():
        sample = crossings[numbers[0] - 1]
        warnings.append(
            f"{len(numbers)} of {len(crossings)} crossings {dep}->{arr}: file implies heading "
            f"{implied_heading(sample.records[0]):.0f} deg (beta + th_wave) but the rhumb-line "
            f"bearing is {rhumb_bearing(sample.departure, sample.arrival):.0f} deg"
            " - check direction coding"
        )
    return g, warnings


def _add_crossing(g: Graph, c: Crossing) -> None:
    vid = f"Voyage-{c.number:04d}"
    voyage = _iri(vid)
    recs = c.records

    g.add((_iri(VESSEL_ID), TWINSHIP.hasVoyage, voyage))
    g.add((voyage, RDF.type, TWINSHIP.Voyage))
    g.add(
        (
            voyage,
            RDFS.label,
            Literal(f"Voyage {c.number:04d}: {c.departure.name} to {c.arrival.name}"),
        )
    )
    g.add((voyage, TWINSHIP.twVoyageIdentifier, Literal(f"V{c.number:04d}")))
    g.add((voyage, TWINSHIP.hasDeparturePort, _iri(f"Port-{c.departure.code}")))
    g.add((voyage, TWINSHIP.hasArrivalPort, _iri(f"Port-{c.arrival.code}")))
    g.add((voyage, TWINSHIP.twDeparturePortCode, Literal(c.departure.code)))
    g.add((voyage, TWINSHIP.twArrivalPortCode, Literal(c.arrival.code)))
    g.add((voyage, TWINSHIP.twVoyageEstimatedStartTime, _ts(record_time(recs[0]["i"]))))
    g.add((voyage, TWINSHIP.twVoyageEstimatedEndTime, _ts(record_time(recs[-1]["i"]))))
    g.add((voyage, TWINSHIP.twDistanceInNm, _dec(c.total_nm, 1)))
    mean_speed = sum(r["vs_sog"] for r in recs) / len(recs)
    g.add((voyage, TWINSHIP.twMeanSpeedInKnots, _dec(mean_speed, 3)))

    waypoints = []
    for k, rec in enumerate(recs, start=1):
        wp = _iri(f"{vid}-WP{k:02d}")
        lat, lon = interpolate(c.departure, c.arrival, rec["dist_trav"] / c.total_nm)
        g.add((wp, RDF.type, TWINSHIP.WayPoint))
        g.add((wp, TWINSHIP.twWayPointLatitude, _dec(lat, 6)))
        g.add((wp, TWINSHIP.twWayPointLongitude, _dec(lon, 6)))
        g.add((wp, TWINSHIP.twWayPointTimestamp, _ts(record_time(rec["i"]))))
        waypoints.append(wp)

    for k, rec in enumerate(recs[:-1], start=1):
        leg_id = f"{vid}-Leg{k:02d}"
        leg = _iri(leg_id)
        leg_nm = recs[k]["dist_trav"] - rec["dist_trav"]
        g.add((voyage, TWINSHIP.hasVoyageLeg, leg))
        g.add((leg, RDF.type, TWINSHIP.VoyageLeg))
        g.add((leg, TWINSHIP.observedDuringVoyage, voyage))
        g.add((leg, TWINSHIP.hasStartWayPoint, waypoints[k - 1]))
        g.add((leg, TWINSHIP.hasEndWayPoint, waypoints[k]))
        g.add((leg, TWINSHIP.twDistanceInNm, _dec(leg_nm, 1)))
        g.add((leg, TWINSHIP.twMeanSpeedInKnots, _dec(rec["vs_sog"], 3)))
        _add_weather(g, leg, leg_id, rec)


def _add_weather(g: Graph, leg, leg_id: str, rec: dict[str, float]) -> None:
    """Weather of the leg's start record."""
    weather = _iri(f"{leg_id}-Weather")
    wind = _iri(f"{leg_id}-Wind")
    wave = _iri(f"{leg_id}-Wave")
    g.add((leg, TWINSHIP.hasWeatherCondition, weather))
    g.add((weather, RDF.type, TWINSHIP.WeatherCondition))
    g.add((weather, TWINSHIP.hasWindCondition, wind))
    g.add((weather, TWINSHIP.hasWaveCondition, wave))
    g.add((wind, RDF.type, TWINSHIP.WindCondition))
    g.add((wind, TWINSHIP.twWindSpeedInKnots, _dec(rec["uw"] * MS_TO_KNOTS, 3)))
    g.add((wind, TWINSHIP.twWindDirectionInDegrees, _dec(rec["th_wind"], 3)))
    g.add((wave, RDF.type, TWINSHIP.WaveCondition))
    g.add((wave, TWINSHIP.twSeaHeightInMeters, _dec(rec["hs"], 3)))
    g.add((wave, TWINSHIP.twSeaDirectionInDegrees, _dec(rec["th_wave"], 3)))


# =============================================================================
# Asset
# =============================================================================


class VoyageConfig(Config):
    """Configuration for the futuristic vessel voyage asset."""

    voyage_path: str = "data/RoRo Futuristic Vessel Voyages.dat"
    output_dir: str = "output"


@asset(
    group_name="output",
    partitions_def=vessel_partitions_def,
    deps=[graphdb_upload],
    description=(
        "Add the futuristic vessel's voyages, legs, waypoints, ports and weather to its "
        "GraphDB repository (no-op for other vessels). Runs after graphdb_upload, which "
        "clears the repository: re-running graphdb_upload alone removes the voyages "
        "until this asset runs again."
    ),
    kinds={"GraphDB"},
)
def futuristic_voyage_upload(
    context: AssetExecutionContext,
    config: VoyageConfig,
    graphdb_client: GraphDBClient,
) -> str:
    """Build the futuristic vessel's voyage graph and add it to its repository."""
    vessel = context.partition_key
    if vessel != VOYAGE_NAMESPACE:
        context.log.info(f"No voyage data for {vessel}")
        return ""

    voyage_path = Path(config.voyage_path)
    if not voyage_path.exists():
        context.log.info(f"Voyage file not found at {voyage_path}, skipping voyages")
        return ""

    records = read_records(voyage_path)
    g, warnings = build_voyage_graph(records)
    for w in warnings:
        context.log.warning(w)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ttl_path = output_dir / f"{vessel}-voyages.ttl"
    g.serialize(destination=str(ttl_path), format="turtle")

    graphdb_client.wait_for_readiness()
    graphdb_client.upload_ttl(ttl_path.read_text(encoding="utf-8"), repo_id=vessel)
    voyage_count = len(set(g.subjects(RDF.type, TWINSHIP.Voyage)))
    context.log.info(f"Added {len(g)} voyage triples ({voyage_count} voyages) to '{vessel}'")

    context.add_output_metadata(
        {
            "records": MetadataValue.int(len(records)),
            "voyages": MetadataValue.int(voyage_count),
            "triples": MetadataValue.int(len(g)),
            "ttl_path": MetadataValue.path(str(ttl_path)),
        }
    )
    return str(ttl_path)
