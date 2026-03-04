from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, daily_readings, doctors, patients

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(daily_readings.router)


@app.get("/health")
def health():
    return {"status": "ok"}
