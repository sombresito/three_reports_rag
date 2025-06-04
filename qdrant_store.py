import qdrant_client
from qdrant_client.models import PointStruct, Distance, VectorParams
import numpy as np
import os
import re
import uuid

def get_client():
    return qdrant_client.QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
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
    print(f"[QDRANT] normalize_collection_name: raw='{raw}' -> normalized='{name}'")
    return name

def to_qdrant_id(uid):
    """
    Преобразует любой uid (строка/число/hex) в UUID для Qdrant.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, str(uid)))

def ensure_collection(client, collection, vector_size):
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        print(f"[QDRANT] Creating collection: '{collection}' (vector_size={vector_size})")
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    else:
        print(f"[QDRANT] Collection exists: '{collection}'")

def save_report_chunks(team: str, uuid: str, chunks, embeddings):
    print("QDRANT_HOST =", os.getenv("QDRANT_HOST"))
    print("QDRANT_PORT =", os.getenv("QDRANT_PORT"))
    client = get_client()    
    collection = normalize_collection_name(team)
    vector_size = embeddings.shape[1] if hasattr(embeddings, 'shape') else len(embeddings[0])
    ensure_collection(client, collection, vector_size)
    points = [
        PointStruct(
            id=to_qdrant_id(chunk["uid"]),  # <-- универсальный, совместимый с Qdrant ID
            vector=embeddings[idx].tolist(),
            payload={**chunk, "report_uuid": uuid}
        ) for idx, chunk in enumerate(chunks)
    ]
    print(f"[QDRANT] Upserting {len(points)} points into '{collection}'")
    client.upsert(collection_name=collection, points=points)

def get_prev_report_chunks(team: str, exclude_uuid: str, limit=2):
    client = get_client()
    collection = normalize_collection_name(team)
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        print(f"[QDRANT] Collection '{collection}' does not exist, returning []")
        return []
    res = client.scroll(collection_name=collection, limit=1000)
    reports = {}
    for point in res[0]:
        uuid_ = point.payload.get("report_uuid")
        if uuid_ and uuid_ != exclude_uuid:
            if uuid_ not in reports:
                reports[uuid_] = []
            reports[uuid_].append(point.payload)
    prev_uuids = list(reports.keys())[:limit]
    print(f"[QDRANT] get_prev_report_chunks: Found {len(prev_uuids)} uuids in '{collection}'")
    return [reports[u] for u in prev_uuids]

def maintain_last_n_reports(team, n, current_uuid):
    client = get_client()
    collection = normalize_collection_name(team)
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        print(f"[QDRANT] Collection '{collection}' does not exist (skip cleanup)")
        return
    res = client.scroll(collection_name=collection, limit=1000)
    uuids = {}
    for point in res[0]:
        uuid_ = point.payload.get("report_uuid")
        if uuid_ not in uuids:
            uuids[uuid_] = []
        uuids[uuid_].append(point.id)
    uuids_list = sorted(uuids.keys(), reverse=True)
    if len(uuids_list) > n:
        print(f"[QDRANT] Deleting reports: {uuids_list[n:]}")
        for u in uuids_list[n:]:
            client.delete(collection_name=collection, points_selector={"points": uuids[u]})
    else:
        print(f"[QDRANT] No reports to delete in '{collection}' (current count: {len(uuids_list)})")
