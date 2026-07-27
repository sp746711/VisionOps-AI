# 🏭 VisionOps-AI — AI-Powered Warehouse Operations Intelligence Platform

<p align="center">
  <img src="https://via.placeholder.com/800x200/1a1a2e/e94560?text=VisionOps-AI" alt="VisionOps-AI Logo" width="800">
  <br>
  <em>Real-Time Computer Vision Intelligence for Warehouse Operations</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=opencv&logoColor=black" alt="YOLOv8">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <br>
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Power%20BI-F2C811?style=for-the-badge&logo=power-bi&logoColor=black" alt="Power BI">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/DVC-945DD6?style=for-the-badge&logo=dvc&logoColor=white" alt="DVC">
  <br>
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License: MIT">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge" alt="PRs Welcome">
  <img src="https://img.shields.io/badge/Open%20Source-❤️-red?style=for-the-badge" alt="Open Source">
</p>

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Problem Statement](#-problem-statement)
- [Solution](#-solution)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Overall Workflow](#-overall-workflow)
- [Technology Stack](#-technology-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Frontend Architecture](#-frontend-architecture)
- [Backend Architecture](#-backend-architecture)
- [AI Processing Pipeline](#-ai-processing-pipeline)
- [Business Rules](#-business-rules)
- [Analytics & Power BI](#-analytics--power-bi)
- [API Overview](#-api-overview)
- [Data Storage](#-data-storage)
- [Installation Guide](#-installation-guide)
- [Environment Variables](#-environment-variables)
- [Running the Project](#-running-the-project)
- [Screenshots](#-screenshots)
- [Logging](#-logging)
- [Error Handling](#-error-handling)
- [Security](#-security)
- [Performance](#-performance)
- [Testing](#-testing)
- [Future Roadmap](#-future-roadmap)
- [Version History](#-version-history)
- [Contributing Guidelines](#-contributing-guidelines)
- [License](#-license)
- [Acknowledgements](#-acknowledgements)
- [Contact Information](#-contact-information)
- [Project Credits](#-project-credits)

---

## 🚀 Project Overview

**VisionOps-AI** is a production-grade, end-to-end computer vision platform purpose-built for **warehouse operations intelligence**. It leverages state-of-the-art **YOLOv8 object detection**, **ByteTrack multi-object tracking**, and a **business rule engine** to automatically monitor, analyze, and optimize warehouse floor activities in real time.

The platform transforms standard CCTV/IP camera feeds into actionable operational intelligence — detecting workers, forklifts, trucks, pallets, and inventory while tracking key performance indicators (KPIs) such as loading times, waiting times, worker productivity, and dock utilization. Results are surfaced through an interactive **React + TypeScript dashboard** and **Power BI embedded analytics**, enabling data-driven warehouse management at scale.

> **Built for production. Designed for scale. Driven by AI.**

---

## 🔍 Problem Statement

Modern warehouses face critical operational challenges:

| Challenge | Impact |
|-----------|--------|
| **Manual Monitoring** | Supervisors rely on visual inspection of CCTV feeds, which is error-prone, labor-intensive, and does not scale |
| **Delayed Reporting** | Operational data is typically available hours or days after events occur, preventing real-time intervention |
| **Lack of Quantified KPIs** | Metrics like dock wait times, forklift utilization, and worker productivity are estimated rather than measured |
| **Congestion Blindness** | Dock congestion and bottleneck formation goes undetected until it causes significant delays |
| **Alert Fatigue** | Generic alerting systems generate excessive false positives, desensitizing operations teams |
| **Data Silos** | Operational video data exists in isolation from business intelligence tools like Power BI |

The logistics and warehousing industry loses billions annually due to these inefficiencies. Traditional approaches to warehouse monitoring simply cannot deliver the real-time, granular, and actionable intelligence that modern operations require.

---

## 💡 Solution

**VisionOps-AI** is a comprehensive, AI-first platform that directly addresses these challenges:

- **🎯 Real-Time AI Detection** — YOLOv8 models detect 10+ object classes including workers, forklifts, pallet jacks, trucks, pallets, inventory racks, dock doors, safety cones, and more
- **🔄 Continuous Multi-Object Tracking** — ByteTrack maintains consistent object identities across video frames for accurate trajectory and dwell time analysis
- **⚙️ Configurable Business Rule Engine** — 30+ domain-specific rules detect congestion, safety violations, prolonged wait times, and operational anomalies
- **📊 Automated KPI Generation** — Real-time computation of loading times, waiting times, productivity scores, and utilization rates
- **🔔 Smart Alerting** — Context-aware, configurable alerts with severity levels, aggregation, and suppression rules
- **📈 Power BI Integration** — Structured analytics datasets are directly consumable by Power BI for executive dashboards
- **📁 Modular CSV/JSON Storage** — All detections, events, KPIs, and alerts are persisted in structured, queryable formats
- **🧹 Automated Data Management** — Archival, backup, and cleanup workers maintain system hygiene without manual intervention

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **🧠 YOLOv8 Detection** | State-of-the-art object detection with 10+ trained warehouse classes |
| **👤 ByteTrack Tracking** | Real-time, occlusion-robust multi-object tracking across frames |
| **🏭 Business Rule Engine** | 30+ configurable rules for congestion, safety, productivity, and events |
| **📈 KPI Engine** | Automated loading time, waiting time, productivity, and utilization computation |
| **🚨 Alert Engine** | Severity-based, aggregatable, suppressible operational alerts |
| **📊 Interactive Dashboard** | React + TypeScript frontend with real-time visualizations |
| **📋 Power BI Integration** | Export-ready analytics datasets for enterprise BI tools |
| **📁 CSV/JSON Storage** | All structured data persisted in portable, queryable formats |
| **📤 Video Upload & Processing** | Batch and streaming video analysis via REST API |
| **🗂️ Automated Archival** | Configurable data lifecycle management with archival and cleanup |
| **🧪 Comprehensive Testing** | Unit and integration tests across all modules |
| **🔒 JWT Authentication** | Secure role-based access control |
| **📜 OpenAPI Documentation** | Auto-generated interactive API docs |
| **🐳 Docker Support** | Containerized deployment for production scalability |

---

## 🏗️ System Architecture

The following diagram illustrates the high-level system architecture of VisionOps-AI:

```mermaid
graph TB
    subgraph "📹 Input Layer"
        A[Camera IP Feed] --> B[Video Upload API]
        C[Batch Video Files] --> B
    end

    subgraph "🧠 AI Processing Pipeline"
        B --> D[Frame Extractor]
        D --> E[YOLO Detector]
        E --> F[ByteTrack Tracker]
        F --> G[Detection Validator]
        G --> H[Object Classifier]
    end

    subgraph "⚙️ Business Logic Layer"
        H --> I[Business Rule Engine]
        I --> J[Event Engine]
        I --> K[Alert Engine]
        I --> L[KPI Engine]
        I --> M[Summary Engine]
    end

    subgraph "📊 Analytics Layer"
        L --> N[Analytics Pipeline]
        M --> N
        K --> N
        N --> O[Aggregator]
        O --> P[Power BI Dataset]
        O --> Q[Dashboard Dataset]
    end

    subgraph "💾 Storage Layer"
        D --> R[Extracted Frames]
        H --> S[CSV Manager]
        J --> S
        K --> S
        L --> S
        O --> T[JSON Manager]
        S --> U[(alerts.csv)]
        S --> V[(detections.csv)]
        S --> W[(events.csv)]
        S --> X[(kpis.csv)]
        T --> Y[(analytics.csv)]
        T --> Z[(summary.json)]
    end

    subgraph "📱 API & Presentation Layer"
        AA[FastAPI Backend] --> AB[REST API]
        AB --> AC[React Dashboard]
        AB --> AD[Power BI]
        AE[Background Workers] --> AA
    end

    subgraph "🔐 Infrastructure"
        AF[JWT Auth Middleware]
        AG[Logging Middleware]
        AH[Exception Handler]
        AI[Redis Cache]
        AJ[Docker Container]
    end

    AC --> AI
    AD --> P
```

---

## 🔄 Overall Workflow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI Backend
    participant Pipeline as AI Pipeline
    participant Business as Business Engine
    participant Analytics as Analytics Layer
    participant Storage as CSV/JSON Storage
    participant Dashboard as React Dashboard

    User->>API: Upload Video
    API->>API: Validate & Store Video
    API->>Pipeline: Start Processing

    activate Pipeline
    Pipeline->>Pipeline: Extract Frames
    Pipeline->>Pipeline: YOLO Detection
    Pipeline->>Pipeline: ByteTrack Tracking
    Pipeline->>Pipeline: Validate Detections
    Pipeline->>Pipeline: Classify Objects
    deactivate Pipeline

    Pipeline->>Business: Detected Objects
    activate Business
    Business->>Business: Apply Business Rules
    Business->>Business: Generate Events
    Business->>Business: Compute KPIs
    Business->>Business: Evaluate Alerts
    Business->>Business: Build Summary
    deactivate Business

    Business->>Storage: Persist Results
    activate Analytics
    Storage->>Analytics: Read Raw Data
    Analytics->>Analytics: Clean & Transform
    Analytics->>Analytics: Aggregate Metrics
    Analytics->>Analytics: Build Datasets
    deactivate Analytics

    Storage-->>Dashboard: Poll for Updates
    Dashboard->>API: Fetch Analytics
    API->>Storage: Query Data
    Storage-->>API: Return Results
    API-->>Dashboard: JSON Response
    Dashboard->>Dashboard: Render Visualizations

    User->>Dashboard: View Real-time KPIs
    User->>Dashboard: View Alerts
    User->>Dashboard: View Reports
```

---

## 🛠️ Technology Stack

### 🎨 Frontend

| Technology | Purpose |
|------------|---------|
| **React 18+** | UI component library for building the interactive dashboard |
| **TypeScript** | Type-safe JavaScript for robust frontend development |
| **React Router** | Client-side routing for multi-page navigation |
| **Recharts / D3.js** | Data visualization and charting libraries |
| **Axios** | HTTP client for API communication |
| **React Query** | Server state management and caching |
| **CSS Modules / Tailwind CSS** | Utility-first styling framework |
| **React Hook Form** | Form validation and management |
| **Jest / React Testing Library** | Unit and component testing |

### ⚙️ Backend

| Technology | Purpose |
|------------|---------|
| **Python 3.13+** | Core programming language |
| **FastAPI** | High-performance async web framework for REST APIs |
| **Uvicorn** | ASGI server for production-grade serving |
| **Pydantic v2** | Data validation and settings management |
| **SQLAlchemy 2.0** | ORM for database interactions |
| **Alembic** | Database migration management |
| **Jinja2** | Template rendering for reports |
| **OpenAPI / Swagger** | Auto-generated API documentation |
| **Redis** | In-memory caching and task queuing |
| **Celery** | Distributed task queue for async processing |

### 🧠 AI / Computer Vision

| Technology | Purpose |
|------------|---------|
| **YOLOv8 (Ultralytics)** | State-of-the-art object detection model |
| **ByteTrack** | Multi-object tracking algorithm for consistent ID assignment |
| **OpenCV** | Video processing, frame extraction, and image manipulation |
| **Supervision** | Detection annotation, visualization, and tracking utilities |
| **NumPy** | Numerical computation for array and matrix operations |
| **Pillow (PIL)** | Image processing and manipulation |
| **ONNX Runtime** | Optimized model inference acceleration |
| **Albumentations** | Image augmentation for training pipeline |

### 📊 Analytics & Visualization

| Technology | Purpose |
|------------|---------|
| **Pandas** | Data manipulation, aggregation, and analysis |
| **Power BI** | Enterprise business intelligence dashboard integration |
| **Power BI REST API** | Dataset push and report embedding |
| **Matplotlib** | Static plot generation for reports |
| **OpenPyXL** | Excel report generation |
| **ReportLab** | PDF report generation |
| **Plotly** | Interactive chart generation |

### 💾 Storage

| Technology | Purpose |
|------------|---------|
| **PostgreSQL** | Primary relational database for structured data |
| **CSV Files** | Portable structured data storage for detections, events, KPIs, alerts |
| **JSON Files** | Summary and analytics data storage |
| **MinIO / S3** | Object storage for videos and extracted frames |
| **Redis** | In-memory cache for real-time dashboard data |

### 🛠️ Tools & DevOps

| Technology | Purpose |
|------------|---------|
| **Docker & Docker Compose** | Containerization and orchestration |
| **DVC** | Data version control for model and dataset tracking |
| **Git** | Version control system |
| **pytest** | Testing framework with coverage reporting |
| **Flake8** | Code linting and style enforcement |
| **Black** | Code formatting |
| **Pre-commit** | Git hook automation |
| **GitHub Actions** | CI/CD pipeline automation |
| **Loguru** | Structured logging |
| **python-dotenv** | Environment variable management |

---

## 📁 Project Directory Structure

```
VisionOps-AI/
│
├── README.md                                    # Project documentation
│
├── backend/                                      # Main backend application
│   ├── main.py                                   # FastAPI application entry point
│   ├── pyproject.toml                            # Python project configuration
│   ├── requirements.txt                          # Production dependencies
│   ├── requirements-dev.txt                      # Development dependencies
│   └── .gitignore                                # Git ignore rules
│   │
│   ├── ai/                                       # 🤖 AI & Computer Vision Module
│   │   ├── __init__.py
│   │   ├── pipeline.py                           # Orchestrates the full AI pipeline
│   │   ├── video_processor.py                    # Video loading, decoding, metadata extraction
│   │   ├── frame_extractor.py                    # Frame sampling at configurable FPS
│   │   ├── yolo_detector.py                      # YOLOv8 inference wrapper
│   │   ├── bytetrack_tracker.py                  # ByteTrack multi-object tracker
│   │   ├── detection_validator.py                # Confidence filtering & validation
│   │   ├── object_classifier.py                  # Fine-grained object classification
│   │   ├── inference_engine.py                   # Abstract inference interface
│   │   ├── models/
│   │   │   ├── config/
│   │   │   │   └── classes.yaml                  # Class mapping configuration
│   │   │   └── detection/                        # YOLO model weights (gitignored)
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── drawing.py                        # Annotation & visualization utilities
│   │       ├── image_utils.py                    # Image processing helpers
│   │       └── video_utils.py                    # Video I/O utilities
│   │
│   ├── analytics/                                # 📈 Analytics & BI Module
│   │   ├── __init__.py
│   │   ├── pipeline.py                           # End-to-end analytics pipeline
│   │   ├── loader.py                             # Data loading from CSV/JSON sources
│   │   ├── cleaner.py                            # Data cleaning & preprocessing
│   │   ├── transformer.py                        # Feature engineering & transformation
│   │   ├── aggregator.py                         # Metric aggregation & summarization
│   │   ├── dashboard_dataset.py                  # Dashboard-optimized dataset builder
│   │   ├── powerbi_dataset.py                    # Power BI-compatible dataset builder
│   │   └── report_generator.py                   # PDF/Excel report generation
│   │
│   ├── api/                                      # 🌐 REST API Layer
│   │   ├── __init__.py
│   │   ├── router.py                             # Central API router aggregation
│   │   ├── dependencies.py                       # FastAPI dependency injection
│   │   ├── health.py                             # Health check endpoints
│   │   ├── videos.py                             # Video upload & management endpoints
│   │   ├── analysis.py                           # Analysis request & status endpoints
│   │   ├── analytics.py                          # Analytics data endpoints
│   │   ├── dashboard.py                          # Dashboard data endpoints
│   │   ├── reports.py                            # Report generation endpoints
│   │   ├── auth.py                               # Authentication endpoints
│   │   └── settings.py                           # System settings endpoints
│   │
│   ├── business/                                 # ⚙️ Business Logic Engine
│   │   ├── __init__.py
│   │   ├── business_engine.py                    # Central business logic orchestrator
│   │   ├── event_engine.py                       # Event detection & generation
│   │   ├── alert_engine.py                       # Alert evaluation & dispatch
│   │   ├── kpi_engine.py                         # KPI computation
│   │   ├── summary_engine.py                     # Session & daily summary generation
│   │   ├── calculators/
│   │   │   ├── __init__.py
│   │   │   ├── loading_time.py                   # Loading/unloading duration calculator
│   │   │   ├── waiting_time.py                   # Dock/truck waiting time calculator
│   │   │   ├── productivity.py                   # Worker productivity calculator
│   │   │   ├── utilization.py                    # Dock/forklift utilization calculator
│   │   │   └── statistics.py                     # Statistical analysis utilities
│   │   └── rules/
│   │       ├── __init__.py
│   │       ├── worker_rules.py                   # Worker behavior rules
│   │       ├── forklift_rules.py                 # Forklift operation rules
│   │       ├── truck_rules.py                    # Truck movement rules
│   │       ├── loading_rules.py                  # Loading dock rules
│   │       ├── congestion_rules.py               # Congestion detection rules
│   │       └── alert_rules.py                    # Alert threshold configuration
│   │
│   ├── config/                                   # ⚙️ Configuration Files
│   │   ├── ai_config.yaml                        # AI model & pipeline configuration
│   │   ├── business_rules.yaml                   # Business rule & threshold configuration
│   │   ├── logging.yaml                          # Logging configuration
│   │   ├── powerbi.yaml                          # Power BI integration settings
│   │   └── settings.yaml                         # Application-wide settings
│   │
│   ├── core/                                     # 🔧 Core Framework
│   │   ├── __init__.py
│   │   ├── config.py                             # Centralized configuration management
│   │   ├── constants.py                          # Application-wide constants
│   │   ├── dependencies.py                       # Core dependency injection
│   │   ├── logging.py                            # Structured logging setup
│   │   ├── security.py                           # JWT, hashing, encryption utilities
│   │   └── startup.py                            # Application startup procedures
│   │
│   ├── middleware/                               # 🛡️ Middleware Layer
│   │   ├── __init__.py
│   │   ├── authentication.py                     # JWT authentication middleware
│   │   ├── cors.py                               # CORS configuration
│   │   ├── exception_handler.py                  # Global exception handling
│   │   ├── logging.py                            # Request/response logging
│   │   └── timing.py                             # Request timing middleware
│   │
│   ├── models/                                   # 🗄️ Data Models
│   │   ├── __init__.py
│   │   ├── video.py                              # Video metadata model
│   │   ├── detection.py                          # Detection record model
│   │   ├── event.py                              # Business event model
│   │   ├── alert.py                              # Alert model
│   │   ├── kpi.py                                # KPI model
│   │   ├── analysis.py                           # Analysis session model
│   │   ├── report.py                             # Report model
│   │   ├── settings.py                           # Settings model
│   │   └── user.py                               # User & role model
│   │
│   ├── schemas/                                  # 📝 Pydantic Schemas
│   │   ├── __init__.py
│   │   ├── common.py                             # Common shared schemas
│   │   ├── video.py                              # Video request/response schemas
│   │   ├── analysis.py                           # Analysis request/response schemas
│   │   ├── analytics.py                          # Analytics data schemas
│   │   ├── dashboard.py                          # Dashboard response schemas
│   │   ├── report.py                             # Report request/response schemas
│   │   ├── auth.py                               # Authentication schemas
│   │   ├── settings.py                           # Settings schemas
│   │   └── response.py                           # Standard API response schemas
│   │
│   ├── services/                                 # 🏢 Service Layer
│   │   ├── __init__.py
│   │   ├── video_service.py                      # Video management business logic
│   │   ├── analysis_service.py                   # Analysis orchestration service
│   │   ├── analytics_service.py                  # Analytics data service
│   │   ├── dashboard_service.py                  # Dashboard data service
│   │   ├── report_service.py                     # Report generation service
│   │   ├── auth_service.py                       # Authentication & authorization
│   │   ├── settings_service.py                   # Settings management service
│   │   └── notification_service.py               # Alert notification service
│   │
│   ├── storage/                                  # 💾 Storage Module
│   │   ├── __init__.py
│   │   ├── storage_service.py                    # Storage abstraction layer
│   │   ├── csv_manager.py                        # CSV file read/write operations
│   │   ├── json_manager.py                       # JSON file read/write operations
│   │   ├── file_manager.py                       # File system operations
│   │   ├── archive_manager.py                    # Data archival management
│   │   └── backup_manager.py                     # Backup & restore management
│   │
│   ├── workers/                                  # ⏳ Background Workers
│   │   ├── __init__.py
│   │   ├── scheduler.py                          # Task scheduler configuration
│   │   ├── analysis_worker.py                    # Async video analysis worker
│   │   ├── analytics_worker.py                   # Async analytics computation worker
│   │   └── cleanup_worker.py                     # Periodic cleanup & archival worker
│   │
│   ├── exceptions/                               # ❌ Custom Exceptions
│   │   ├── __init__.py
│   │   ├── api_exceptions.py                     # API-specific exceptions
│   │   ├── ai_exceptions.py                      # AI module exceptions
│   │   ├── analytics_exceptions.py               # Analytics module exceptions
│   │   ├── storage_exceptions.py                 # Storage module exceptions
│   │   └── validation_exceptions.py              # Data validation exceptions
│   │
│   ├── utils/                                    # 🛠️ Utility Functions
│   │   ├── __init__.py
│   │   ├── csv_utils.py                          # CSV parsing helpers
│   │   ├── json_utils.py                         # JSON manipulation helpers
│   │   ├── file_utils.py                         # File system helpers
│   │   ├── date_utils.py                         # Date/time utilities
│   │   ├── math_utils.py                         # Statistical math helpers
│   │   ├── id_generator.py                       # Unique ID generation
│   │   ├── timer.py                              # Execution timing utilities
│   │   └── validation.py                         # Input validation helpers
│   │
│   ├── tests/                                    # 🧪 Test Suite
│   │   ├── __init__.py
│   │   ├── test_upload.py                        # Video upload tests
│   │   ├── test_analysis.py                      # Analysis pipeline tests
│   │   ├── test_business.py                      # Business engine tests
│   │   ├── test_analytics.py                     # Analytics pipeline tests
│   │   ├── test_dashboard.py                     # Dashboard API tests
│   │   ├── test_reports.py                       # Report generation tests
│   │   ├── test_storage.py                       # Storage module tests
│   │   └── test_auth.py                          # Authentication tests
│   │
│   ├── scripts/                                  # 📜 Utility Scripts
│   │   ├── initialize_project.py                 # First-time project setup
│   │   ├── create_default_files.py               # Default data file creation
│   │   ├── backup_data.py                        # Manual data backup
│   │   ├── clean_outputs.py                      # Output directory cleanup
│   │   └── reset_project.py                      # Project state reset
│   │
│   ├── data/                                     # 📊 Runtime Data
│   │   ├── videos.csv                            # Video metadata registry
│   │   ├── detections.csv                        # Object detection records
│   │   ├── events.csv                            # Business events log
│   │   ├── alerts.csv                            # Generated alerts log
│   │   ├── kpis.csv                              # KPI time-series data
│   │   ├── analytics.csv                         # Aggregated analytics data
│   │   ├── summary.json                          # Session summary data
│   │   ├── raw/                                  # Raw uploaded videos
│   │   ├── processed/                            # Processed video output
│   │   ├── analytics/                            # Analytics output files
│   │   └── archive/                              # Archived data files
│   │
│   ├── uploads/                                  # 📤 Upload Directory
│   │   ├── videos/                               # Uploaded video files
│   │   └── thumbnails/                           # Video thumbnail images
│   │
│   ├── outputs/                                  # 📦 Processing Outputs
│   │   ├── extracted_frames/                     # Extracted video frames
│   │   ├── detection_images/                     # Annotated detection images
│   │   ├── annotated_videos/                     # Processed videos with overlays
│   │   ├── previews/                             # Preview thumbnails
│   │   └── reports/                              # Generated PDF/Excel reports
│   │
│   ├── reports/                                  # 📁 Generated Reports
│   │   ├── pdf/                                  # PDF report output
│   │   ├── excel/                                # Excel report output
│   │   └── json/                                 # JSON report output
│   │
│   ├── docs/                                     # 📚 Documentation
│   │   ├── architecture.md                       # Architecture documentation
│   │   ├── development.md                        # Developer guide
│   │   ├── api_examples.md                       # API usage examples
│   │   └── openapi.json                          # OpenAPI specification
│   │
│   └── logs/                                     # 📝 Log Files
│
└── frontend/                                     # (Refer to Frontend Architecture)
```

---

## 🎨 Frontend Architecture

The frontend is a **React 18+** single-page application built with **TypeScript**, designed to consume VisionOps-AI's REST API and provide an intuitive, real-time warehouse monitoring experience. The architecture follows a modular, component-based structure organized as follows:

### 📦 Core Modules

| Module | Description |
|--------|-------------|
| **Authentication** | Login, registration, password reset, and session management with JWT tokens stored in HTTP-only cookies |
| **Dashboard** | Main operational view with real-time KPI widgets, live detection feed, alert ticker, and system status indicators |
| **Video Management** | Upload interface with drag-and-drop, progress tracking, video library with search/filter, and metadata editing |
| **Analysis Viewer** | Detailed analysis results display including annotated video playback, frame-by-frame detection inspection, and object trajectory visualization |
| **Analytics** | Interactive charts (Recharts/D3.js) for KPI trends, heatmaps for congestion analysis, and exportable data tables |
| **Reports** | Report generation interface with date range selection, metric picker, and one-click PDF/Excel download |
| **Alerts** | Real-time alert feed with severity filtering, acknowledgement workflow, and historical alert search |
| **Settings** | User preferences, notification configuration, system settings, and business rule threshold adjustments |
| **Admin Panel** | User management, role assignment, system monitoring, and audit log viewer |

### 🧩 Component Architecture

```
src/
├── components/           # Reusable UI components
│   ├── common/          # Buttons, inputs, modals, tables
│   ├── charts/          # Recharts/D3 chart components
│   ├── layout/          # Header, sidebar, footer
│   └── widgets/         # KPI cards, alert badges, status indicators
├── pages/               # Route-level page components
├── hooks/               # Custom React hooks (useAuth, useWebSocket, etc.)
├── services/            # API client (Axios), WebSocket client
├── store/               # State management (React Query + Context)
├── types/               # TypeScript type definitions
├── utils/               # Utility functions
└── styles/              # CSS modules and Tailwind config
```

### 🔄 Data Flow

1. User interacts with React components
2. Components call custom hooks that wrap Axios API calls
3. React Query manages caching, deduplication, and background refetching
4. API responses are validated against TypeScript types
5. State updates propagate through React's virtual DOM
6. Real-time updates arrive via WebSocket connections
7. Charts and widgets re-render with new data

---

## 🧠 Backend Architecture

The backend follows a **layered architecture** with clear separation of concerns, dependency injection, and middleware-based cross-cutting concerns.

### 📐 Architectural Layers

```
┌─────────────────────────────────────────────────┐
│                 🌐 API Layer                     │
│          (FastAPI Routers / Endpoints)           │
├─────────────────────────────────────────────────┤
│                 🏢 Service Layer                  │
│          (Business Logic Orchestration)          │
├─────────────────────────────────────────────────┤
│   ⚙️ Business Engine  │  🧠 AI Pipeline          │
│   (Business Logic)    │  (Computer Vision)       │
├─────────────────────────────────────────────────┤
│             💾 Storage Layer                      │
│     (CSV, JSON, File System, S3)                 │
├─────────────────────────────────────────────────┤
│   🗄️ Models & Schemas │  🛠️ Utils                │
│   (Data Definition)   │  (Helpers)               │
└─────────────────────────────────────────────────┘
```

### 🧩 Core Backend Modules

| Module | Description |
|--------|-------------|
| **`api/`** | FastAPI route handlers organized by domain (videos, analysis, analytics, dashboard, reports, auth, settings, health). Each router defines endpoints, request validation via Pydantic schemas, and response serialization. |
| **`services/`** | Business logic orchestration layer that sits between API routers and domain engines. Encapsulates complex workflows, coordinates multiple engines, and handles transaction boundaries. |
| **`core/`** | Application foundation including configuration management (`config.py`), security utilities (JWT, hashing), structured logging setup, application constants, and startup initialization routines. |
| **`middleware/`** | Cross-cutting concerns implemented as ASGI middleware: JWT authentication, CORS headers, request/response logging, execution timing, and global exception handling. |
| **`models/`** | Data models representing core domain entities (Video, Detection, Event, Alert, KPI, Analysis, Report, Settings, User). Used by storage layer for schema enforcement. |
| **`schemas/`** | Pydantic v2 schemas for API request/response validation, serialization, and OpenAPI documentation generation. |
| **`exceptions/`** | Domain-specific exception hierarchy with custom error codes, messages, and HTTP status mappings. |
| **`workers/`** | Background task processing via Celery workers: analysis processing, analytics computation, and periodic cleanup/archival tasks. |
| **`scripts/`** | Administrative CLI tools for project initialization, data seeding, backup/restore, output cleanup, and environment reset. |

### 🔌 Dependency Injection

FastAPI's dependency injection system is used extensively for:
- Database session management
- Current user authentication context
- Configuration loading per request
- Service instantiation with proper lifecycle
- Rate limiting and throttling

---

## 🤖 AI Processing Pipeline

The AI pipeline is the core intelligence engine of VisionOps-AI. It transforms raw video streams into structured, actionable data through a multi-stage processing flow:

```mermaid
flowchart LR
    A[Video Input] --> B[🎞️ Frame Extraction]
    B --> C[🔍 YOLO Detection]
    C --> D[🔄 ByteTrack Tracking]
    D --> E[✅ Detection Validation]
    E --> F[🏷️ Object Classification]
    F --> G[📊 CSV/JSON Output]
    F --> H[⚙️ Business Rules]
    H --> I[📈 KPI Generation]
    H --> J[🚨 Alert Generation]
```

### 1️⃣ Video Upload

- **Supported Formats**: MP4, AVI, MOV, MKV, FLV
- **Upload Mechanism**: Multipart POST request with chunked upload support for large files
- **Validation**: Format verification, codec detection, resolution check, duration validation
- **Storage**: Raw files stored in `uploads/videos/` with metadata registered in `data/videos.csv`
- **Preprocessing**: Transcoding to standard format, thumbnail generation, metadata extraction

### 2️⃣ Frame Extraction

- **Module**: `ai/frame_extractor.py`
- **Configuration**: Configurable extraction rate via `ai_config.yaml` (default: 5 FPS)
- **Method**: Decodes video using OpenCV and samples frames at specified intervals
- **Output**: Frames saved as JPEG images in `outputs/extracted_frames/`
- **Optimization**: Skip identical frames using histogram comparison to reduce redundancy

### 3️⃣ YOLO Detection

- **Module**: `ai/yolo_detector.py`
- **Model**: Ultralytics YOLOv8 (nano, small, or medium variants based on performance requirements)
- **Classes Detected**:
  - Worker, Forklift, Pallet Jack, Truck, Trailer
  - Pallet, Inventory Rack, Dock Door, Safety Cone
  - Cart, Tote, Stretch Wrapper, Dock Leveler
- **Output**: Bounding boxes, confidence scores, class labels per frame
- **Optimization**: ONNX Runtime inference, batch processing, GPU acceleration (CUDA)

### 4️⃣ ByteTrack Tracking

- **Module**: `ai/bytetrack_tracker.py`
- **Algorithm**: ByteTrack multi-object tracking with Kalman filter prediction
- **Capabilities**:
  - Consistent object ID assignment across frames
  - Occlusion handling via re-identification
  - Trajectory computation (entry/exit points, paths)
  - Dwell time calculation per object
- **Output**: Tracked objects with stable IDs, trajectory history, and movement vectors

### 5️⃣ Detection Validation

- **Module**: `ai/detection_validator.py`
- **Confidence Threshold**: Configurable per class (default: 0.5)
- **Validation Rules**:
  - Minimum confidence filter
  - Non-maximum suppression (NMS) for overlapping boxes
  - Temporal consistency check (object must appear in N consecutive frames)
  - Size ratio validation (reject improbable object dimensions)
  - Zone-based filtering (restrict detections to defined ROI)

### 6️⃣ Business Rule Engine

- **Module**: `business/business_engine.py`
- **Input**: Validated detections with tracking IDs
- **Processing**: Applies 30+ configurable warehouse rules
- **Output**: Structured business events with timestamps and context
- **Integration**: Feeds into KPI Engine, Alert Engine, and Event Engine simultaneously

### 7️⃣ KPI Generation

- **Module**: `business/kpi_engine.py`
- **Key Metrics**:
  - **Loading Time**: Duration from dock door open to truck departure
  - **Waiting Time**: Truck arrival to dock assignment duration
  - **Worker Productivity**: Tasks completed per unit time
  - **Dock Utilization**: Percentage of time dock is actively used
  - **Forklift Utilization**: Active vs idle time ratio
  - **Congestion Index**: Number of objects per zone normalized by area
- **Storage**: Time-series data written to `data/kpis.csv`

### 8️⃣ Alert Generation

- **Module**: `business/alert_engine.py`
- **Alert Types**:
  - **Congestion Alerts**: Dock area exceeding object density threshold
  - **Prolonged Wait Alerts**: Truck waiting > configurable duration
  - **Safety Alerts**: Personnel in restricted zones, forklift speed violations
  - **Productivity Alerts**: Worker idle time exceeding threshold
  - **Equipment Alerts**: Forklift/pallet jack prolonged inactivity
- **Severity Levels**: INFO, WARNING, CRITICAL
- **Suppression**: Configurable cooldown period to prevent alert storms

### 9️⃣ CSV/JSON Storage

- **Module**: `storage/csv_manager.py`, `storage/json_manager.py`
- **Data Files**:
  - `detections.csv` — All validated detections with frame, class, confidence, bbox
  - `events.csv` — Business events with type, timestamp, involved objects
  - `kpis.csv` — Time-series KPI measurements
  - `alerts.csv` — Generated alerts with severity, message, timestamp
  - `analytics.csv` — Aggregated analytics for dashboard consumption
  - `summary.json` — Session-level summary statistics

### 🔟 Analytics Pipeline

- **Module**: `analytics/pipeline.py`
- **Stages**:
  1. **Load** — Read raw data from CSV/JSON files
  2. **Clean** — Remove outliers, handle missing values, normalize timestamps
  3. **Transform** — Feature engineering, time-based aggregation, window functions
  4. **Aggregate** — Compute hourly/daily/session summaries
  5. **Build Datasets** — Generate `analytics.csv` and Power BI-compatible datasets
- **Output**: Cleaned, aggregated data ready for visualization

### 1️⃣1️⃣ Dashboard

- **Backend**: `api/dashboard.py` serves dashboard-specific aggregated data
- **Frontend**: React dashboard renders real-time KPI cards, charts, alert feed, and video player
- **Data Refresh**: Configurable polling interval with Redis caching for performance
- **Visualizations**: Time-series charts, bar charts, pie charts, heatmaps, status indicators

---

## 📜 Business Rules

VisionOps-AI includes a comprehensive **Business Rule Engine** with 30+ configurable rules organized into six categories:

### 👷 Worker Rules (`business/rules/worker_rules.py`)

| Rule | Description | Default Threshold |
|------|-------------|-------------------|
| Worker Presence | Detect worker entry/exit in zone | — |
| Worker Idle Detection | Flag worker with no movement for N seconds | 120s |
| Worker Congregation | Alert when >N workers in same zone | 5 workers |
| Restricted Zone Entry | Alert when worker enters prohibited area | — |
| Worker Productivity | Calculate active vs idle time ratio | <60% triggers alert |

### 🚜 Forklift Rules (`business/rules/forklift_rules.py`)

| Rule | Description | Default Threshold |
|------|-------------|-------------------|
| Forklift Movement | Track forklift entry/exit and path | — |
| Forklift Idle Detection | Flag forklift stationary for N seconds | 180s |
| Forklift Speed Estimation | Estimate speed based on frame-to-frame movement | — |
| Forklift Congestion | >N forklifts in loading zone | 3 forklifts |
| Forklift-Dock Association | Link forklift to dock activity | — |

### 🚛 Truck Rules (`business/rules/truck_rules.py`)

| Rule | Description | Default Threshold |
|------|-------------|-------------------|
| Truck Arrival | Detect truck entry into yard/dock area | — |
| Truck Departure | Detect truck leaving dock area | — |
| Truck Waiting Time | Calculate time from arrival to dock assignment | >30min triggers wait alert |
| Truck Loading Time | Calculate time from dock start to departure | — |
| Truck Dock Association | Link truck to specific dock door | — |

### 🏗️ Loading Rules (`business/rules/loading_rules.py`)

| Rule | Description | Default Threshold |
|------|-------------|-------------------|
| Dock Door Activity | Track dock door open/close state changes | — |
| Loading Session Start | Detect start of loading/unloading activity | — |
| Loading Session End | Detect end of loading/unloading activity | — |
| Loading Duration | Calculate total loading/unloading time | — |
| Dock Utilization Rate | Percentage of time dock is occupied | <50% triggers utilization alert |
| Cross-Dock Activity | Detect goods transfer across adjacent docks | — |

### 🚦 Congestion Rules (`business/rules/congestion_rules.py`)

| Rule | Description | Default Threshold |
|------|-------------|-------------------|
| Zone Occupancy | Count objects per defined zone | — |
| Congestion Index | Objects per zone normalized by area | >0.8 triggers congestion alert |
| Congestion Trend | Rate of congestion increase over time | >20% in 5min triggers alert |
| Bottleneck Detection | Identify zones consistently above threshold | — |
| Peak Hour Detection | Identify time periods with max congestion | — |

### 🔔 Alert Rules (`business/rules/alert_rules.py`)

| Rule | Description | Default Threshold |
|------|-------------|-------------------|
| Severity Classification | Map business conditions to severity levels | — |
| Alert Aggregation | Merge duplicate alerts within cooldown period | 300s cooldown |
| Alert Suppression | Suppress alerts when system state is acknowledged | — |
| Escalation Rules | Escalate unacknowledged CRITICAL alerts | 600s escalation |
| Notification Routing | Route alerts to appropriate channels | — |

---

## 📊 Analytics & Power BI

### 📈 Dashboard Generation

The analytics pipeline (`analytics/pipeline.py`) processes raw operational data through a multi-stage ETL process to generate:

1. **Real-Time KPIs** — Current values for loading time, waiting time, productivity, utilization, and congestion
2. **Time-Series Trends** — Hourly, daily, and weekly KPI aggregation for trend analysis
3. **Heatmaps** — Zone-based congestion heatmaps over configurable time windows
4. **Session Summaries** — Per-loading-session performance summaries
5. **Comparative Analytics** — Day-over-day and week-over-week KPI comparisons

### 📋 Power BI Integration

VisionOps-AI generates Power BI-compatible datasets (`analytics/powerbi_dataset.py`) that can be:

1. **Directly Imported** — CSV files structured for Power BI data ingestion
2. **Pushed via REST API** — Using Power BI REST API for real-time dataset push
3. **Embedded** — Power BI reports embedded directly in the VisionOps-AI dashboard
4. **Scheduled Refresh** — Automated data refresh via Power BI Gateway

### 📄 Report Types

| Report Type | Format | Content |
|-------------|--------|---------|
| **Operations Summary** | PDF, Excel | Daily/weekly KPI summary, top alerts, zone performance |
| **Dock Performance** | PDF, Excel | Per-dock utilization, loading times, bottleneck analysis |
| **Worker Productivity** | PDF, Excel | Individual and team productivity scores, idle analysis |
| **Alert History** | PDF, Excel | Alert frequency, severity distribution, response times |
| **Congestion Analysis** | PDF, Excel, JSON | Zone heatmaps, peak hours, congestion trends |

---

## 🔌 API Overview

The VisionOps-AI REST API is built with **FastAPI** and organized into domain-specific route groups. All endpoints are auto-documented via **OpenAPI/Swagger** at `/docs`.

### 📡 API Route Groups

| Group | Prefix | Module | Description |
|-------|--------|--------|-------------|
| **Health** | `/health` | `api/health.py` | System health, readiness, and liveliness probes |
| **Videos** | `/api/videos` | `api/videos.py` | Video upload, list, get, delete, and metadata management |
| **Analysis** | `/api/analysis` | `api/analysis.py` | Analysis request, status polling, results retrieval |
| **Analytics** | `/api/analytics` | `api/analytics.py` | Analytics data queries, aggregation, export |
| **Dashboard** | `/api/dashboard` | `api/dashboard.py` | Dashboard-specific aggregated data endpoints |
| **Reports** | `/api/reports` | `api/reports.py` | Report generation request, download, history |
| **Auth** | `/api/auth` | `api/auth.py` | Login, register, refresh, logout, password management |
| **Settings** | `/api/settings` | `api/settings.py` | System settings CRUD, user preferences |

### 📋 Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Authenticate user and return JWT tokens |
| `POST` | `/api/auth/register` | Register a new user account |
| `POST` | `/api/videos/upload` | Upload a video file for processing |
| `GET` | `/api/videos` | List all uploaded videos with metadata |
| `GET` | `/api/videos/{id}` | Get video details by ID |
| `DELETE` | `/api/videos/{id}` | Delete a video and associated data |
| `POST` | `/api/analysis/start` | Start a new video analysis session |
| `GET` | `/api/analysis/{id}/status` | Poll analysis session status |
| `GET` | `/api/analysis/{id}/results` | Retrieve analysis results |
| `GET` | `/api/analytics/kpis` | Query KPI data with time filters |
| `GET` | `/api/analytics/alerts` | Query alert history |
| `GET` | `/api/dashboard/summary` | Get dashboard summary data |
| `GET` | `/api/dashboard/trends` | Get time-series trend data |
| `POST` | `/api/reports/generate` | Generate a new report |
| `GET` | `/api/reports/{id}/download` | Download a generated report |
| `GET` | `/health` | Health check and system status |

> **Full API documentation** is available via Swagger UI at `http://localhost:8000/docs` after starting the backend server.

---

## 💾 Data Storage

VisionOps-AI uses a **hybrid storage architecture** combining structured CSV files for operational data, JSON for summary/analytics data, and the file system for media assets.

### 📄 CSV Files

| File | Location | Schema | Purpose |
|------|----------|--------|---------|
| `videos.csv` | `data/videos.csv` | id, filename, path, format, resolution, duration, fps, status, uploaded_at, processed_at | Video metadata registry |
| `detections.csv` | `data/detections.csv` | id, video_id, frame_number, timestamp, class_id, class_name, confidence, x1, y1, x2, y2, tracker_id | Raw object detection records |
| `events.csv` | `data/events.csv` | id, video_id, timestamp, event_type, event_name, object_ids, zone, duration, metadata | Business events log |
| `kpis.csv` | `data/kpis.csv` | id, video_id, timestamp, metric_name, metric_value, unit, category, zone | Time-series KPI data |
| `alerts.csv` | `data/alerts.csv` | id, video_id, timestamp, severity, alert_type, message, object_ids, acknowledged, acknowledged_at | Alert log |
| `analytics.csv` | `data/analytics.csv` | id, timestamp, metric_name, metric_value, dimension, granularity, session_id | Aggregated analytics |

### 📋 JSON Files

| File | Location | Schema | Purpose |
|------|----------|--------|---------|
| `summary.json` | `data/summary.json` | session_id, video_id, duration, total_frames, total_detections, events[], kpis{}, alerts[], timestamp | Session summary data |

### 🗂️ Directory Structure

| Directory | Purpose | Lifecycle |
|-----------|---------|-----------|
| `uploads/videos/` | Raw uploaded video files | Archived after processing |
| `uploads/thumbnails/` | Video thumbnail previews | Retained permanently |
| `outputs/extracted_frames/` | Extracted video frames | Periodic cleanup |
| `outputs/detection_images/` | Annotated detection frames | Periodic cleanup |
| `outputs/annotated_videos/` | Processed videos with overlays | Retained on demand |
| `outputs/previews/` | Preview images for UI | Retained permanently |
| `outputs/reports/` | Generated PDF/Excel reports | Retained permanently |
| `data/archive/` | Archived data files | Configurable retention |
| `data/processed/` | Intermediate processing data | Cleaned after processing |
| `data/analytics/` | Analytics output files | Retained for BI access |
| `logs/` | Application logs | Configurable rotation |
| `reports/pdf/` | PDF report output | Retained permanently |
| `reports/excel/` | Excel report output | Retained permanently |
| `reports/json/` | JSON report output | Retained permanently |

---

## 📦 Installation Guide

### ✅ Prerequisites

Before installing VisionOps-AI, ensure you have the following installed:

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.13+ | Core runtime |
| **Node.js** | 18+ | Frontend runtime |
| **npm** | 9+ | Package management |
| **PostgreSQL** | 14+ | Primary database |
| **Redis** | 6+ | Caching & task queue |
| **Docker** | 24+ | Containerization (optional) |
| **Git** | 2.30+ | Version control |
| **Make** | (optional) | Build automation |

### 📥 Step-by-Step Installation

#### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-org/VisionOps-AI.git
cd VisionOps-AI
```

#### 2️⃣ Create Virtual Environment

```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
# source venv/bin/activate
```

#### 3️⃣ Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# For development, install additional dependencies
pip install -r requirements-dev.txt
```

#### 4️⃣ Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
# See Environment Variables section below for all required variables
```

#### 5️⃣ Initialize the Database

```bash
# Run database migrations (if using SQLAlchemy + Alembic)
# alembic upgrade head

# Or initialize with default data
python scripts/initialize_project.py
```

#### 6️⃣ Start the Backend Server

```bash
# Start the FastAPI development server
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 7️⃣ Start the Frontend (if applicable)

```bash
cd frontend
npm install
npm start
```

#### 8️⃣ Verify Installation

- Backend API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`
- Frontend Dashboard: `http://localhost:3000`
- Health Check: `http://localhost:8000/health`

---

## 🔐 Environment Variables

Create a `.env` file in the project root with the following variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | ✅ | `VisionOps-AI` | Application name |
| `APP_VERSION` | ✅ | `1.0.0` | Application version |
| `DEBUG` | ✅ | `false` | Debug mode enabled/disabled |
| `SECRET_KEY` | ✅ | — | JWT signing secret (generate with `openssl rand -hex 32`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | `30` | JWT access token expiry (minutes) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ✅ | `7` | JWT refresh token expiry (days) |
| `ALGORITHM` | ✅ | `HS256` | JWT signing algorithm |
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string (`postgresql://user:pass@localhost:5432/visionops`) |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` | Redis connection string |
| `CORS_ORIGINS` | ✅ | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `UPLOAD_DIR` | ✅ | `uploads/videos/` | Video upload directory |
| `OUTPUT_DIR` | ✅ | `outputs/` | Processing output directory |
| `DATA_DIR` | ✅ | `data/` | Data storage directory |
| `LOG_LEVEL` | ✅ | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_DIR` | ✅ | `logs/` | Log file directory |
| `MAX_UPLOAD_SIZE` | ✅ | `1073741824` | Max upload size in bytes (1GB) |
| `ALLOWED_EXTENSIONS` | ✅ | `.mp4,.avi,.mov,.mkv` | Allowed video file extensions |
| `FRAME_EXTRACTION_FPS` | ✅ | `5` | Frame extraction rate (FPS) |
| `YOLO_MODEL_PATH` | ✅ | — | Path to YOLO model weights |
| `YOLO_CONFIDENCE_THRESHOLD` | ✅ | `0.5` | YOLO detection confidence threshold |
| `YOLO_IOU_THRESHOLD` | ✅ | `0.45` | YOLO NMS IOU threshold |
| `BYTETRACK_TRACK_THRESHOLD` | ✅ | `0.5` | ByteTrack matching threshold |
| `BYTETRACK_HIGH_THRESHOLD` | ✅ | `0.6` | ByteTrack high score threshold |
| `BYTETRACK_MISSED_FRAME_LIMIT` | ✅ | `30` | ByteTrack max missed frames before termination |
| `POWERBI_ENABLED` | ✅ | `false` | Power BI integration enabled |
| `POWERBI_CLIENT_ID` | ❌ | — | Power BI client ID |
| `POWERBI_CLIENT_SECRET` | ❌ | — | Power BI client secret |
| `POWERBI_TENANT_ID` | ❌ | — | Power BI tenant ID |
| `POWERBI_WORKSPACE_ID` | ❌ | — | Power BI workspace ID |
| `POWERBI_DATASET_ID` | ❌ | — | Power BI dataset ID |
| `SMTP_HOST` | ❌ | — | Email notification SMTP host |
| `SMTP_PORT` | ❌ | `587` | Email notification SMTP port |
| `SMTP_USERNAME` | ❌ | — | Email notification SMTP username |
| `SMTP_PASSWORD` | ❌ | — | Email notification SMTP password |
| `NOTIFICATION_EMAIL_FROM` | ❌ | — | Notification sender email |
| `ADMIN_EMAIL` | ❌ | — | Admin notification email |

---

## 🚀 Running the Project

### 🧪 Development Mode

```bash
# Terminal 1: Start the backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start the frontend
cd frontend
npm start

# Terminal 3: Start Celery worker (if using async processing)
celery -A workers.scheduler worker --loglevel=info
```

**Development features:**
- Hot-reload enabled for both backend (`--reload`) and frontend (`HMR`)
- Detailed debug-level logging
- Auto-generated OpenAPI docs at `/docs`
- CORS configured for local development origins
- SQLAlchemy echo mode (query logging) for debugging

### 🏭 Production Mode

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or manually:
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

**Production considerations:**
- Set `DEBUG=false`
- Use a production-grade ASGI server (Uvicorn with Gunicorn process manager)
- Configure proper PostgreSQL credentials (not root)
- Set up Redis for caching and task queuing
- Configure reverse proxy (Nginx) for SSL termination and load balancing
- Enable comprehensive monitoring and alerting
- Regular database backups (use `scripts/backup_data.py`)
- Configure log rotation and retention policies

---

## 📸 Screenshots

> Screenshots will be added as the project matures. Below are placeholder descriptions of each major screen.

### 🏠 Landing Page

```
┌──────────────────────────────────────────────────────┐
│  [Logo]  VisionOps-AI                     [Login]    │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  AI-Powered Warehouse Operations             │   │
│  │  Intelligence Platform                       │   │
│  │                                              │   │
│  │  [Get Started]  [Learn More]  [View Demo]    │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Features:  Detection  Tracking  Analytics  Alerts   │
│  Stats:   10K+ Videos  500+ Warehouses  99.9% Uptime│
└──────────────────────────────────────────────────────┘
```

### 📊 Dashboard

```
┌──────────────────────────────────────────────────────┐
│  📊 Dashboard                         [Alerts (3)]   │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                 │
│ │Loading│ │Waiting│ │Product│ │Utiliz │                 │
│ │ 12min │ │ 8min │ │ 87%  │ │ 72%  │                 │
│ └──────┘ └──────┘ └──────┘ └──────┘                 │
│ ┌─────────────────────────────────────────────────┐   │
│ │  KPI Trends (Last 24 Hours)                    │   │
│ │  [📈 Line Chart: Loading Time Trend]           │   │
│ └─────────────────────────────────────────────────┘   │
│ ┌─────────────┐ ┌─────────────────────────────────┐   │
│ │  Alerts    │ │  Live Detection Feed            │   │
│ │  🔴 CRIT  │ │  [📹 Annotated Video Feed]      │   │
│ │  🟡 WARN   │ │                                 │   │
│ └─────────────┘ └─────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### 📤 Upload

```
┌──────────────────────────────────────────────────────┐
│  📤 Upload Video                                     │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │                                              │   │
│  │     Drag & Drop video files here              │   │
│  │     or click to browse                        │   │
│  │                                              │   │
│  │     Supported: MP4, AVI, MOV, MKV            │   │
│  │     Max size: 1GB                            │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Recent Uploads:                                      │
│  ├─ warehouse_1.mp4   [████████░░] 80%  Processing  │
│  ├─ dock_5_am.mp4     [██████████] 100% Completed   │
│  └─ loading_bay.mp4   [░░░░░░░░░░] 0%   Queued     │
└──────────────────────────────────────────────────────┘
```

### 🧠 AI Detection

```
┌──────────────────────────────────────────────────────┐
│  🧠 Analysis Results              Video: dock_5.mp4  │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  [Annotated Video Player with bounding boxes] │   │
│  │  Worker #12  ┌─────┐                         │   │
│  │              │  👷  │  Confidence: 0.94      │   │
│  │              └─────┘                         │   │
│  │  Forklift #3 ┌──────┐                        │   │
│  │              │ 🚜  │  Confidence: 0.89      │   │
│  │              └──────┘                        │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Detection Summary:                                  │
│  Workers: 12  Forklifts: 3  Trucks: 2  Pallets: 18  │
│  Total Objects: 35           Tracked IDs: 24        │
└──────────────────────────────────────────────────────┘
```

### 📈 Analytics

```
┌──────────────────────────────────────────────────────┐
│  📈 Analytics                   Period: Last 7 Days  │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Loading Time Trend                          │   │
│  │  ╱╲    ╱╲    ╱╲    ╱╲                          │   │
│  │ ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲                         │   │
│  │╱    ╲╱    ╲╱    ╲╱    ╲                        │   │
│  │ Mon  Tue  Wed  Thu  Fri  Sat  Sun              │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────┐ ┌─────────────────────────────────┐│
│  │  Top Alerts │ │  Zone Congestion Heatmap        ││
│  │  1. Dock 3  │ │  ┌─────┬─────┬─────┐           ││
│  │  2. Dock 1  │ │  │🔥🔥 │ 🟡  │ 🟢  │           ││
│  │  3. Zone B  │ │  ├─────┼─────┼─────┤           ││
│  └─────────────┘ │  │ 🟢  │ 🟡  │🔥🔥 │           ││
│                   │  └─────┴─────┴─────┘           ││
│                   └────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

### 📋 Reports

```
┌──────────────────────────────────────────────────────┐
│  📋 Reports                                          │
│                                                      │
│  ┌─────────┬──────────┬────────┬────────┬────────┐  │
│  │  Name   │   Type   │ Period │ Status │ Action │  │
│  ├─────────┼──────────┼────────┼────────┼────────┤  │
│  │ Ops Sum │ PDF      │ Weekly │ ✅     │ [📥]  │  │
│  │ Dock 3  │ Excel    │ Daily  │ ✅     │ [📥]  │  │
│  │ Alerts  │ PDF      │ Hourly │ ⏳     │ [👁️]  │  │
│  │ Congest │ JSON     │ Daily  │ ❌     │ [🔄]  │  │
│  └─────────┴──────────┴────────┴────────┴────────┘  │
│                                                      │
│  Generate New Report:                                │
│  Type: [Operations Summary]  Period: [This Week]     │
│  [Generate Report]                                   │
└──────────────────────────────────────────────────────┘
```

---

## 📝 Logging

VisionOps-AI implements a **comprehensive, structured logging system** using Loguru, with configuration managed via `config/logging.yaml`.

### 🔧 Logging Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Rotation** | `10 MB` | Rotate log files when they reach 10MB |
| **Retention** | `30 days` | Keep log files for 30 days |
| **Compression** | `zip` | Compress rotated log files |
| **Format** | `{time} | {level} | {name} | {function} | {message}` | Structured log format |
| **Console Level** | `INFO` | Minimum level for console output |
| **File Level** | `DEBUG` | Minimum level for file output |

### 📋 Log Categories

| Category | File | Description |
|----------|------|-------------|
| **API Access** | `logs/api.log` | All HTTP request/response logs |
| **AI Pipeline** | `logs/ai.log` | Model inference, detection, tracking logs |
| **Business Engine** | `logs/business.log` | Rule evaluation, event generation logs |
| **Analytics** | `logs/analytics.log` | ETL pipeline, aggregation logs |
| **Errors** | `logs/errors.log` | All exceptions and error traces |
| **Workers** | `logs/workers.log` | Background task execution logs |

### 🌟 Structured Logging

All logs are emitted in structured format, enabling easy ingestion by log aggregation tools (ELK, Grafana Loki, Datadog):

```json
{
  "timestamp": "2025-01-15T14:30:00.123Z",
  "level": "INFO",
  "module": "ai.yolo_detector",
  "function": "detect",
  "message": "Frame 1245 processed",
  "extras": {
    "video_id": "vid_001",
    "frame_number": 1245,
    "detections": 12,
    "inference_time_ms": 45.2
  }
}
```

---

## ⚠️ Error Handling

VisionOps-AI implements a **multi-layered error handling strategy**:

### 🎯 Custom Exception Hierarchy

```
Exception
├── VisionOpsException (base)
│   ├── APIException
│   │   ├── NotFoundException
│   │   ├── UnauthorizedException
│   │   ├── ForbiddenException
│   │   ├── BadRequestException
│   │   ├── ConflictException
│   │   └── RateLimitException
│   ├── AIException
│   │   ├── ModelLoadException
│   │   ├── InferenceException
│   │   └── TrackingException
│   ├── AnalyticsException
│   │   ├── DataLoadException
│   │   └── AggregationException
│   ├── StorageException
│   │   ├── FileNotFoundException
│   │   ├── FileWriteException
│   │   └── ArchiveException
│   └── ValidationException
│       ├── SchemaValidationException
│       └── BusinessRuleValidationException
```

### 🌐 Global Exception Handler

The `middleware/exception_handler.py` middleware catches all unhandled exceptions and returns consistent API responses:

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Video with ID 'vid_999' not found",
    "details": {
      "video_id": "vid_999",
      "resource_type": "video"
    }
  },
  "request_id": "req_a1b2c3d4",
  "timestamp": "2025-01-15T14:30:00.123Z"
}
```

### 🔄 Retry & Fallback

- **AI Pipeline**: Automatic retry on transient inference failures (3 retries with exponential backoff)
- **Storage Operations**: Retry on file I/O errors with configurable retry count
- **Worker Tasks**: Automatic retry with dead-letter queue for persistently failing tasks
- **External Services**: Circuit breaker pattern for Power BI API calls

---

## 🔒 Security

### 🛡️ Authentication & Authorization

| Mechanism | Implementation |
|-----------|----------------|
| **JWT Tokens** | Access + Refresh token pattern with RS256 signing |
| **Password Hashing** | bcrypt with configurable rounds (default: 12) |
| **Token Storage** | HTTP-only, Secure, SameSite=Strict cookies |
| **Token Rotation** | Refresh token rotation on each use |
| **Rate Limiting** | Per-endpoint rate limiting via Redis |
| **Session Management** | Token blacklist on logout |

### 🚧 Middleware Security

| Middleware | Protection |
|------------|------------|
| **CORS** | Strict origin validation, whitelist-based |
| **Authentication** | JWT verification on protected routes |
| **Request Validation** | Pydantic schema validation on all inputs |
| **SQL Injection** | Parameterized queries via SQLAlchemy |
| **XSS Protection** | Content-Type enforcement, output encoding |
| **CSRF** | Double-submit cookie pattern for state-changing requests |
| **Helmet-like Headers** | Security headers via middleware |

### 🔐 Data Protection

- **At Rest**: Encrypted storage for sensitive configuration (`.env` excluded from version control)
- **In Transit**: TLS/SSL enforced in production
- **API Keys**: Hashed storage, masked in logs
- **File Uploads**: Extension validation, MIME type checking, malware scanning (optional)

---

## ⚡ Performance

### 🚄 Optimizations

| Area | Optimization | Impact |
|------|--------------|--------|
| **AI Inference** | ONNX Runtime + CUDA GPU acceleration | 2-5x inference speedup |
| **Frame Extraction** | Multi-threaded extraction with histogram-based dedup | 40% fewer frames processed |
| **Batch Processing** | Batched YOLO inference (max batch size: 16) | 3x throughput improvement |
| **Caching** | Redis caching for dashboard queries | <50ms response times |
| **Database** | Indexed CSV queries, connection pooling | Fast data retrieval |
| **Workers** | Celery async task processing | Non-blocking API responses |
| **File I/O** | Buffered writes, async file operations | Minimal I/O latency |
| **Memory** | Configurable frame buffer limits | Controlled memory usage |

### 📊 Benchmarks (Reference)

| Operation | Metric | Target |
|-----------|--------|--------|
| Frame Extraction | FPS | 30+ FPS (1080p) |
| YOLO Inference | ms/frame | <30ms (GPU), <150ms (CPU) |
| ByteTrack Update | ms/frame | <5ms |
| Full Pipeline (1 min video) | Total time | <2 minutes |
| API Response (cached) | Latency | <50ms |
| API Response (uncached) | Latency | <500ms |
| Dashboard Load | Page load | <2 seconds |

---

## 🧪 Testing

VisionOps-AI includes a **comprehensive test suite** with both unit and integration tests.

### 📁 Test Structure

| Test File | Module Under Test | Type |
|-----------|-------------------|------|
| `tests/test_upload.py` | Video upload functionality | Integration |
| `tests/test_analysis.py` | Analysis pipeline | Integration |
| `tests/test_business.py` | Business rule engine | Unit + Integration |
| `tests/test_analytics.py` | Analytics pipeline | Unit + Integration |
| `tests/test_dashboard.py` | Dashboard API | Integration |
| `tests/test_reports.py` | Report generation | Unit |
| `tests/test_storage.py` | CSV/JSON storage | Unit |
| `tests/test_auth.py` | Authentication | Integration |

### 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_business.py -v

# Run tests by keyword
pytest -k "kpi"

# Run with verbose output
pytest -v --tb=long
```

### ✅ Testing Goals

| Metric | Target |
|--------|--------|
| **Code Coverage** | >85% |
| **Unit Tests** | >100 |
| **Integration Tests** | >50 |
| **API Tests** | All endpoints covered |
| **Business Rule Tests** | Each rule has minimum 3 test cases |

---

## 🗺️ Future Roadmap

### Phase 2: Scale & Enhance

- [ ] **Multi-Camera Support** — Simultaneous processing of multiple camera feeds
- [ ] **Real-Time Streaming** — WebSocket-based live video analysis with sub-second latency
- [ ] **Custom Model Training** — Web UI for uploading labeled datasets and training custom YOLO models
- [ ] **Advanced Analytics** — Machine learning-based predictive analytics for congestion forecasting

### Phase 3: Enterprise

- [ ] **Multi-Warehouse Support** — Unified management across multiple warehouse locations
- [ ] **RBAC Enhancement** — Granular role-based access control with resource-level permissions
- [ ] **Synthetic Data Generation** — Create training data from simulated warehouse environments
- [ ] **Integration Marketplace** — Plugins for WMS, ERP, and OMS systems

### Phase 4: Intelligence

- [ ] **Generative AI Reports** — LLM-powered natural language report generation and insights
- [ ] **Anomaly Detection** — Unsupervised learning for detecting unusual operational patterns
- [ ] **Automated Optimization** — AI-driven recommendations for dock allocation and worker scheduling
- [ ] **Digital Twin** — Real-time 3D digital twin of warehouse operations

---

## 📌 Version History

| Version | Date | Description |
|---------|------|-------------|
| **v1.0.0** | Q1 2025 | Initial release with core AI pipeline, business rules, KPI engine, and dashboard |
| **v0.9.0** | Q4 2024 | Beta release with YOLOv8 detection, ByteTrack tracking, and basic analytics |
| **v0.5.0** | Q3 2024 | Alpha release with video upload, frame extraction, and detection validation |
| **v0.1.0** | Q2 2024 | Project initialization and architectural foundation |

---

## 🤝 Contributing Guidelines

We welcome contributions from the community! Here's how you can help make VisionOps-AI better:

### 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a branch** for your feature or fix
4. **Make your changes** following our coding standards
5. **Write tests** for your changes
6. **Run the test suite** to ensure nothing is broken
7. **Submit a pull request** with a clear description

### 📏 Coding Standards

| Standard | Enforcement |
|----------|-------------|
| **Python Style** | PEP 8 via Flake8 |
| **Python Formatting** | Black (line length: 100) |
| **Type Hints** | Required for all function signatures |
| **Docstrings** | Google-style docstrings required for public APIs |
| **Import Order** | isort with Black-compatible configuration |
| **Commit Messages** | Conventional Commits specification |
| **Branch Naming** | `feature/`, `fix/`, `docs/`, `refactor/` prefixes |

### 🧪 Before Submitting

- [ ] All tests pass locally (`pytest`)
- [ ] Code is formatted with Black (`black .`)
- [ ] Imports are sorted (`isort .`)
- [ ] Linting passes (`flake8`)
- [ ] Type checks pass (`mypy .`)
- [ ] New features include tests
- [ ] Documentation is updated (if applicable)
- [ ] No sensitive data or secrets in code

### 📋 Pull Request Process

1. Ensure your PR description clearly describes the problem and solution
2. Reference any related issues using `Fixes #issue_number`
3. Update documentation if your changes affect public APIs or behavior
4. Add or update tests to cover your changes
5. Request review from at least one maintainer
6. Address all review comments before merging

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](backend/LICENSE) file for details.

```
MIT License

Copyright (c) 2025 VisionOps-AI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgements

VisionOps-AI builds upon several outstanding open-source projects and research contributions:

- **[Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)** — State-of-the-art object detection framework
- **[ByteTrack](https://github.com/ifzhang/ByteTrack)** — Multi-object tracking by associating every detection box
- **[FastAPI](https://github.com/tiangolo/fastapi)** — Modern, fast web framework for building APIs
- **[OpenCV](https://opencv.org/)** — Comprehensive computer vision library
- **[Supervision](https://github.com/roboflow/supervision)** — Computer vision annotation and visualization tools
- **[Pydantic](https://github.com/pydantic/pydantic)** — Data validation using Python type annotations
- **[React](https://reactjs.org/)** — UI component library
- **[Power BI](https://powerbi.microsoft.com/)** — Business intelligence and analytics platform
- **[Redis](https://redis.io/)** — In-memory data structure store
- **[PostgreSQL](https://www.postgresql.org/)** — Advanced relational database
- **[Docker](https://www.docker.com/)** — Containerization platform
- **[DVC](https://dvc.org/)** — Data version control

---

## 📬 Contact Information

| Channel | Details |
|---------|---------|
| **Project Maintainer** | [Your Name](mailto:your.email@example.com) |
| **GitHub Issues** | [github.com/your-org/VisionOps-AI/issues](https://github.com/your-org/VisionOps-AI/issues) |
| **Discussions** | [github.com/your-org/VisionOps-AI/discussions](https://github.com/your-org/VisionOps-AI/discussions) |
| **Documentation** | [visionops-ai.readthedocs.io](https://visionops-ai.readthedocs.io) |
| **Twitter / X** | [@VisionOpsAI](https://twitter.com/VisionOpsAI) |
| **LinkedIn** | [VisionOps-AI](https://linkedin.com/company/visionops-ai) |

---

## 👥 Project Credits

### 🏗️ Architecture & Design

| Role | Contributor |
|------|-------------|
| **System Architect** | [Name] |
| **Backend Lead** | [Name] |
| **Frontend Lead** | [Name] |
| **AI/ML Engineer** | [Name] |
| **DevOps Engineer** | [Name] |

### 🤝 Contributors

<a href="https://github.com/your-org/VisionOps-AI/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=your-org/VisionOps-AI" alt="Contributors">
</a>

### 💖 Support

If you find VisionOps-AI valuable, please consider:

- ⭐ **Starring** the repository on GitHub
- 🐛 **Reporting bugs** and suggesting features via Issues
- 📢 **Sharing** the project with your network
- 🤝 **Contributing** code, documentation, or feedback

---

<p align="center">
  Made with ❤️ for the open-source community
  <br>
  <strong>VisionOps-AI</strong> — Seeing your warehouse operations clearly
  <br>
  <br>
  <a href="https://github.com/your-org/VisionOps-AI">
    <img src="https://img.shields.io/badge/GitHub-VisionOps--AI-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
  <a href="https://github.com/your-org/VisionOps-AI/issues">
    <img src="https://img.shields.io/badge/Report%20Bug-FF6B6B?style=for-the-badge&logo=bugcrowd&logoColor=white" alt="Report Bug">
  </a>
  <a href="https://github.com/your-org/VisionOps-AI/discussions">
    <img src="https://img.shields.io/badge/Join%20Discussion-5865F2?style=for-the-badge&logo=discourse&logoColor=white" alt="Join Discussion">
  </a>
</p>

