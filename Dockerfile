FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Копируем только код и необходимые папки
COPY . .

# Создаём каталоги (на случай если volume не примонтирован)
RUN mkdir -p /app/plots /app/local_models

# Стартуем Uvicorn сервер
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
