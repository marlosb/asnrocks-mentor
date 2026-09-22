# Project Instructions

## Project Overview

This project is a web application hosted on Azure Functions.

## Technology Stack

- Use Python for the backend.
- Use plain HTML, CSS, and JavaScript for the frontend.
- Keep the frontend framework-free unless a library is strictly necessary.
- Design backend code and deployment configuration for Azure Functions.

## Dependencies

- Minimize third-party libraries to reduce dependencies, deployment size, and maintenance overhead.
- Prefer the Python standard library and native browser APIs when they provide a clear, maintainable solution.
- Add a third-party package only when it provides meaningful value that would be impractical to implement with built-in functionality.

## Python Package Installation

External Python package feeds are unavailable on the corporate network. Install packages from the internal package feed:

```powershell
python -m pip install --index-url https://packagefeedproxy.microsoft.io/pypi/simple <package-name>
```

Do not install Python packages directly from external package indexes such as PyPI.
