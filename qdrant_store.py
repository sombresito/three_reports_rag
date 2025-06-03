import qdrant_client
from qdrant_client.models import PointStruct, Distance, VectorParams
import numpy as np
import os
import re

def get_client():
    return qdrant_client.QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )

def normalize_collection_name(name: str) -> str:
    """
    Делает имя коллекции совместимым с Qdrant:
    - только латиница, цифры, -, _, .
    - никаких пробелов и кириллицы
    - не начинается/заканчивается на - или .
    - max 96 символов
    """
    name = name.encode('ascii', 'ignore').decode('ascii')  # Удалить не-ASCII
    name = name.replace(' ', '_')
    name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)         # Остальное в "_"
    name = re.sub(r'[-\.]{2,}', '_', name)                 # Нет двойных - или .
    name = name.strip('_-.')
    return name[:96]

def ensure_collection(client, collection, vector_size):
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

def save_report_chunks(team: str, uuid: str, chunks, embeddings):
    client = get_client()
    collection = normalize_collection_name(team)
    vector_size = embeddings.shape[1] if hasattr(embeddings, 'shape') else len(embeddings[0])
    ensure_collection(client, collection, vector_size)
    points = [
        PointStruct(
            id=int(hash(chunk["uid"])),
            vector=embeddings[idx].tolist(),
            payload={**chunk, "report_uuid": uuid}
        ) for idx, chunk in enumerate(chunks)
    ]
    client.upsert(collection_name=collection, points=points)

def get_prev_report_chunks(team: str, exclude_uuid: str, limit=2):
    client = get_client()
    collection = normalize_collection_name(team)
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        return []
    res = client.scroll(collection_name=collection, limit=1000)
    reports = {}
    for point in res[0]:
        uuid = point.payload.get("report_uuid")
        if uuid and uuid != exclude_uuid:
            if uuid not in reports:
                reports[uuid] = []
            reports[uuid].append(point.payload)
    prev_uuids = list(reports.keys())[:limit]
    return [reports[u] for u in prev_uuids]

def maintain_last_n_reports(team, n, current_uuid):
    client = get_client()
    collection = normalize_collection_name(team)
    existing_collections = [col.name for col in client.get_collections().collections]
    if collection not in existing_collections:
        return
    res = client.scroll(collection_name=collection, limit=1000)
    uuids = {}
    for point in res[0]:
        uuid = point.payload.get("report_uuid")
        if uuid not in uuids:
            uuids[uuid] = []
        uuids[uuid].append(point.id)
    uuids_list = sorted(uuids.keys(), reverse=True)
    if len(uuids_list) > n:
        for u in uuids_list[n:]:
            client.delete(collection_name=collection, points_selector={"points": uuids[u]})
