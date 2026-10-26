from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.liveness_routes import router as liveness_router


app = FastAPI(
    title="AI Attendance System",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5173",
        "http://localhost:5173"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# ROUTES
# =========================================================

app.include_router(router)

app.include_router(liveness_router)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "message": "AI Attendance Service is running"
    }