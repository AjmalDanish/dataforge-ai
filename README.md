# DataForge AI v1.0.0

> Autonomous Multi-Agent Data Science Platform powered by True Graph Engineering

---

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Coverage](https://img.shields.io/badge/coverage-76%25-green.svg)
![Status](https://img.shields.io/badge/status-RC--orange.svg)
![Agents](https://img.shields.io/badge/agents-7-blue.svg)

**DataForge AI** is an autonomous platform that orchestrates 7 specialized AI agents through a true branching graph workflow to analyze structured datasets. Simply provide a dataset file, and DataForge AI will dynamically plan, execute, validate, and report insights—completely autonomously.

This is **not** a chatbot. This is **not** AutoML. This is **not** a linear pipeline. This is an autonomous AI system with intelligent decision-making at every step.

---

## 🚀 Quick Start

### Installation

```bash
# Install via pip (from source)
pip install -e \"langgraph>=0.0.0\"

# Install with dependencies
pip install langgraph pandas plotly scipy pyarrow pydantic openai anthropic

# Clone and setup
git clone https://github.com/yourusername/dataforge-ai.git
cd dataforge-ai
pip install -e -r -e .
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

**Verbose Mode**
```bash
python run.py datasets/employees.csv --verbose
```

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

### 4. Technology Stack

- **Python 3.11+** with type hints
- **LangGraph** for graph orchestration
- **Pandas** for data manipulation
- **Plotly** for interactive visualizations
- **SciPy** for statistical tests
- **PyArrow** for Parquet support
- **Pydantic** for data validation
- **OpenAI** or **Anthropic** for LLM providers
- **Click** for CLI interface

---

## 🏗️ Architecture

### Clean Architecture

```
dataforge/
├── agents/               # 7 specialized agents
│   ├── base.py              # Base agent abstract class
│   ├── planner.py           # Decision engine
│   ├── evaluator.py         # Quality validation
│   ├── ingestion.py         # Data loading
│   ├── profiling.py         # Column analysis
│   ├── statistics.py        # Statistical analysis
│   ├── visualization.py       # Visualizations
│   └── reporting.py          # Report generation
├── core/                 # Core infrastructure
│   ├── llm.py               # LLM abstraction
│   ├── logger.py             # Structured logging
│   ├── state.py             # State management
│   └── __init__.py
├── graph/                # Workflow orchestration
│   ├── workflow.py          # LangGraph definition
│   └── __init__.py
├── infrastructure/        # External integrations
│   └── llm_providers/       # LLM providers
│       ├── openai.py           # OpenAI provider
│       └── anthropic.py        #  Anthropic provider
├── presentation/         # User interfaces
│   ├── cli.py              # CLI interface
│   └── __init__.py
└── shared/               # Shared utilities
    ├── config.py             # Settings
    ├── errors.py             # Custom exceptions
    └── utils.py              # Helper functions
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

## 📊 Example Output

### Sample Dataset

**datasets/employees.csv** (15 rows × 8 columns)

| id | name | age | department | salary | years_of_service | performance_score | remote_worker |
|----|------|-----|-------------|--------|-----------------|------------------|---------------|
| 1 | Alice Johnson | 28 | Engineering | 75000.0 | 2 | 8.5 | True |
| 2 | Bob Smith | 35 | Sales | 65000.0 | 5 | 7.2 | False |
| 3 | Charlie Brown | 42 | Engineering | 95000.0 | 10 | 9.1 | True |

### Generated Output

```
output/employees/
├── report.html                    # Interactive HTML report
├── report.json                    # Machine-readable JSON
├── execution_*.log                # Structured execution logs
└── visualizations/                # Generated charts
    ├── distribution_*.html           # Distribution plots
    ├── boxplot_*.html              # Box plots
    ├── correlation_heatmap.html        # Correlation matrix
    ├── scatter_*.html              # Scatter plots
    └── bar_*.html                  # Bar charts
```

### Example HTML Report

- **Profile Section**: Data shape, column types, missing value analysis
- **Statistics Section**: Descriptive statistics, correlations, outliers, distribution tests
- **Visualizations Section**: Interactive charts with filtering
- **Insights Section**: Data quality, statistics, correlations, visualization insights

---

## 📖 Documentation

### Core Documentation
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md) - Complete system architecture
- **[AGENTS.md](docs/agents.md) - All 7 agents and workflow
- **[GRAPH_DESIGN.md](docs/graph_design.md) - LangGraph workflow design
- **[REQUIREMENTS.md](docs/requirements.md) - Functional and non-functional requirements
- **[DEVELOPMENT.md](docs/development_guide.md) - Development guide and coding standards

### Project Documentation
- **[PHASE1_SUMMARY.md](PHASE1_SUMMARY.md) - Phase 1 summary
- **[PHASE2_SUMMARY.md](PHASE2_SUMMARY.md) - Phase 2 summary
- **[FINAL_ENGINEERING_AUDIT.md](FINAL_ENGINEERING_AUDIT.md) - Engineering audit summary

---

## 🔧 Installation

### Requirements

- Python 3.11 or higher
- OpenAI or Anthropic API key
- 2GB RAM minimum
- 100MB maximum file size

### Quick Start

```bash
# Install dependencies
pip install langgraph pandas plotly scipy pyarrow pydantic openai anthropic

# Run analysis
python run.py datasets/employees.csv
```

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
- TODO comments removed (CLI workflow is now functional)
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

### v1.5 (Planned)
- Custom agent plugins
- Enhanced visualizations
- More export formats
- Better CLI interface

### v2.0 (Planned)
- Web interface
- Database connectors
- Analysis history
- Multi-user support

See [VISION.md](docs/VISION.md) for details.

---

**🎉 Version 1.0.0 is a Release Candidate!**