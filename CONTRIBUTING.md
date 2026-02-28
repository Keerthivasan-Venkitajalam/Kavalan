# Contributing to Kavalan

Thank you for your interest in contributing to Kavalan! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, browser, versions)
- Screenshots or logs if applicable

### Suggesting Features

Feature requests are welcome! Please include:
- Clear description of the feature
- Use case and benefits
- Potential implementation approach
- Any relevant examples or mockups

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Run the test suite** to ensure everything passes
6. **Submit a pull request** with a clear description

## Development Setup

### Backend (Python)

```bash
cd packages/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Frontend (TypeScript)

```bash
cd packages/extension
npm install
```

## Coding Standards

### Python

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Write docstrings for public APIs (Google style)
- Maximum line length: 100 characters
- Use `black` for formatting: `black app/ tests/`
- Use `ruff` for linting: `ruff check app/ tests/`
- Use `mypy` for type checking: `mypy app/`

### TypeScript

- Follow ESLint configuration
- Use TypeScript strict mode
- Write JSDoc comments for exported functions
- Maximum line length: 100 characters
- Use Prettier for formatting: `npm run format`
- Run linter: `npm run lint`

## Testing

### Backend Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_audio_transcriber.py -v

# Run property-based tests
pytest tests/ -k "property" -v
```

### Frontend Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test
npm test -- platform-detector.test.ts
```

## Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(audio): add speaker diarization support

Implement speaker change detection using pyannote.audio
for multi-speaker transcription accuracy.

Closes #123
```

```
fix(extension): resolve WebRTC stream capture on Firefox

Firefox requires different MediaStream handling compared to Chrome.
Updated platform detector to handle Firefox-specific APIs.

Fixes #456
```

## Documentation

- Update README.md for user-facing changes
- Update API documentation in docstrings
- Add inline comments for complex logic
- Update architecture diagrams if needed
- Create migration guides for breaking changes

## Review Process

1. **Automated checks**: CI pipeline runs tests and linting
2. **Code review**: At least one maintainer reviews the PR
3. **Testing**: Reviewer tests the changes locally
4. **Approval**: PR is approved and merged

## Areas for Contribution

### High Priority

- **Deepfake detection improvements**: Enhance liveness detection accuracy
- **Performance optimization**: Reduce inference latency
- **Language support**: Add more Indian languages
- **Mobile support**: iOS/Android app development

### Good First Issues

- **Documentation**: Improve setup guides and API docs
- **Testing**: Add more test coverage
- **UI/UX**: Enhance accessibility features
- **Localization**: Translate UI to more languages

### Advanced

- **Federated learning**: Privacy-preserving model updates
- **Edge deployment**: Optimize for edge devices
- **Model quantization**: Reduce model size
- **Distributed tracing**: Enhance observability

## Questions?

- Open a GitHub issue for technical questions
- Email the team at keerthivasan.sv@example.com
- Join our community discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Kavalan! Together, we can protect more people from Digital Arrest scams.
