import os
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from qdrant_store import (
    save_report_chunks,
    get_prev_report_chunks,
    maintain_last_n_reports,
)
from report_fetcher import fetch_allure_report
from chunker import chunk_report
from embedder import generate_embeddings
from plotter import plot_trends
import utils
from dotenv import load_dotenv

load_dotenv()

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
        # 2. Получаем чанки и имя команды (chunk_report возвращает tuple)
        chunks, team_name = chunk_report(report)
        if not team_name:
            team_name = "default_team"

        # 3. Генерируем эмбеддинги
        embeddings = generate_embeddings(chunks)
        # 4. Сохраняем чанки и эмбеддинги в Qdrant
        save_report_chunks(team_name, uuid, chunks, embeddings)
        # 5. Чистим старые отчёты в коллекции
        maintain_last_n_reports(team_name, n=3, current_uuid=uuid)
        # 6. Получаем чанки из предыдущих двух отчётов
        prev_chunks = get_prev_report_chunks(team_name, exclude_uuid=uuid, limit=2)

        # 7. Подготавливаем flat-список всех кейсов для аналитики и графика
        all_cases = []
        if isinstance(report, list):
            all_cases.extend(report)
        else:
            all_cases.append(report)
        for prev in prev_chunks:
            if isinstance(prev, list):
                all_cases.extend(prev)
            else:
                all_cases.append(prev)

        # 8. Генерируем график тренда и трендовые данные
        img_path, trend = plot_trends(all_cases, team_name)
        # Формируем текст тренда для LLM
        if trend:
            trend_text = "\n".join([
                f"{day}: passed={data['passed']}, failed={data['failed']}, skipped={data['skipped']}"
                for day, data in sorted(trend.items())
            ])
        else:
            trend_text = "Нет данных по динамике запусков."

        # 9. Генерируем анализ с помощью LLM (через Ollama, передаём trend_text)
        summary, rules = utils.analyze_cases_with_llm(all_cases, team_name, trend_text)

        # 10. Отправляем результат обратно (или сохраняем для тестов)
        analysis = [{"rule": rule, "message": msg} for rule, msg in rules]
        utils.send_analysis_to_allure(uuid, analysis)
        return {"result": "ok", "summary": summary, "analysis": analysis}
    except Exception as e:
        print("=== TRACEBACK START ===")
        traceback.print_exc()
        print("=== TRACEBACK END ===")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "ok"}
