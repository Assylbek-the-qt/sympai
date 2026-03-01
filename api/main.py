from fastapi import FastAPI

from routers import items, patients

app = FastAPI()

app.include_router(items.router)
app.include_router(patients.router)


@app.get("/health")
def health():
    return {"status": "ok"}
