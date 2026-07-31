# Contributing to DataForge AI

We welcome contributions! Thank you for considering contributing to DataForge AI.

## Development Setup

```bash
git clone https://github.com/yourusername/dataforge-ai.git
cd dataforge-ai
pip install poetry
poetry install
poetry install --with dev
```

## Running Tests

```bash
poetry run pytest
poetry run pytest tests/unit/
poetry run pytest tests/integration/
```

## Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints for all public interfaces
- Maximum line length: 100 characters
- Run `black` and `isort` before committing

### Testing
- Unit tests for agent logic
- Integration tests for workflows
- Aim for >80% coverage
- All tests must pass before merging

### Documentation
- Update docstrings when changing behavior
- Update CHANGELOG.md
- Keep README.md up to date

### Agent Development

To add a new agent:

1. Create class inheriting from `Agent`
2. Implement `async def execute(self, state: GraphState) -> AgentResult`
3. Add agent to `dataforge/agents/__init__.py`
4. Add to workflow graph in `dataforge/graph/workflow.py`
5. Add tests in `tests/unit/test_<agent>.py`
6. Update documentation

### Pull Request Process

1. Fork the repository
2. Create a descriptive branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests and documentation
5. Run tests: `poetry run pytest`
6. Commit with clear commit message
7. Push to your fork
8. Create pull request with description

### Issues

When reporting issues:
- Provide a clear description
- Include steps to reproduce
- Add environment details (Python version, OS, errors)
- Add relevant logs

## Code Review Process

All submissions go through code review:

1. Architecture review - Is this the right approach?
2. Code review - Is the code clean and well-documented?
3. Test review - Are tests comprehensive?

## License

By contributing, you agree to license your contributions under the MIT License.