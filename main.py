import utils
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from report_fetcher import fetch_allure_report
from chunker import chunk_report
from embedder import generate_embeddings
from qdrant_store import save_report_chunks, get_prev_report_chunks, maintain_last_n_reports
from analyzer import analyze_reports
from plotter import plot_trends
from utils import save_analysis_result


app = FastAPI()

class AnalyzeRequest(BaseModel):
    uuid: str

@app.post("/uuid/analyze")
async def analyze_uuid(req: AnalyzeRequest):
    uuid = req.uuid
    try:
        # 1. Получаем отчет Allure по UUID
        report = fetch_allure_report(uuid)
        # 2. Разбиваем на чанки
        chunks, team_name = chunk_report(report)
        # 3. Генерируем эмбеддинги
        embeddings = generate_embeddings(chunks)
        # 4. Сохраняем чанки в Qdrant (оставляем только 3 отчёта)
        maintain_last_n_reports(team_name, n=3, current_uuid=uuid)
        save_report_chunks(team_name, uuid, chunks, embeddings)
        # 5. Получаем 2 предыдущих отчета
        prev_chunks = get_prev_report_chunks(team_name, exclude_uuid=uuid, limit=2)
        # 6. Генерируем Summary-график
        img_path = plot_trends([report] + prev_chunks, team_name)
        # 7. Анализ через Ollama + LangChain
        analysis = analyze_reports(report, prev_chunks, img_path)
        # 8. Сохраняем анализ в файл (для истории)
        save_analysis_result(uuid, analysis)
        # 9. Отправляем результат (POST) в Allure
        utils.send_analysis_to_allure(uuid, analysis)
        return {"result": "ok", "analysis": analysis}
    except Exception as e:
        print("=== TRACEBACK START ===")
        traceback.print_exc()
        print("=== TRACEBACK END ===")
        raise HTTPException(status_code=500, detail=str(e))
