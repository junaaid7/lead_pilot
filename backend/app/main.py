from fastapi import FastAPI

app = FastAPI(title="CodeCelix Lead Finder API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/hello")
def hello():
    return {"message": "CodeCelix Lead Finder backend chal raha hai"}