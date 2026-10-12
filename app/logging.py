import json
import logging

logger = logging.getLogger("bari_demo")


def event(name: str, **fields) -> None:
    logger.info(
        json.dumps({"event": name, "synthetic": True, **fields}, sort_keys=True, default=str)
    )
