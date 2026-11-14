"""What the ingestion worker fetches, and why.

Honesty rules for this file:
* Nothing here states a NASA finding. Titles, dates, authors and licences are read from the NTRS record at
  ingestion time and stored with the document, never typed in by hand.
* NTRS IDs below were returned by NASA web searches for these investigations. Each is re-checked at ingestion:
  the worker reads the record, and a document is kept only if its own text mentions the investigation or fire
  safety terms (see `relevance_ok` in ingest.py).
* Search queries let the worker discover further NTRS records; every hit goes through the same checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExperimentSpec:
    key: str
    name: str
    program: str
    description: str
    source_url: str | None
    variables: tuple[str, ...]
    ntrs_ids: tuple[str, ...] = ()
    queries: tuple[str, ...] = ()
    keywords: tuple[str, ...] = field(default_factory=tuple)


EXPERIMENTS: tuple[ExperimentSpec, ...] = (
    ExperimentSpec(
        key="BASS-II",
        name="Burning and Suppression of Solids II",
        program="NASA ISS microgravity combustion",
        description="ISS investigation of flame spread, extinction and suppression on solid fuels in microgravity.",
        source_url="https://www.nasa.gov/mission_pages/station/research/news/bassII",
        variables=("oxygen", "airflow", "pressure", "geometry"),
        ntrs_ids=("20160000593", "20150002323"),
        queries=("Burning and Suppression of Solids BASS-II microgravity flame",),
        keywords=("bass", "burning and suppression", "solid fuel", "flame spread", "microgravity"),
    ),
    ExperimentSpec(
        key="SoFIE",
        name="Solid Fuel Ignition and Extinction",
        program="NASA ISS microgravity combustion",
        description="ISS combustion investigation of ignition and extinction of solid fuels in the Combustion Integrated Rack.",
        source_url=None,
        variables=("oxygen", "airflow", "pressure", "temperature"),
        ntrs_ids=("20210011385",),
        queries=("Solid Fuel Ignition and Extinction SoFIE microgravity",),
        keywords=("sofie", "solid fuel ignition", "extinction", "flammability"),
    ),
    ExperimentSpec(
        key="ACME",
        name="Advanced Combustion via Microgravity Experiments",
        program="NASA ISS microgravity combustion",
        description="ISS combustion investigations of gas-jet flames and related phenomena in microgravity.",
        source_url=None,
        variables=("oxygen", "pressure"),
        queries=("Advanced Combustion via Microgravity Experiments ACME",),
        keywords=("acme", "advanced combustion", "microgravity"),
    ),
    ExperimentSpec(
        key="Saffire",
        name="Spacecraft Fire Experiment (Saffire)",
        program="NASA spacecraft fire safety",
        description="Large-scale spacecraft fire experiments flown on uncrewed resupply vehicles.",
        source_url=None,
        variables=("oxygen", "airflow", "geometry", "heating"),
        queries=(
            "Spacecraft Fire Experiment Saffire Cygnus",
            "Saffire spacecraft fire safety large scale flame",
        ),
        keywords=("saffire", "spacecraft fire", "cygnus"),
    ),
    ExperimentSpec(
        key="SFS",
        name="Spacecraft fire safety (general)",
        program="NASA spacecraft fire safety",
        description="NASA material flammability, fire detection and suppression literature for crewed spacecraft.",
        source_url=None,
        variables=("oxygen", "pressure", "airflow"),
        queries=(
            "spacecraft fire safety material flammability microgravity",
            "reduced gravity flame spread exploration atmosphere oxygen concentration",
        ),
        keywords=("fire safety", "flammability", "fire detection", "flame spread", "oxygen"),
    ),
)

# Public NASA pages (HTML). Fetched as text, same provenance and quarantine rules as NTRS documents.
WEB_PAGES: tuple[tuple[str, str, str], ...] = (
    ("WEB-BASS2-STATION", "BASS-II", "https://www.nasa.gov/mission_pages/station/research/news/bassII"),
    ("WEB-PSI-SPOTLIGHT", "BASS-II", "https://science.data.nasa.gov/learn/blog/psi-spotlight"),
)

DEMO_EXPERIMENT = ExperimentSpec(
    key="DEMO",
    name="Synthetic demonstration evidence",
    program="SYNTHETIC/DEMO",
    description="Offline demonstration passages written for this prototype. Not NASA data.",
    source_url=None,
    variables=(),
)


def experiment_by_key(key: str) -> ExperimentSpec | None:
    return next((e for e in (*EXPERIMENTS, DEMO_EXPERIMENT) if e.key == key), None)
