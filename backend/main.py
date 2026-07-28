

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from core.config import settings
from core.logging import setup_logging
from core.startup import startup_event, shutdown_event


# --------------------------------------------------------
# Initialize Logging
# --------------------------------------------------------

setup_logging()


# --------------------------------------------------------
# Application Lifespan
# --------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executes application startup and shutdown events.
    """

    await startup_event()

    yield

    await shutdown_event()


# --------------------------------------------------------
# Create FastAPI Application
# --------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# --------------------------------------------------------
# Configure CORS
# --------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------
# Register API Routes
# --------------------------------------------------------

app.include_router(api_router)


# --------------------------------------------------------
# Root Endpoint
# --------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    """

    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "message": "Welcome to OptiWare AI Backend API"
    }


# --------------------------------------------------------
# Health Check
# --------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health():
    """
    Basic health endpoint.
    """

    return {
        "status": "healthy"
    }