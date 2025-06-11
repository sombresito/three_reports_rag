import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_store import (
    save_report_chunks,
    get_prev_report_chunks,
    maintain_last_n_reports,
)
from report_fetcher import fetch_allure_report
from chunker import chunk_report
from embedder import generate_embeddings
from plotter import plot_trends_for_reports
import utils
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# How many reports should be kept and compared (current + previous ones)
REPORTS_HISTORY_DEPTH = int(os.getenv("REPORTS_HISTORY_DEPTH", 3))

app = FastAPI()

class AnalyzeRequest(BaseModel):
    uuid: str

@app.post("/uuid/analyze")
async def analyze_uuid(req: AnalyzeRequest):
    uuid = req.uuid
    try:
        # 1. Получить Allure-отчёт (JSON)
        report = fetch_allure_report(uuid)
        if not isinstance(report, list):
            raise HTTPException(status_code=400, detail="Report JSON must be a list of test-cases")
        # 2. Получаем чанки и имя команды
        chunks, team_name = chunk_report(report)
        starts = [c.get("time", {}).get("start") for c in report if isinstance(c.get("time", {}).get("start"), (int, float))]
        timestamp = int(min(starts)) if starts else 0
        if not team_name:
            team_name = "default_team"

        # 3. Генерируем эмбеддинги
        embeddings = generate_embeddings(chunks)
        # 4. Сохраняем чанки и эмбеддинги в Qdrant
        save_report_chunks(team_name, uuid, chunks, embeddings, timestamp)
        # 5. Чистим старые отчёты в коллекции
        maintain_last_n_reports(team_name, n=REPORTS_HISTORY_DEPTH, current_uuid=uuid)
        # 6. Получаем чанки из предыдущих отчётов (от старого к новому!)
        prev_limit = max(REPORTS_HISTORY_DEPTH - 1, 0)
        prev_chunks = get_prev_report_chunks(team_name, exclude_uuid=uuid, limit=prev_limit)

        # 7. Собираем для plotter: 2 prev + текущий
        all_reports = []
        all_uuids = []
        all_teams = []
        # prev_chunks — это dict {uuid: [cases]}
        for report_uuid, chunks in prev_chunks.items():
            if chunks:
                all_reports.append(chunks)
                all_uuids.append(report_uuid)
                # Название команды из labels первого кейса
                team = None
                if isinstance(chunks[0], dict) and chunks[0].get("labels"):
                    for lbl in chunks[0]["labels"]:
                        if lbl.get("name") == "suite":
                            team = lbl.get("value")
                            break
                all_teams.append(team or "")
        # Добавляем текущий отчёт
        all_reports.append(report)
        all_uuids.append(uuid)
        all_teams.append(team_name)

        # Оставляем только последние REPORTS_HISTORY_DEPTH (если вдруг больше)
        if len(all_reports) > REPORTS_HISTORY_DEPTH:
            all_reports = all_reports[-REPORTS_HISTORY_DEPTH:]
            all_uuids = all_uuids[-REPORTS_HISTORY_DEPTH:]
            all_teams = all_teams[-REPORTS_HISTORY_DEPTH:]

        # 8. Генерируем все тренды (и индивидуальные bar, и summary line)
        img_path = plot_trends_for_reports(all_reports, all_uuids, all_teams)

        # 9. Формируем текстовую аналитику
        # Тренд в виде строки для LLM (пример: passed=12, failed=2,... на каждый отчёт)
        trend_text = "\n".join(
            [f"{i+1}-й: passed={sum(1 for x in rep if (x.get('status') or '').lower() == 'passed')}, "
             f"failed={sum(1 for x in rep if (x.get('status') or '').lower() == 'failed')}, "
             f"broken={sum(1 for x in rep if (x.get('status') or '').lower() == 'broken')}, "
             f"skipped={sum(1 for x in rep if (x.get('status') or '').lower() == 'skipped')}"
             for i, rep in enumerate(all_reports)]
        )

        summary, rules = utils.analyze_cases_with_llm(all_reports, team_name, trend_text, img_path)
        analysis = [{"rule": rule, "message": msg} for rule, msg in rules]
        utils.send_analysis_to_allure(uuid, analysis)

        return {"result": "ok", "summary": summary, "analysis": analysis}
    except Exception as e:
        logger.exception("Unhandled exception while processing UUID %s", uuid)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "ok"}
