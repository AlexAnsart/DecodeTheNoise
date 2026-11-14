"""Gives each zone of a build a short name, one LLM call per zone through the AI Router.

Run: uv run python -m pipelines.zones.name --name ira-3k   (then pack again)
"""

import argparse
import json
import logging
from pathlib import Path

import httpx
import numpy as np
from pydantic import TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.map.schema import ZoneInfo
from backend.model_client.llm import ChatClient
from pipelines import runlog
from pipelines.corpus import read_corpus
from pipelines.paths import CORPUS_FILE, DATA, ZONE_OF_POINT_FILE, ZONES_FILE, work_dir
from pipelines.vectors import read_vectors
from pipelines.zones.naming import (
    PROMPT_VERSION,
    SAMPLES_PER_ZONE,
    CachedName,
    name_zone,
    representative,
    tell_apart,
)

log = logging.getLogger("zones.name")

CACHE_FILE = DATA / "llm" / "zone-names.json"
ZONE_NAMES_FILE = "zone-names.json"
_CACHE = TypeAdapter(dict[str, CachedName])


class RouterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hostinger_router_api_base: str = "https://router.hostinger.com/v1"
    hostinger_router_api_key: str
    llm_model: str = "gemini-3.8-flash"


def read_cache(path: Path) -> dict[str, CachedName]:
    return _CACHE.validate_json(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_cache(path: Path, cache: dict[str, CachedName]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_CACHE.dump_json(cache, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = RouterSettings()
    work = work_dir(args.name)
    zones = [ZoneInfo.model_validate(z) for z in json.loads((work / ZONES_FILE).read_text("utf-8"))]
    zone_of_point = np.load(work / ZONE_OF_POINT_FILE)
    vectors, _ = read_vectors(work)
    texts = [item.text for item in read_corpus(work / CORPUS_FILE)]
    client = ChatClient(
        settings.hostinger_router_api_base, settings.hostinger_router_api_key, settings.llm_model
    )
    cache = read_cache(CACHE_FILE)

    named: list[ZoneInfo] = []
    with runlog.timed() as elapsed:
        for zone in zones:
            members = np.flatnonzero(zone_of_point == zone.id)
            samples = [texts[i] for i in representative(vectors, members, SAMPLES_PER_ZONE)]
            try:
                name = name_zone(client, settings.llm_model, cache, zone.words, samples)
            except httpx.HTTPError as error:
                # The zone keeps its words; the next run asks again.
                log.warning("zone %d was not named: %s", zone.id, error)
                name = None
            named.append(zone.model_copy(update={"name": name, "named": True}) if name else zone)
            log.info("zone %d: %s", zone.id, named[-1].name)
    client.close()
    write_cache(CACHE_FILE, cache)
    labels = tell_apart([zone.name for zone in named], [zone.words for zone in named])
    named = [
        zone.model_copy(update={"name": label}) if zone.named else zone
        for zone, label in zip(named, labels, strict=True)
    ]

    payload = [zone.model_dump() for zone in named]
    (work / ZONES_FILE).write_text(json.dumps(payload, ensure_ascii=False, indent=1), "utf-8")
    record = {
        "model": settings.llm_model,
        "prompt_version": PROMPT_VERSION,
        "temperature": 0,
        "named": sum(zone.named for zone in named),
        "zones": len(named),
    }
    (work / ZONE_NAMES_FILE).write_text(json.dumps(record, indent=1), encoding="utf-8")
    note = f"{settings.llm_model} through the AI Router, {record['named']} zones named"
    runlog.record("zone-names", args.name, len(named), elapsed[0], note=note)
    log.info("%d of %d zones named with %s", record["named"], len(named), settings.llm_model)


if __name__ == "__main__":
    main()
