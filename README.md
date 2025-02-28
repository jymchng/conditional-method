<div align="center">
<h1>Conditional Method</h1>
  <a href="https://pypi.org/project/conditional-method/">
    <img src="https://img.shields.io/pypi/v/conditional-method.svg" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/conditional-method/">
    <img src="https://img.shields.io/pypi/pyversions/conditional-method.svg" alt="Python Versions">
  </a>
  <a href="https://github.com/jymchng/conditional-method/blob/main/LICENSE">
    <img src="https://img.shields.io/pypi/l/conditional-method.svg" alt="License">
  </a>
  <a href="https://pepy.tech/project/conditional-method">
    <img src="https://static.pepy.tech/badge/conditional-method" alt="Downloads">
  </a>
  <a href="https://github.com/jymchng/conditional-method/stargazers">
    <img src="https://img.shields.io/github/stars/jymchng/conditional-method.svg" alt="GitHub stars">
  </a>
  <a href="https://github.com/jymchng/conditional-method/network">
    <img src="https://img.shields.io/github/forks/jymchng/conditional-method.svg" alt="GitHub forks">
  </a>
  <a href="https://github.com/jymchng/conditional-method/issues">
    <img src="https://img.shields.io/github/issues/jymchng/conditional-method.svg" alt="GitHub issues">
  </a>
  <a href="https://codecov.io/gh/jymchng/conditional-method">
    <img src="https://codecov.io/gh/jymchng/conditional-method/branch/main/graph/badge.svg" alt="codecov">
  </a>
  <a href="https://github.com/jymchng/conditional-method/actions">
    <img src="https://github.com/jymchng/conditional-method/workflows/Python%20Tests/badge.svg" alt="Build Status">
  </a>
  <a href="https://github.com/psf/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
  </a>
  <a href="https://pycqa.github.io/isort/">
    <img src="https://img.shields.io/badge/%20imports-isort-%231674b1" alt="Imports: isort">
  </a>
</div>

A powerful Python library that enables conditional method implementation based on runtime, initial conditions, at program startup or latest at class building time, allowing you to define different method implementations that are selected at when your classes are being built according to specific conditions.

## 🚀 Features

- ✅ **Conditional Method Selection**: Define methods that are only active when specific conditions are met
- 🔄 **Runtime Conditional Logic**: Choose method implementations based on runtime conditions
- 🧩 **Clean Class Design**: Keep your class definitions clean by separating conditional logic from implementation
- 📦 **Type-Safe**: Fully compatible with type checkers and includes type annotations
- 🛡️ **Zero Dependencies**: No external dependencies required
- 🔍 **Debuggable**: Optional debug logging for troubleshooting

## 📋 Installation (Coming Soon!)

```bash
pip install conditional-method
```

## 🔧 Usage

A decorator `@conditional_method` that selects a method implementation (among those that are identically named) for a class during class build time, leaving only the selected method in its attributes set when the class is built, i.e. 'well-formed'.

### Basic Example

```python
from conditional_method import conditional_method

import os

ENVIRONMENT_KEY = "ENVIRONMENT_KEY"
os.environ[ENVIRONMENT_KEY] = "production"

ENVIRONMENT = os.environ[ENVIRONMENT_KEY]


class Worker:
    __slots__ = ()

    @conditional_method(condition=ENVIRONMENT == "production")
    def work(self, *args, **kwargs):
        print("Working in production")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "production"

    @conditional_method(condition=ENVIRONMENT == "development")
    def work(self, *args, **kwargs):
        print("Working in development")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "development"

    @conditional_method(condition=ENVIRONMENT == "staging")
    def work(self, *args, **kwargs):
        print("Working in staging")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        return "staging"


worker = Worker()

print(f"ENVIRONMENT: {ENVIRONMENT}")  # ENVIRONMENT: production

print(f"Worker.__dict__: {Worker.__dict__}")
# only one of the `work` methods will be bound to the Worker class
# Worker.__dict__: {
#     '__module__': '__main__',
#     '__slots__': (),
#     'work': <function Worker.work at 0x7f6151683670>,
#     '__doc__': None
# }

print(worker.work(1, 2, 3, a=4, b=5))

# Working in production
# Args: (1, 2, 3)
# Kwargs: {'a': 4, 'b': 5}
# production (return value of the selected method)

```

### Dynamic Conditions

```python
import os
from conditional_method import conditional_method

class DatabaseConnector:
    @conditional_method(condition=lambda: os.environ.get("ENV") == "production")
    def connect(self, config):
        """Used in production environment"""
        print("Connecting to production database...")
        # Production-specific connection logic
        
    @conditional_method(condition=lambda: os.environ.get("ENV") == "development")
    def connect(self, config):
        """Used in development environment"""
        print("Connecting to development database...")
        # Development-specific connection logic
        
    @conditional_method(condition=lambda: os.environ.get("ENV") not in ["production", "development"])
    def connect(self, config):
        """Used in any other environment"""
        print("Connecting to local/test database...")
        # Default connection logic
```

### Feature Flags

```python
from conditional_method import conditional_method

# Feature flag system
FEATURES = {
    "new_algorithm": True,
    "legacy_mode": False
}

class DataProcessor:
    @conditional_method(condition=lambda: FEATURES["new_algorithm"])
    def process_data(self, data):
        """New algorithm implementation"""
        print("Processing with new algorithm...")
        # New algorithm implementation
        
    @conditional_method(condition=lambda: FEATURES["legacy_mode"])
    def process_data(self, data):
        """Legacy implementation"""
        print("Processing with legacy algorithm...")
        # Legacy algorithm implementation
        
    @conditional_method(condition=lambda: not FEATURES["new_algorithm"] and not FEATURES["legacy_mode"])
    def process_data(self, data):
        """Default implementation"""
        print("Processing with standard algorithm...")
        # Standard algorithm implementation
```

### Platform-Specific Code

```python
import sys
from conditional_method import conditional_method

class FileSystem:
    @conditional_method(condition=lambda: sys.platform.startswith("win"))
    def get_temp_directory(self):
        """Windows implementation"""
        return "C:\\Temp"
        
    @conditional_method(condition=lambda: sys.platform.startswith("linux"))
    def get_temp_directory(self):
        """Linux implementation"""
        return "/tmp"
        
    @conditional_method(condition=lambda: sys.platform == "darwin")
    def get_temp_directory(self):
        """macOS implementation"""
        return "/private/tmp"
```

## 🔍 Debugging

You can enable debug logging by setting the environment variable `__conditional_method_debug__` to any value other than "false":

```bash
# Linux/macOS
export __conditional_method_debug__=true

# Windows
set __conditional_method_debug__=true
```

## 📝 Technical Details

The `conditional_method` decorator uses Python's descriptor protocol to manage method selection at runtime. When a class is defined:

1. Each method decorated with `@conditional_method` is evaluated
2. Only one implementation (where condition is `True`) is bound to the class
3. If no conditions are `True`, an error is raised
4. If multiple conditions are `True`, the first one encountered is used

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Thanks to all contributors who have helped shape this project
- Inspired by the need for cleaner conditional logic in Python applications
