# Contributing to Face Recognition Attendance System

First off, thank you for considering contributing to this project! 🎉

## Code of Conduct

This project and everyone participating in it is governed by respect, kindness, and professionalism. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include screenshots if possible**
- **Include your environment details** (OS, Python version, browser, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List any examples of how it would be used**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. Ensure your code follows the existing style
4. Update the documentation
5. Make sure your code lints
6. Issue that pull request!

## Development Setup

1. Clone your fork:
```bash
git clone https://github.com/your-username/face-recognition-system.git
cd face-recognition-system
```

2. Create a branch:
```bash
git checkout -b feature/my-new-feature
```

3. Set up the development environment:
```bash
conda create -n face_rec_dev python=3.10
conda activate face_rec_dev
pip install -r requirements.txt
```

4. Make your changes and test thoroughly

5. Commit your changes:
```bash
git add .
git commit -m "Add some feature"
```

6. Push to your fork:
```bash
git push origin feature/my-new-feature
```

7. Open a Pull Request

## Style Guidelines

### Python Style Guide

- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and small
- Add comments for complex logic

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Example:
```
Add voice pitch control feature

- Add slider for pitch adjustment in settings
- Update speak() function to use pitch parameter
- Add tests for voice configuration
Closes #123
```

## Testing

Before submitting a pull request, ensure:

- All existing tests pass
- New features have appropriate tests
- The application runs without errors
- Face recognition still works correctly
- Voice announcements function properly

## Documentation

- Update README.md if needed
- Update relevant documentation in `/docs`
- Add inline comments for complex code
- Update API documentation if endpoints change

## Questions?

Feel free to open an issue with the label "question" or reach out to the maintainers.

## Recognition

Contributors will be acknowledged in the README.md file.

Thank you for contributing! 🙏
