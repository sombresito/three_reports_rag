import os
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

from qdrant_store import (
    save_report_chunks,
    get_prev_report_chunks,
    maintain_last_n_reports,
)
from report_fetcher import fetch_allure_report
from chunker import chunk_report
from embedder import generate_embeddings
from plotter import plot_trends_for_report, extract_trend_data
import utils

load_dotenv()
app = FastAPI()

class AnalyzeRequest(BaseModel):
    uuid: str

@app.post("/uuid/analyze")
async def analyze_uuid(req: AnalyzeRequest):
    uuid = req.uuid
    try:
        # 1. Получить Allure-отчёт
        report = fetch_allure_report(uuid)
        if not isinstance(report, list):
            raise HTTPException(status_code=400, detail="Report JSON must be a list of test-cases")

        # 2. Получаем чанки и имя команды
        chunks, team_name = chunk_report(report)
        if not team_name:
            team_name = "default_team"

        # 3. Эмбеддинги
        embeddings = generate_embeddings(chunks)

        # 4. Qdrant: сохранить текущий отчёт, почистить старые
        save_report_chunks(team_name, uuid, chunks, embeddings)
        maintain_last_n_reports(team_name, n=3, current_uuid=uuid)
        prev_chunks = get_prev_report_chunks(team_name, exclude_uuid=uuid, limit=2)

        # 5. Преобразуем prev_chunks в dict (uuid -> chunks)
        if isinstance(prev_chunks, dict):
            prev_chunks_dict = prev_chunks
        elif isinstance(prev_chunks, list):
            prev_chunks_dict = {f"prev_{i}": chs for i, chs in enumerate(prev_chunks)}
        else:
            prev_chunks_dict = {}

        # 6. Построить индивидуальный и summary-график тренда (авторотация файлов — внутри plotter.py)
        summary_plot_path = plot_trends_for_report(
            uuid, chunks, prev_chunks_dict
        )

        # 7. Собираем данные для анализа (LLM)
        all_cases = []
        all_cases.extend(chunks)
        for prev in prev_chunks_dict.values():
            all_cases.extend(prev)

        trend_text_parts = []
        for u, chs in [(uuid, chunks)] + list(prev_chunks_dict.items()):
            dates, passed, failed, skipped = extract_trend_data(chs)
            for dt, p, f, s in zip(dates, passed, failed, skipped):
                trend_text_parts.append(
                    f"Отчёт {u[:8]} {dt}: passed={p}, failed={f}, skipped={s}"
                )
        trend_text = "\n".join(trend_text_parts) if trend_text_parts else "Нет данных по динамике запусков."

        # 8. LLM-анализ
        summary, rules = utils.analyze_cases_with_llm(all_cases, team_name, trend_text)

        # 9. Отправить результат обратно в Allure (или сохранить для тестов)
        analysis = [{"rule": rule, "message": msg} for rule, msg in rules]
        utils.send_analysis_to_allure(uuid, analysis)

        return {
            "result": "ok",
            "summary": summary,
            "analysis": analysis,
            "trend_plot": summary_plot_path,
        }
    except Exception as e:
        print("=== TRACEBACK START ===")
        traceback.print_exc()
        print("=== TRACEBACK END ===")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "ok"}
