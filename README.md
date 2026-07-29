# DataForge AI

> Autonomous Multi-Agent Data Science Platform powered by True Graph Engineering

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**DataForge AI** is an autonomous platform that orchestrates specialized AI agents through a **true branching graph workflow** to analyze structured datasets. Simply provide a dataset file, and DataForge AI will dynamically plan, execute, validate, and report insights—completely autonomously.

This is **not** a chatbot. This is **not** AutoML. This is **not** a linear pipeline. This is an autonomous AI system with intelligent decision-making at every step.

## 🚀 Quick Start

```bash
# Install
pip install dataforge-ai

# Set your API key
export OPENAI_API_KEY="sk-..."

# Analyze a dataset
dataforge analyze data.csv
```

Output:
- `report.md` - Markdown report with insights
- `report.html` - Interactive HTML report
- `visualizations/` - Publication-quality charts
- `execution_*.log` - Structured execution logs

## ✨ Features

- **True Graph Workflow**: Dynamic agent selection with branching (not a linear pipeline)
- **Planner Agent**: Intelligent decision-making adapts to your data
- **Validation Loops**: Quality assurance with automatic remediation
- **7 Specialized Agents**: Planner, Evaluator, Ingestion, Profiling, Statistics, Visualization, Reporting
- **Vendor-Agnostic**: Abstract LLM interface (OpenAI, Anthropic, extensible)
- **Built-in Observability**: Structured logging for every operation
- **Privacy First**: Data never leaves your environment (except LLM API calls)

## 📋 What DataForge AI Does

Given a structured dataset, DataForge AI will:

1. **Plan** - Analyze requirements and determine execution path
2. **Ingest** - Read and validate your data
3. **Profile** - Understand structure, types, and characteristics
4. **Analyze** - Compute statistics, correlations, and detect patterns
5. **Validate** - Check quality and request additional analysis if needed
6. **Visualize** - Generate relevant, publication-quality charts
7. **Report** - Compile comprehensive insights with explanations

All with intelligent decision-making at every step. All without coding.

## 🏗️ Architecture

DataForge AI is built on **Clean Architecture** principles with:

- **True Graph Orchestration**: Dynamic branching via LangGraph
- **Centralized State**: Unified GraphState shared by all agents
- **Abstract Interfaces**: Vendor-agnostic LLM integration
- **Built-in Observability**: Structured logging throughout

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
       │Ingestion │  │Profiling │  │Statistics│
       │  Agent   │  │  Agent   │  │  Agent   │
       └────┬─────┘  └────┬─────┘  └────┬─────┘
            │            │            │
            └─────┬──────┴─────┬──────┘
                  │            │
                  ▼            ▼
           ┌─────────────┐ ┌─────────────┐
           │Visualization│ │ Evaluator  │ ← Quality check
           │   Agent     │ │   Agent     │   (can retry)
           └──────┬──────┘ └──────┬──────┘
                  │              │
                  └──────┬───────┘
                         │
                  ┌─────────────┐
                  │  Reporting  │
                  │   Agent     │
                  └──────┬──────┘
                         │
                    ┌─────────┐
                    │   END   │
                    └─────────┘
```

## 🔧 Installation

### From PyPI (Coming Soon)

```bash
pip install dataforge-ai
```

### From Source

```bash
git clone https://github.com/yourusername/dataforge-ai.git
cd dataforge-ai
poetry install
```

### Requirements

- Python 3.11 or higher
- OpenAI or Anthropic API key
- 2GB RAM minimum

## 📖 Usage

### Basic Analysis

```bash
dataforge analyze path/to/dataset.csv
```

### Specify Output Directory

```bash
dataforge analyze data.csv --output ./results
```

### Use Anthropic Instead of OpenAI

```bash
dataforge analyze data.csv --provider anthropic
```

### Verbose Logging

```bash
dataforge analyze data.csv --verbose
```

## 📊 Example Output

After analysis, you'll find:

```
output/
├── report.md              # Markdown report
├── report.html            # HTML report
├── execution_*.log        # Execution log
├── logs_*.json            # Structured logs (JSON)
└── visualizations/        # Generated charts
    ├── histogram_*.png
    ├── bar_*.png
    ├── heatmap_correlations.png
    └── scatter_*.png
```

## 🤝 Contributing

We welcome contributions! Please see [DEVELOPMENT.md](docs/DEVELOPMENT.md) for guidelines.

## 📚 Documentation

### Core Documentation
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Complete system architecture, components, and principles
- **[REQUIREMENTS.md](docs/REQUIREMENTS.md)** - Functional and non-functional requirements
- **[AGENTS.md](docs/AGENTS.md)** - All 7 agents and true graph workflow
- **[VISION.md](docs/VISION.md)** - Project vision and 5-year roadmap
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development guide and coding standards

### Architecture Review
- **[ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md)** - Critical review, changes, and rationale

## 🗺️ Roadmap

### v1.0 (Current - 5 Day Sprint)
- ✅ Architecture complete
- 🔄 Core infrastructure
- ⏳ 7 specialized agents
- ⏳ True graph workflow with Planner
- ⏳ CLI interface
- ⏳ CSV/Parquet support

### v1.5 (Planned)
- Custom agent plugins
- Analysis templates
- Enhanced visualizations
- More export formats

### v2.0 (Planned)
- Web interface
- Database connectors
- Analysis history
- Multi-user support

See [VISION.md](docs/VISION.md) for details.

## 🌟 What Makes DataForge AI Different?

| Feature | DataForge AI | Chatbots | AutoML | Linear Pipelines |
|---------|--------------|----------|--------|-----------------|
| Autonomous Analysis | ✅ | ❌ | ❌ | ✅ |
| Dynamic Decision Making | ✅ | ❌ | ❌ | ❌ |
| Validation Loops | ✅ | ❌ | ❌ | ❌ |
| Complete Reports | ✅ | ❌ | ❌ | ❌ |
| True Graph Workflow | ✅ | ❌ | ❌ | ❌ |
| Vendor-Agnostic LLM | ✅ | ❌ | ❌ | ✅ |
| Built-in Observability | ✅ | ❌ | ❌ | ✅ |
| Multi-Agent System | ✅ | ❌ | ❌ | ✅ |

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) - Graph orchestration
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [Plotly](https://plotly.com/) - Visualization
- [OpenAI](https://openai.com/) & [Anthropic](https://www.anthropic.com/) - LLM providers

## 📮 Contact

- GitHub Issues: [Report bugs and request features](https://github.com/yourusername/dataforge-ai/issues)
- Discussions: [Ask questions and share ideas](https://github.com/yourusername/dataforge-ai/discussions)

## ⭐ Star History

If you find DataForge AI useful, please consider giving it a star!

---

**Built with ❤️ for the data science community**