import logging
import qdrant_client
from qdrant_client.models import PointStruct, Distance, VectorParams
import numpy as np
import os
import re
import uuid
import requests

logger = logging.getLogger(__name__)


def get_client():
    return qdrant_client.QdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )

def normalize_collection_name(name: str) -> str:
    """
    Приводит имя коллекции к формату, совместимому с Qdrant:
    - только латиница, цифры, -, _, .
    - без пробелов, кириллицы и спецсимволов
    - не начинается/заканчивается на - или .
    - max 96 символов
    - если получилось пусто — отдаёт 'default_team'
    """
    raw = name
    name = name.encode('ascii', 'ignore').decode('ascii')
    name = name.replace(' ', '_')
    name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    name = re.sub(r'[-\.]{2,}', '_', name)
    name = name.strip('_-.')
    name = name[:96]
    if not name:
        name = "default_team"
    logger.debug("[QDRANT] normalize_collection_name: raw='%s' -> normalized='%s'", raw, name)
    return name

def to_qdrant_id(uid):
    """
    Преобразует любой uid (строка/число/hex) в UUID для Qdrant.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, str(uid)))

def ensure_collection(client, collection, vector_size):
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        logger.info("[QDRANT] Creating collection: '%s' (vector_size=%s)", collection, vector_size)
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    else:
        logger.debug("[QDRANT] Collection exists: '%s'", collection)

def save_report_chunks(team: str, uuid: str, chunks, embeddings, timestamp):
    logger.debug("QDRANT_HOST = %s", os.getenv("QDRANT_HOST"))
    logger.debug("QDRANT_PORT = %s", os.getenv("QDRANT_PORT"))
    logger.debug("[QDRANT] client.get_collections() call")
    client = get_client()
    collection = normalize_collection_name(team)
    vector_size = embeddings.shape[1] if hasattr(embeddings, 'shape') else len(embeddings[0])
    ensure_collection(client, collection, vector_size)
    points = [
        PointStruct(
            id=to_qdrant_id(f"{uuid}-{chunk['uid']}"),  # уникальный ID для каждой попытки теста
            vector=embeddings[idx].tolist(),
            payload={**chunk, "report_uuid": uuid, "timestamp": chunk.get("timestamp", 0)}
        ) for idx, chunk in enumerate(chunks)
    ]
    logger.info("[QDRANT] Upserting %s points into '%s'", len(points), collection)
    client.upsert(collection_name=collection, points=points)

def get_prev_report_chunks(team: str, exclude_uuid: str, limit=2):
    client = get_client()
    collection = normalize_collection_name(team)
    try:
        res = client.scroll(collection_name=collection, limit=1000)
    except Exception as e:
        # Если коллекция есть, но points нет — ловим 404 и возвращаем пусто!
        logger.error("[QDRANT] scroll exception: %s", e)
        return {}
    reports = {}
    for point in res[0]:
        uuid = point.payload.get("report_uuid")
        if uuid and uuid != exclude_uuid:
            ts = point.payload.get("timestamp", 0)
            if uuid not in reports:
                reports[uuid] = {"timestamp": ts, "chunks": []}
            else:
                if ts < reports[uuid]["timestamp"]:
                    reports[uuid]["timestamp"] = ts
            reports[uuid]["chunks"].append(point.payload)
    sorted_reports = sorted(
        reports.items(), key=lambda x: x[1]["timestamp"], reverse=True
    )[:limit]
    return {uid: data["chunks"] for uid, data in sorted_reports}


def maintain_last_n_reports(team, n, current_uuid):
    logger.debug("[QDRANT] client.get_collections() call")
    client = get_client()
    collection = normalize_collection_name(team)
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        logger.debug("[QDRANT] Collection '%s' does not exist (skip cleanup)", collection)
        return
    res = client.scroll(collection_name=collection, limit=1000)
    uuids = {}
    for point in res[0]:
        uuid_ = point.payload.get("report_uuid")
        ts = point.payload.get("timestamp", 0)
        if uuid_ not in uuids:
            uuids[uuid_] = []
        uuids[uuid_].append(point.id)
    uuids_list = sorted(uuids.keys(), reverse=True)

    # Keep the most recent n reports including the current one
    keep = set()
    if current_uuid:
        keep.add(current_uuid)
    for u in uuids_list:
        if len(keep) >= n:
            break
        keep.add(u)
    to_delete = [u for u in uuids_list if u not in keep]
    if to_delete:
        logger.info("[QDRANT] Deleting reports: %s", to_delete)
        for u in to_delete:
            client.delete(collection_name=collection, points_selector={"points": uuids[u]})
    else:
        logger.debug(
            "[QDRANT] No reports to delete in '%s' (current count: %s)",
            collection,
            len(uuids_list),
        )
