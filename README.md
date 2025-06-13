# three_reports_rag

A FastAPI service that analyses multiple Allure reports using retrieval augmented generation (RAG).

## Setup

Install dependencies and download the embedding model used by the service.

```bash
pip install -r requirements.txt
```

### Download the embedding model

The application expects a local copy of the model. Use `download_embedding_model.py` to fetch it. The destination can be provided as a command line argument or via the `EMBEDDING_MODEL_PATH` environment variable.

```bash
python download_embedding_model.py --output-path path/to/local_models/intfloat/multilingual-e5-small
```

or

```bash
export EMBEDDING_MODEL_PATH=path/to/local_models/intfloat/multilingual-e5-small
python download_embedding_model.py
```

Make sure the same path is supplied to the service through the `EMBEDDING_MODEL_PATH` environment variable.

## Running

After downloading the model, start the API server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

You can also run everything via Docker Compose:

```bash
docker-compose up --build
```

The Compose stack now includes the Ollama container used for LLM requests. Simply
run `docker-compose up` and all services, including Ollama, will start automatically.

## Environment variables

Set `ALLURE_ALLOW_ATTACHMENTS=true` to enable uploading attachments when sending
analysis results to the Allure API. If not set, only the JSON payload is sent.
