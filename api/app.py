"""FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from api.routes import router

app = FastAPI(title="AB PMJAY Auto Adjudication API", version="1.0.0")
app.include_router(router)
