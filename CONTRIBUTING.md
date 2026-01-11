# Contributing to AI Debate Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

---

## 🚀 Quick Start for Contributors

```bash
# 1. Fork and clone
git clone https://github.com/your-username/AI-debate.git
cd AI-debate

# 2. Set up environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 3. Configure .env (see .env.example)
cp .env.example .env
# Add your OPENROUTER_API_KEY

# 4. Run tests
pytest tests/ -v

# 5. Create a branch
git checkout -b feature/your-feature-name
```

---

## 📝 Types of Contributions

### 1. Bug Reports
- Check [CHANGELOG.md](CHANGELOG.md) to see if already fixed
- Open an issue with:
  - Clear description
  - Steps to reproduce
  - Expected vs actual behavior
  - Debate ID if applicable
  - Raw logs (`raw_model_calls.jsonl`) if relevant

### 2. Feature Requests
- Check [ROADMAP.md](ROADMAP.md) to see if planned
- Open an issue describing:
  - Use case
  - Proposed solution
  - Alternative approaches considered

### 3. Code Contributions
- See sections below for guidelines
- Ensure tests pass
- Update documentation
- Follow code style

### 4. Documentation
- Fix typos, improve clarity
- Add examples
- Update for new features
- Keep [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) up to date

---

## 🏗️ Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for classes and functions
- Keep functions focused and testable

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_moderator.py::test_phase_0 -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Requirements:**
- All new features must have tests
- Bug fixes should include regression tests
- Maintain >80% code coverage
- Tests should be independent and repeatable

### Commits
- Use clear, descriptive commit messages
- Reference issues where applicable
- One logical change per commit

**Format:**
```
[Component] Short description (50 chars max)

Longer explanation if needed. Wrap at 72 characters.

Fixes #123
```

**Examples:**
```
[Agents] Add support for custom voter personas

Allow users to define custom voter archetypes beyond the
default 10 persona types.

Fixes #45
```

---

## 🔧 Architecture Guidelines

### Agent Development
See [AGENTS_COMPLETE.md](AGENTS_COMPLETE.md) for agent architecture.

**When adding/modifying agents:**
1. Inherit from `Agent` base class
2. Implement `execute_turn()` method
3. Use `create_response()` for consistent responses
4. Log actions via debate logger
5. Handle errors gracefully
6. Add type hints
7. Write comprehensive tests

### File Manager
All file I/O must go through `FileManager`:
- Never write directly to JSON files
- Use appropriate write methods (`write_by_agent`, `write_by_moderator`)
- Validate data before writing
- Handle race conditions

### Cost Tracking
When calling LLMs:
1. Estimate cost before call
2. Check budget
3. Track actual cost after call
4. Update `CostTracker`

### Logging
Two logging systems:
1. **Debate Logger** (`debate_log.jsonl`) - High-level events
2. **Raw Data Logger** (`raw_model_calls.jsonl`) - All LLM I/O

Use appropriate logger for context.

---

## 🧪 Testing Guidelines

### Test Structure
```python
# tests/test_component.py
import pytest
from src.component import Component

def test_basic_functionality():
    """Test description."""
    # Arrange
    component = Component()
    
    # Act
    result = component.method()
    
    # Assert
    assert result == expected
```

### Fixtures
Use `pytest` fixtures for common setup:
```python
@pytest.fixture
def config():
    """Provide test configuration."""
    return Config(...)
```

### Mocking LLM Calls
Always mock external API calls in tests:
```python
@pytest.mark.asyncio
async def test_agent_turn(monkeypatch):
    """Test agent turn without API calls."""
    async def mock_generate(*args, **kwargs):
        return "Mock response"
    
    monkeypatch.setattr("src.agents.agent.generate", mock_generate)
    # ... test code
```

---

## 📚 Documentation Guidelines

### Code Documentation
```python
def function_name(param1: Type, param2: Type) -> ReturnType:
    """
    Brief description (one line).
    
    Longer description if needed. Explain the purpose,
    behavior, and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception occurs
    """
```

### Markdown Documentation
- Use clear headings
- Include code examples
- Add links to related docs
- Keep lines under 80 characters
- Use tables for comparisons

### README Updates
When adding features:
1. Update [README.md](README.md) if user-facing
2. Update [CHANGELOG.md](CHANGELOG.md)
3. Update [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
4. Create detailed docs if complex feature

---

## 🔍 Pull Request Process

1. **Before Starting**
   - Check existing issues/PRs
   - Discuss major changes in an issue first

2. **Development**
   - Create feature branch from `main`
   - Make your changes
   - Add/update tests
   - Update documentation

3. **Before Submitting**
   - Run full test suite: `pytest tests/ -v`
   - Check code style: `flake8 src/`
   - Update [CHANGELOG.md](CHANGELOG.md)
   - Ensure all tests pass

4. **Submit PR**
   - Clear title describing change
   - Description with:
     - What changed
     - Why (link to issue)
     - Testing performed
     - Screenshots if UI change
   - Link related issues

5. **Review Process**
   - Respond to feedback
   - Make requested changes
   - Keep PR up to date with main

6. **Merge**
   - Squash commits if many small changes
   - Use clear merge commit message

---

## 🐛 Bug Fix Process

1. **Reproduce** - Confirm bug exists
2. **Identify** - Find root cause
3. **Test** - Write failing test
4. **Fix** - Implement fix
5. **Verify** - Test passes
6. **Document** - Update CHANGELOG
7. **Submit** - Create PR

---

## 🚨 Security Issues

**Do NOT open public issues for security vulnerabilities.**

Instead:
1. Email security contact (add your email here)
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix if any

---

## 📊 Project Structure

```
src/
├── agents/          # Agent implementations
│   ├── base.py     # Agent base class
│   ├── debator.py  # Debator agent
│   ├── judge.py    # Judge agent
│   ├── crowd.py    # Crowd agent
│   └── factchecker.py
├── clients/         # API clients
│   ├── openrouter_client.py
│   └── gemini_client.py
├── utils/           # Utilities
│   ├── file_manager.py
│   ├── debate_logger.py
│   ├── raw_data_logger.py
│   └── cost_tracker.py
├── config.py        # Configuration
└── moderator.py     # Orchestration

tests/               # Test suite
├── test_agents.py
├── test_moderator.py
└── test_utils.py
```

---

## 🎯 Areas for Contribution

### High Priority
- [ ] Web interface
- [ ] Debate comparison tools
- [ ] Performance optimization
- [ ] More comprehensive tests

### Medium Priority
- [ ] Custom voter personas
- [ ] Argument graph visualization
- [ ] Export to different formats
- [ ] Internationalization

### Low Priority
- [ ] UI themes
- [ ] Voice output
- [ ] Debate templates

See [ROADMAP.md](ROADMAP.md) for complete plans.

---

## 💬 Communication

- **Issues**: For bugs, features, questions
- **Pull Requests**: For code contributions
- **Discussions**: For general questions (if enabled)

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intent
- Keep discussions on-topic

---

## ❓ Questions?

- Check [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
- Search existing issues
- Ask in a new issue if not found

---

Thank you for contributing to the AI Debate Platform! 🎉
