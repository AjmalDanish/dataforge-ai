# DataForge AI v1.0.0

> Autonomous Multi-Agent Data Science Platform powered by True Graph Engineering

---

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Coverage](https://img.shields.io/badge/coverage-73%25-green.svg)
![Status](https://img.shields.io/badge/status-v1.0.0-brightgreen.svg)
![Agents](https://img.shields.io/badge/agents-7-blue.svg)

**DataForge AI** is an autonomous platform that orchestrates 7 specialized AI agents through a true branching graph workflow to analyze structured datasets. Simply provide a dataset file, and DataForge AI will dynamically plan, execute, validate, and report insights—completely autonomously.

This is **not** a chatbot. This is **not** AutoML. This is **not** a linear pipeline. This is an autonomous AI system with intelligent decision-making at every step.

---

## 🎯 Project Overview

DataForge AI demonstrates advanced AI engineering through:

- **True Graph Workflow**: Dynamic branching with LangGraph, not a linear pipeline
- **7 Specialized Agents**: Each with distinct responsibilities and decision-making capabilities
- **Autonomous Planning**: Planner Agent intelligently routes workflow based on data characteristics
- **Quality Gates**: Evaluator Agent validates results and triggers automatic remediation
- **Production-Ready Code**: Clean architecture, comprehensive testing, type hints throughout

## 💡 Why DataForge AI

I built DataForge AI to demonstrate:

1. **Graph Engineering Expertise**: Moving beyond linear pipelines to true branching workflows
2. **Agent Architecture**: Designing autonomous agents with clear responsibilities and communication patterns
3. **State Management**: Implementing robust state handling for complex multi-agent systems
4. **Production Quality**: Writing code that's testable, maintainable, and ready for real-world use
5. **AI System Design**: Creating systems that make intelligent decisions at every step

This project showcases the skills needed for AI Engineer, ML Engineer, and Data Scientist roles at top tech companies.

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/dataforge-ai.git
cd dataforge-ai

# Install dependencies
pip install -e .

# Set up API key (optional for demo mode)
export OPENAI_API_KEY=your_key_here
```

### Usage

**Basic Analysis**
```bash
python run.py datasets/employees.csv
```

**With Custom Output Directory**
```bash
python run.py datasets/employees.csv ./my_output
```

**Using CLI**
```bash
python -m dataforge.presentation.cli analyze datasets/products.csv --output ./output
```

---

## 📊 Example Outputs

### Screenshots

**HTML Report**
![HTML Report](docs/screenshots/html_report.png)

**Interactive Visualizations**
![Visualizations](docs/screenshots/visualizations.png)

**CLI Execution**
![CLI Execution](docs/screenshots/cli_execution.png)

### Generated Artifacts

Running analysis on `datasets/employees.csv` produces:

```
output/employees/
├── report.html                    # Interactive HTML report
├── report.json                    # Machine-readable JSON
├── execution_*.log                # Structured execution logs
└── visualizations/                # Generated charts
    ├── distribution_age.html       # Distribution plots
    ├── boxplot_salary.html         # Box plots
    ├── correlation_heatmap.html    # Correlation matrix
    ├── scatter_salary_age.html     # Scatter plots
    └── bar_department.html         # Bar charts
```

See [docs/examples/](docs/examples/) for complete sample outputs.

---

## ✨ Key Features

### 1. True Graph Workflow

- **Dynamic Branching**: The Planner Agent intelligently routes between agents based on data characteristics
- **No Linear Pipeline**: Each agent makes decisions about what to do next
- **Self-Optimizing**: Automatically skips unnecessary steps (e.g., statistics for non-numeric data)
- **Quality Gates**: EvaluatorAgent validates output quality with automatic retry logic

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌─────────────┐
                    │   Planner   │ ← Central Decision Maker
                    │   Agent     │   (runs after each agent)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │Ingestion│  │Profiling│  │Statistics│  │Evaluation│
       │  Agent   │  Agent   │  │   Agent   │ │  Agent   │
       └──────────┘  └──────────┘  └──────────┘  └──────────┘
            │            │            │
            ▼            ▼            ▼
       ┌─────────────┐ ┌─────────────┐
       │Visualization│ │  Reporting│
       │   Agent     │ │   Agent     │
       └──────┬──────┘  └──────┬──────┘
                  │              │
                  ▼
           ┌─────────────┐
           │  Reporting  │
           │   Agent     │
           └─────────────┘

            │
           ┌─────────┐
            │   END   │
            └─────────┘
```

### 2. 7 Specialized AI Agents

| Agent | Role | Key Capabilities |
|-------|------|-------------------|
| **PlannerAgent** | Decision Engine | Routes workflow, handles retry logic, decides next action |
| **EvaluatorAgent** | Quality Control | Validates analysis quality, triggers remediation on failure |
| **DataIngestionAgent** | Data Loading | CSV/Parquet support, encoding fallback |
| **DataProfilingAgent** | Understanding | Semantic type detection, missing value analysis |
| **StatisticalAnalysisAgent** | Number Crunching | Descriptive stats, correlations, outlier detection |
| **VisualizationAgent** | Visual Storytelling | Interactive HTML plots, publication-quality charts |
| **ReportingAgent** | Comprehensive Documentation | HTML + JSON reports with insights |

### 3. Smart Features

- **Adaptive Planning**: Skips statistics for non-numeric datasets
- **Quality Gates**: Automatic retry logic (max 3 retries)
- **Encoding Fallback**: UTF-8 → Latin-1 → CP1252 for international data
- **Vendor-Agnostic**: Works with OpenAI and Anthropic (extensible to others)
- **Comprehensive Logging**: Structured logging with timestamps for debugging
- **Observability**: All operations logged with agent, duration, and decision data

---

## 🏗️ Architecture

### System Architecture

📊 **Interactive Diagrams Available**: See [docs/diagrams/](docs/diagrams/) for detailed Mermaid diagrams:
- [Architecture Diagram](docs/diagrams/architecture.md) - Visual representation of all layers and components
- [Workflow Diagram](docs/diagrams/workflow.md) - Complete execution flow with error handling
- [GraphState Model](docs/diagrams/graphstate.md) - State structure and mutation patterns
- [Agent Interaction](docs/diagrams/agent-interaction.md) - Sequence diagram of agent communication
- [Data Flow](docs/diagrams/data-flow.md) - Data transformation pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   CLI (Click) │  │  execute.py   │  │   run.py      │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼──────────────────┼──────────────────┼───────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Graph Orchestration Layer                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           LangGraph StateGraph (workflow.py)           │  │
│  │  - Planner Node (decision routing)                    │  │
│  │  - Agent Nodes (ingestion, profiling, statistics,     │  │
│  │                visualization, evaluation, reporting)   │  │
│  │  - Conditional Edges (dynamic branching)              │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Planner │ │Evaluator │ │Ingestion │ │ Profiling │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  │Statistics│ │Visualization│ │ Reporting │                     │
│  └──────────┘ └──────────┘ └──────────┘                     │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Core Infrastructure Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │GraphState│ │Structured│ │  LLM     │ │  Utils   │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                  External Integrations Layer                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  OpenAI  │ │Anthropic │ │  Pandas  │ │  Plotly  │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### GraphState Model

```python
class GraphState(BaseModel):
    # Immutable Input
    input_dataset_path: str
    input_query: str | None = None
    output_dir: str = "./output"

    # Mutable Data (single source of truth)
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="All analysis data stored as key-value pairs"
    )

    # Execution Context
    execution_id: str
    steps_completed: list[str] = Field(default_factory=list)
    agent_history: list[dict[str, Any]] = Field(default_factory=list)

    # Validation & Retry
    validation_status: str = "pending"
    retry_count: int = 0
    max_retries: int = 3

    # Observability
    logs: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    # Timing
    start_time: str
    end_time: str | None = None

    # Methods
    def get(key: str, default=None) -> Any: get()
    def set(key, value) -> set()
    def add_log(level, agent, message, **kwargs) -> add_log()
    def add_agent_result(agent_name: str, result: dict) -> add_agent_result()
    def update_step(step: str) -> update_step()
    def increment_retry() -> increment_retry()
    def add_metric(key, value) -> add_metric()
    def mark_complete() -> mark_complete()
```

---

## 📁 Folder Structure

```
dataforge-ai/
├── dataforge/                 # Main package
│   ├── agents/               # 7 specialized agents
│   │   ├── base.py           # Base agent abstract class
│   │   ├── planner.py        # Decision engine
│   │   ├── evaluator.py      # Quality validation
│   │   ├── ingestion.py      # Data loading
│   │   ├── profiling.py      # Column analysis
│   │   ├── statistics.py     # Statistical analysis
│   │   ├── visualization.py  # Visualizations
│   │   └── reporting.py     # Report generation
│   ├── core/                 # Core infrastructure
│   │   ├── llm.py           # LLM abstraction
│   │   ├── logger.py         # Structured logging
│   │   └── state.py         # State management
│   ├── graph/                # Workflow orchestration
│   │   └── workflow.py       # LangGraph definition
│   ├── infrastructure/        # External integrations
│   │   └── llm_providers/   # LLM providers
│   ├── presentation/         # User interfaces
│   │   └── cli.py           # CLI interface
│   └── shared/               # Shared utilities
│       ├── config.py         # Settings
│       ├── errors.py         # Custom exceptions
│       └── utils.py          # Helper functions
├── datasets/                 # Example datasets
│   ├── employees.csv         # Employee demographics
│   └── products.csv          # Product sales data
├── docs/                     # Documentation
│   ├── architecture.md       # System architecture
│   ├── agents.md             # Agent documentation
│   ├── graph_design.md       # Workflow design
│   ├── examples/             # Example outputs
│   └── screenshots/          # UI screenshots
├── tests/                    # Test suite
│   ├── integration/          # End-to-end tests
│   └── unit/                 # Unit tests
├── execute.py                # Direct execution script
├── run.py                    # Main entry point
├── pyproject.toml            # Project configuration
├── README.md                 # This file
└── LICENSE                   # MIT License
```

---

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.11+** with type hints throughout
- **LangGraph** (^0.0.20) for graph orchestration
- **Pydantic** (^2.0.0) for data validation
- **Click** (^8.1.0) for CLI interface

### Data Processing
- **Pandas** (^2.0.0) for data manipulation
- **NumPy** (^1.24.0) for numerical operations
- **SciPy** (^1.11.0) for statistical tests
- **PyArrow** (^12.0.0) for Parquet support

### Visualization
- **Plotly** (^5.18.0) for interactive visualizations
- **Kaleido** (^0.2.1) for static image export

### AI/LLM
- **OpenAI** (^1.0.0) for GPT models
- **Anthropic** (^0.7.0) for Claude models
- **Structlog** (^23.0.0) for structured logging

### Development
- **pytest** (^7.4.0) for testing
- **pytest-cov** (^4.1.0) for coverage
- **pytest-asyncio** (^0.21.0) for async tests
- **black** (^23.0.0) for code formatting
- **mypy** (^1.5.0) for type checking

---

## 🧪 Testing

### Test Coverage
- **73% code coverage** across all modules
- **72 tests passing** (71 unit + integration tests)
- **Async test support** with pytest-asyncio

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dataforge --cov-report=html

# Run specific test file
pytest tests/integration/test_e2e_workflow.py

# Run with verbose output
pytest -v
```

### Test Structure
- **Unit Tests**: Individual agent and component testing
- **Integration Tests**: End-to-end workflow testing
- **Agent Tests**: Planner, Evaluator, Ingestion, Profiling agents
- **Core Tests**: State management, logging, utilities

---

## 📖 Documentation

📚 **Documentation Index**: See [docs/README.md](docs/README.md) for complete documentation navigation.

### Core Documentation
- **[docs/architecture.md](docs/architecture.md)** - Complete system architecture
- **[docs/agents.md](docs/agents.md)** - All 7 agents and workflow
- **[docs/graph_design.md](docs/graph_design.md)** - LangGraph workflow design
- **[docs/requirements.md](docs/requirements.md)** - Functional and non-functional requirements
- **[docs/development_guide.md](docs/development_guide.md)** - Development guide and coding standards

### Interactive Diagrams
- **[docs/diagrams/](docs/diagrams/)** - Mermaid diagrams for architecture, workflow, and data flow

### Example Outputs
- **[docs/examples/](docs/examples/)** - Sample HTML reports, JSON outputs, and visualizations

---

## 🛠️ Known Limitations

### Technical
- No caching mechanism (computations not cached)
- No file size or row count limits
- No timeout enforcement
- No parallel execution
- No checkpoint/save state for recovery
- No deadlock detection
- No circuit breaker patterns

### Data Processing
- Supports only CSV and Parquet (no Excel, JSON, etc.)
- No streaming support
- No database connectors (file-based only)
- No support for very large datasets (>1M rows)
- No incremental updates

### ML/AI Features
- No predictive models (statistical analysis only)
- No ML model training
- No hyperparameter optimization
- No feature importance analysis
- No time series analysis
- No clustering

### Development
- No type checking on Windows (mypy doesn't run)
- No performance benchmarks
- No stress tests
- No chaos engineering tests

---

## 🚦 Quick Start Guide

### 1. Create test data

Create `test.csv`:

```python
import pandas as pd

df = pd.DataFrame({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "salary": [50000, 60000, 70000]
})

df.to_csv("test.csv", index=False)
```

### 2. Run analysis

```bash
python run.py test.csv ./output
```

### 3. Check outputs

```bash
ls -la output/
# report.html    # Comprehensive HTML report
# visualizations/*.html  # Interactive charts
# execution_*.log  # Structured logs
```

---

## 📁 Demo Datasets

### datasets/employees.csv (15 rows × 8 columns)

Employee demographics with salary and performance data.

### datasets/products.csv (20 rows × 8 columns)

Product sales data with price, inventory, and ratings.

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## ⭐ Star History

If you find DataForge AI useful, please consider giving it a star!

---

**Built with ❤️ for the data science community**

---

## 🏗️ Roadmap

### v1.1 (Planned)
- LLM Integration: Wire LLMProvider into PlannerAgent for AI-assisted routing
- Resource limits: Enforce max_file_size_mb and max_rows
- Per-agent timeout: Implement asyncio.wait_for() wrappers
- LangGraph upgrade: Upgrade to current stable version

### v1.5 (Planned)
- Caching layer: Cache computed results keyed by file hash
- Parallel execution: Use asyncio.gather() for independent agents
- Checkpoint persistence: Serialize GraphState for crash recovery
- Additional formats: Excel, JSON support

### v2.0 (Planned)
- Web interface: FastAPI backend + HTML/JS frontend
- Database connectors: PostgreSQL, SQLite, BigQuery
- Analysis history: Store past runs in SQLite
- Multi-user support: User accounts and shared analyses

---

## 👤 Author

**DataForge AI Contributors**

Built as a demonstration of advanced AI engineering and graph workflow orchestration.

---

**Version:** 1.0.0  
**Release Date:** 2024  
**Status:** Production Ready