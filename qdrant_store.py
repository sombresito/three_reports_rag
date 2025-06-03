import qdrant_client
from qdrant_client.models import PointStruct, Distance, VectorParams, Filter, FieldCondition, MatchValue
import numpy as np
import os

def get_client():
    return qdrant_client.QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), port=int(os.getenv("QDRANT_PORT", 6333)))

def save_report_chunks(team: str, uuid: str, chunks, embeddings):
    client = get_client()
    collection = team
    # Создаём коллекцию, если нет
    if collection not in [col.name for col in client.get_collections().collections]:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=embeddings.shape[1], distance=Distance.COSINE),
        )
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
    collection = team
    res = client.scroll(collection_name=collection, limit=1000)
    reports = {}
    for point in res[0]:
        uuid = point.payload.get("report_uuid")
        if uuid and uuid != exclude_uuid:
            if uuid not in reports:
                reports[uuid] = []
            reports[uuid].append(point.payload)
    # Сортируем по времени (если есть)
    prev_uuids = list(reports.keys())[:limit]
    return [reports[u] for u in prev_uuids]

def maintain_last_n_reports(team, n, current_uuid):
    client = get_client()
    collection = team
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
