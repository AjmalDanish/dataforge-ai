# DataForge AI - Development Guide

## Development Overview

This guide provides comprehensive instructions for contributing to DataForge AI. Follow these standards to maintain code quality and consistency.

---

## Table of Contents
1. [Setup](#setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Documentation](#documentation)
7. [Git Workflow](#git-workflow)
8. [Common Tasks](#common-tasks)

---

## Setup

### Prerequisites
- Python 3.11 or higher
- Git
- Poetry 1.7.0 or higher
- An LLM API key (OpenAI or Anthropic)

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/dataforge-ai.git
cd dataforge-ai

# 2. Install Poetry (if not already installed)
pip install poetry

# 3. Install dependencies
poetry install

# 4. Activate virtual environment
poetry shell

# 5. Set up pre-commit hooks (optional but recommended)
pre-commit install
```

### Configuration

Create a `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env

# Edit with your API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Verification

```bash
# Run tests to verify setup
poetry run pytest

# Check code formatting
poetry run black --check .
poetry run isort --check-only .

# Type checking
poetry run mypy .
```

---

## Project Structure

```
dataforge-ai/
├── dataforge/                 # Main package
│   ├── __init__.py
│   ├── core/                  # Domain entities and interfaces
│   │   ├── __init__.py
│   │   ├── entities.py        # Dataset, AnalysisResult, etc.
│   │   ├── state.py           # GraphState model
│   │   └── interfaces.py      # Agent interfaces
│   ├── agents/                # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py            # Base agent class
│   │   ├── ingestion.py       # Data ingestion agent
│   │   ├── profiling.py       # Data profiling agent
│   │   ├── statistics.py      # Statistical analysis agent
│   │   ├── visualization.py   # Visualization agent
│   │   └── reporting.py       # Reporting agent
│   ├── graph/                 # LangGraph workflow
│   │   ├── __init__.py
│   │   ├── workflow.py        # Main graph definition
│   │   └── routing.py         # Conditional routing logic
│   ├── infrastructure/        # External dependencies
│   │   ├── __init__.py
│   │   ├── llm/               # LLM clients
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── openai.py
│   │   │   └── anthropic.py
│   │   ├── storage/           # File I/O and storage
│   │   │   ├── __init__.py
│   │   │   └── file_reader.py
│   │   └── viz/               # Visualization engine
│   │       ├── __init__.py
│   │       └── plotly_engine.py
│   ├── application/           # Use cases
│   │   ├── __init__.py
│   │   └── analyze_dataset.py
│   ├── presentation/          # CLI interface
│   │   ├── __init__.py
│   │   └── cli.py
│   └── shared/                # Utilities
│       ├── __init__.py
│       ├── config.py
│       ├── logging.py
│       ├── retry.py
│       └── constants.py
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── unit/                  # Unit tests
│   │   ├── test_entities.py
│   │   ├── test_agents.py
│   │   └── test_state.py
│   ├── integration/           # Integration tests
│   │   ├── test_workflow.py
│   │   └── test_llm_integration.py
│   └── e2e/                   # End-to-end tests
│       └── test_cli.py
├── docs/                      # Documentation
│   ├── architecture.md
│   ├── vision.md
│   ├── requirements.md
│   ├── tech_stack.md
│   ├── development_guide.md
│   ├── graph_design.md
│   ├── agents.md
│   └── roadmap.md
├── examples/                  # Example datasets and outputs
│   └── sample_data.csv
├── scripts/                   # Utility scripts
│   └── setup_dev_env.sh
├── .env.example               # Example environment variables
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Development Workflow

### 1. Create a Branch

```bash
# Start from main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation changes
- `test/` - Test additions/changes

### 2. Make Changes

Follow the coding standards in this guide.

### 3. Run Tests Locally

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=dataforge --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_agents.py

# Run specific test
poetry run pytest tests/unit/test_agents.py::test_ingestion_agent
```

### 4. Code Quality Checks

```bash
# Format code
poetry run black .
poetry run isort .

# Lint
poetry run flake8

# Type check
poetry run mypy

# Docstring check
poetry run pydocstyle dataforge
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat: add data profiling agent"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (formatting)
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Maintenance tasks

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title following commit format
- Description of changes
- Reference to related issues
- Screenshots if UI changes

---

## Coding Standards

### Python Style Guide

Follow **PEP 8** with these tools:
- **Black**: Auto-formatting
- **isort**: Import sorting
- **flake8**: Linting

### Type Hints

All public functions must have type hints:

```python
from typing import Optional, List
from dataforge.core.entities import Dataset

def analyze_dataset(
    dataset: Dataset,
    query: Optional[str] = None,
) -> AnalysisResult:
    """Analyze a dataset and return results.

    Args:
        dataset: The dataset to analyze.
        query: Optional user query for targeted analysis.

    Returns:
        AnalysisResult containing insights and visualizations.
    """
    ...
```

### Docstrings

Use **Google style** docstrings:

```python
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process and clean the input DataFrame.

    This function handles missing values, converts data types,
    and removes duplicates.

    Args:
        df: Input DataFrame with raw data.

    Returns:
        Cleaned DataFrame with consistent types and no missing values.

    Raises:
        ValueError: If DataFrame is empty or has no columns.

    Examples:
        >>> df = pd.DataFrame({'a': [1, 2, None]})
        >>> clean_df = process_data(df)
        >>> clean_df.isna().sum().sum()
        0
    """
    ...
```

### Error Handling

Use specific exceptions:

```python
# Good
try:
    data = pd.read_csv(file_path)
except FileNotFoundError:
    raise DataIngestionError(f"File not found: {file_path}")
except pd.errors.EmptyDataError:
    raise DataIngestionError(f"File is empty: {file_path}")
except Exception as e:
    raise DataIngestionError(f"Failed to read file: {e}")

# Bad
try:
    data = pd.read_csv(file_path)
except:
    raise Error("Something went wrong")
```

### Logging

Use structured logging:

```python
import structlog

log = structlog.get_logger()

def process_data(data: pd.DataFrame) -> pd.DataFrame:
    """Process data with logging."""
    log.info("Starting data processing", rows=len(data), columns=len(data.columns))

    try:
        result = data.dropna()
        log.info("Processed data", 
                 original_rows=len(data), 
                 result_rows=len(result),
                 dropped_rows=len(data) - len(result))
        return result
    except Exception as e:
        log.error("Data processing failed", error=str(e))
        raise
```

### Constants

Use UPPER_CASE for constants:

```python
# shared/constants.py

MAX_FILE_SIZE_MB = 100
MAX_ROWS = 1_000_000
MAX_COLUMNS = 1_000
SUPPORTED_FORMATS = [".csv", ".parquet"]
DEFAULT_TIMEOUT_SECONDS = 60
```

### Class Design

Follow SOLID principles:

```python
# Single Responsibility
class DataValidator:
    """Validates data structure and content."""
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        ...

class DataCleaner:
    """Cleans and preprocesses data."""
    
    def clean(self, data: pd.DataFrame) -> pd.DataFrame:
        ...

# Dependency Inversion
class AnalysisAgent(ABC):
    """Abstract base for analysis agents."""
    
    @abstractmethod
    def analyze(self, data: pd.DataFrame, llm_client: LLMClient) -> AnalysisResult:
        ...

class StatisticalAnalyzer(AnalysisAgent):
    """Concrete implementation using dependency injection."""
    
    def analyze(self, data: pd.DataFrame, llm_client: LLMClient) -> AnalysisResult:
        ...
```

---

## Testing

### Test Organization

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_entities.py
│   ├── test_agents.py
│   └── test_utils.py
├── integration/       # Test component interactions
│   ├── test_workflow.py
│   └── test_llm_integration.py
└── e2e/               # Full workflow tests
    └── test_cli.py
```

### Writing Tests

Use pytest with clear, descriptive names:

```python
import pytest
from dataforge.agents.profiling import DataProfilingAgent
from dataforge.core.state import GraphState
import pandas as pd


class TestDataProfilingAgent:
    """Test suite for DataProfilingAgent."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'age': [25, 30, 35, 40, 45],
            'salary': [50000.0, 60000.0, 70000.0, 80000.0, 90000.0],
        })
    
    @pytest.fixture
    def agent(self, mock_llm_client):
        """Create agent with mocked LLM client."""
        return DataProfilingAgent(llm_client=mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_analyze_numeric_columns(self, agent, sample_data):
        """Test that numeric columns are correctly identified."""
        state = GraphState(raw_data=sample_data)
        result = await agent.execute(state)
        
        assert 'age' in result.profile.numeric_columns
        assert 'salary' in result.profile.numeric_columns
        assert result.profile.numeric_columns['age'].mean == 35.0
    
    @pytest.mark.asyncio
    async def test_analyze_with_missing_values(self, agent):
        """Test handling of missing values."""
        data = pd.DataFrame({
            'a': [1, 2, None, 4],
            'b': ['x', None, 'z', 'w'],
        })
        state = GraphState(raw_data=data)
        result = await agent.execute(state)
        
        assert result.profile.missing_values['a'] == 1
        assert result.profile.missing_values['b'] == 1
```

### Mocking

Use pytest-mock for external dependencies:

```python
import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_llm_client():
    """Create mocked LLM client."""
    client = Mock()
    client.generate = AsyncMock(return_value="Mocked insight")
    return client


def test_with_mock(mock_llm_client):
    """Test using mocked dependency."""
    result = await mock_llm_client.generate("test prompt")
    assert result == "Mocked insight"
    mock_llm_client.generate.assert_called_once_with("test prompt")
```

### Coverage Targets

- **Business logic**: > 90% coverage
- **Agents**: > 85% coverage
- **Overall**: > 80% coverage

Run coverage report:

```bash
poetry run pytest --cov=dataforge --cov-report=html --cov-report=term
```

---

## Documentation

### Code Documentation

- All public classes have module-level docstrings
- All public functions have Google-style docstrings
- Complex logic has inline comments

### Module Docstrings

```python
"""Data profiling agent.

This module provides the DataProfilingAgent class which analyzes
the structure and content of datasets to generate comprehensive
profiles including data types, missing values, and distributions.

Example:
    >>> agent = DataProfilingAgent(llm_client=client)
    >>> state = GraphState(raw_data=dataframe)
    >>> result = await agent.execute(state)
    >>> print(result.profile.summary)
"""
```

### README.md

Keep README.md up-to-date with:
- Installation instructions
- Quick start guide
- Usage examples
- Configuration options
- Contributing guidelines

### API Documentation

Build API docs with Sphinx:

```bash
cd docs
make html
```

---

## Git Workflow

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch (if needed)
- `feature/*`: Feature development
- `fix/*`: Bug fixes
- `hotfix/*`: Emergency fixes to main

### Commit Guidelines

Use Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance

Examples:

```
feat(agents): add statistical analysis agent

Implement the StatisticalAnalysisAgent that computes
descriptive statistics, correlations, and identifies
significant relationships.

Closes #23
```

```
fix(ingestion): handle empty files

Previously, empty CSV files would cause a crash.
Now they return a proper error message.

Fixes #45
```

### Pull Request Guidelines

Before merging, PRs must:
1. Pass all CI checks
2. Have > 80% test coverage
3. Include tests for new features
4. Update relevant documentation
5. Be reviewed by at least one maintainer
6. Have a clear description of changes

### Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. Build and publish: `poetry publish`

---

## Common Tasks

### Adding a New Agent

1. Create agent file in `dataforge/agents/`
2. Inherit from `Agent` base class
3. Implement required methods
4. Add tests in `tests/unit/`
5. Update graph to include new agent
6. Update documentation

```python
# dataforge/agents/new_agent.py

from dataforge.agents.base import Agent
from dataforge.core.state import GraphState, AgentResult


class NewAgent(Agent):
    """Description of what this agent does."""
    
    async def execute(self, state: GraphState) -> AgentResult:
        """Execute the agent's logic."""
        # Implementation
        return AgentResult(...)
    
    def can_handle(self, state: GraphState) -> bool:
        """Check if this agent should run."""
        return state.raw_data is not None
    
    def get_dependencies(self) -> List[str]:
        """Return required state keys."""
        return ["raw_data"]
```

### Adding a New Visualization

1. Add method to `PlotlyEngine`
2. Handle new chart type
3. Add tests
4. Update documentation

```python
# infrastructure/viz/plotly_engine.py

def create_radar_chart(self, data: pd.DataFrame) -> go.Figure:
    """Create a radar chart for multi-dimensional comparison."""
    fig = go.Figure()
    # Implementation
    return fig
```

### Debugging Graph Workflows

Enable debug logging:

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger(__name__)
log.debug("Detailed debugging info", data=state)
```

### Running with Sample Data

```bash
# Download sample dataset
curl -o examples/sample.csv https://example.com/data.csv

# Run analysis
poetry run dataforge analyze examples/sample.csv
```

---

## Troubleshooting

### Common Issues

**Issue**: Poetry install fails
```bash
# Solution: Update Poetry and clear cache
poetry self update
poetry cache clear --all pypi
poetry install
```

**Issue**: Tests fail with import errors
```bash
# Solution: Install in development mode
poetry install --with dev
poetry shell
```

**Issue**: Type checking fails
```bash
# Solution: Install mypy plugins
poetry run pip install mypy-pytest
poetry run mypy
```

**Issue**: LLM API rate limits
```bash
# Solution: Add delay between requests
export OPENAI_REQUEST_DELAY=1
```

---

## Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Create GitHub issue with bug template
- **Discussions**: Use GitHub Discussions for questions
- **Code Review**: Request review on pull requests

---

## Code Review Checklist

When reviewing code, check:
- [ ] Follows coding standards
- [ ] Has appropriate tests
- [ ] Includes documentation
- [ ] No security vulnerabilities
- [ ] Error handling is complete
- [ ] Logging is appropriate
- [ ] Performance is acceptable
- [ ] Types are correct

---

## Conclusion

Following this guide ensures consistent, high-quality contributions to DataForge AI. When in doubt, prioritize simplicity and clarity over cleverness.

**Remember**: Production quality code is readable, testable, and maintainable.

**Document Version**: 1.0
**Last Updated**: 2024