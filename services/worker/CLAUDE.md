# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Thrasio IQ Worker Service**, a Python-based microservice that implements AI-powered data analysis workflows using LangGraph and LangChain. The service integrates with Google Cloud services (BigQuery, Vertex AI) to provide intelligent data analytics capabilities.

## Development Commands

### Package Management (uv)
This project uses `uv` as the package manager instead of pip:
```bash
uv sync                    # Install dependencies from lockfile
uv add <package>           # Add new dependency
uv remove <package>        # Remove dependency
uv run <command>           # Run command in virtual environment
```

**Important Dependencies:**
- `db-dtypes`: Required for pandas BigQuery data type compatibility
- `google-cloud-bigquery==3.27.0`: Compatible version (avoid 3.28.0)

### Code Quality
```bash
uv run black .             # Format code
uv run isort .             # Sort imports
uv run flake8             # Lint code
uv run mypy app/          # Type checking
```

### Testing
```bash
uv run pytest             # Run all tests
uv run pytest tests/test_config.py  # Run specific test file
uv run pytest -v          # Run tests with verbose output
```

### Type Checking
The project uses both `mypy` (configured in pyproject.toml) and `pyright` (configured in pyrightconfig.json):
```bash
uv run mypy app/          # MyPy type checking
pyright                   # Pyright type checking (if installed globally)
```

### Logging Configuration
The project uses structured logging with different modes:
- **CLI Mode**: Quiet logging with text format (hides verbose third-party logs)  
- **Service Mode**: JSON structured logging for production monitoring
- **Debug Mode**: Detailed logging for development

Key logging components:
- `CLIQuietFilter`: Suppresses noisy logs from LangGraph, LangChain, etc.
- Third-party logger levels automatically set to WARNING
- CLI automatically configures quiet mode for better user experience

## Architecture

### Core Components

**Configuration System (`app/core/config.py`)**
- Centralized settings management using Pydantic
- Environment-specific configurations (development, staging, production)
- Separate configs for Google Cloud, LLM, Worker, and Langsmith services
- Uses `get_settings()` function to access global settings instance

**Agent Framework (`app/agents/`)**
- `BaseAgent`: Abstract base class for all AI agents
- Implements async `run()` and `astream()` methods
- Uses LangChain message types and state management

**BigQuery Integration (`app/tools/bigquery/`)**
- `BigQueryClient`: Main client wrapper with enhanced functionality
- Supports parameterized queries, dry runs, and result pagination
- Includes dataset/table exploration capabilities
- Built-in logging and error handling

**Tool Ecosystem (`app/tools/`)**
- Modular tool structure for different integrations
- Currently includes: BigQuery, Gmail, Looker, Monday, NetSuite, Zendesk
- Each tool has its own client and specialized functionality

### Key Design Patterns

1. **Pydantic Configuration**: All settings use Pydantic models with environment variable support
2. **Structured Logging**: Uses `structlog` for consistent, structured logging throughout
3. **Async-First**: Agents and workflows are built with async/await patterns
4. **Type Safety**: Strong typing with mypy enforcement (strict mode enabled)

### Google Cloud Integration

**Dual Project Setup**:
- Main GCP project: `thrasio-dev-ai-agent` (for AI/ML services)
- BigQuery project: `thrasio-dev-data-wh-7ee095` (for data warehouse)

**Authentication**: Uses Google Application Default Credentials or service account JSON files

## Environment Variables

Key environment variables (see `app/core/config.py` for complete list):
- `GCP_PROJECT_ID`: Main Google Cloud project
- `GCP_BIGQUERY_PROJECT_ID`: BigQuery-specific project  
- `LLM_MODEL_NAME`: AI model to use (default: gemini-2.5-flash)
- `ENVIRONMENT`: development/staging/production
- `LANGSMITH_TRACING`: Enable LangSmith tracing

## File Structure Notes

- `app/` contains all application code
- `app/core/` has configuration and logging setup
- `app/agents/` contains AI agent implementations
- `app/tools/` has integrations with external services
- `app/workflows/` is currently empty (future workflow definitions)
- `pyproject.toml` defines dependencies and tool configurations
- Uses `uv.lock` for dependency locking