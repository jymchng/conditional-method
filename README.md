<div align="center">
<h1>Conditional Method</h1>
<h2>[Repository is a Work In Progress]</h2>
<div><em>The code is very usable though...</em></div>
  ____


  <a href="https://pypi.org/project/conditional-method/">
    <img src="https://img.shields.io/pypi/v/conditional-method.svg" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/conditional-method/">
    <img src="https://img.shields.io/pypi/pyversions/conditional-method.svg" alt="Python Versions">
  </a>
  <a href="https://github.com/jymchng/conditional-method/blob/main/LICENSE">
    <img src="https://img.shields.io/pypi/l/conditional-method.svg" alt="License">
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
</div>
<br>
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

## 🔧 Usage of `@conditional_method` decorator (aliases: `@if_`, `@cfg`, `@cm`)

A decorator `@conditional_method` (aliases: `@if_`, `@cfg`, `@cm`) that selects a method implementation (among those that are identically named) for a class during class build time, leaving only the selected method in its attributes set when the class is built, i.e. 'well-formed'.

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

### Desugaring

```python
import os
from conditional_method import conditional_method

class DatabaseConnector:
    @conditional_method(condition=lambda f: os.environ.get("ENV") == "production")
    def connect(self, config):
        """Used in production environment"""
        print("Connecting to production database...")
        # Production-specific connection logic
        
    @conditional_method(condition=lambda f: os.environ.get("ENV") == "development")
    def connect(self, config):
        """Used in development environment"""
        print("Connecting to development database...")
        # Development-specific connection logic
        
    @conditional_method(condition=lambda f: os.environ.get("ENV") not in ["production", "development"])
    def connect(self, config):
        """Used in any other environment"""
        print("Connecting to local/test database...")
        # Default connection logic
```

Basically desugars to:

```python
import os
from conditional_method import conditional_method

class DatabaseConnector:
    if os.environ.get("ENV") == "production":
        def connect(self, config):
            """Used in production environment"""
            print("Connecting to production database...")
            # Production-specific connection logic
    
    elif os.environ.get("ENV") == "development":
        def connect(self, config):
            """Used in development environment"""
            print("Connecting to development database...")
            # Development-specific connection logic
    
    else:
        def connect(self, config):
            """Used in any other environment"""
            print("Connecting to local/test database...")
            # Default connection logic
```

### It can be applied to global functions

```python
import os
from conditional_method import conditional_method

@conditional_method(condition=os.environ.get("ENV") == "production")
def connect_to_db():
    # Production implementation
    print("Connecting to production database...")

@conditional_method(condition=os.environ.get("ENV") == "development")
def connect_to_db():
    # Development implementation
    print("Connecting to development database...")
```

### Can also be applied to classes

```python
import os
from conditional_method import conditional_method

# Set environment for demonstration
os.environ["ENV"] = "production"

@conditional_method(condition=os.environ.get("ENV") == "production")
class DatabaseConnector:
    """Production database connector with advanced security features"""
    
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        print("Initializing PRODUCTION database connector")
        
    def connect(self):
        print(f"Connecting to PRODUCTION database at {self.host}:{self.port}")
        print("Using enhanced security protocols")
        # Production-specific connection logic

@conditional_method(condition=os.environ.get("ENV") == "development")
class DatabaseConnector:
    """Development database connector with debugging capabilities"""
    
    def __init__(self, host="localhost", port=5432, user="dev", password="dev"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        print("Initializing DEVELOPMENT database connector")
        
    def connect(self):
        print(f"Connecting to DEVELOPMENT database at {self.host}:{self.port}")
        print("Debug mode enabled")
        # Development-specific connection logic with debug features

# Usage
if __name__ == "__main__":
    # Since ENV=production, this will use the production version
    db = DatabaseConnector("prod-db.example.com", 5432, "app_user", "secure_pwd")
    db.connect()
    
    # If we changed ENV to development before importing:
    # db = DatabaseConnector()  # Default parameters would work
    # db.connect()  # Would show debugging output
```

Note!! But maybe it is easier to place `@conditional_method` decorator on the `def __init__(...)` constructor instead.


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
4. If multiple conditions are `True`, the **LAST** one encountered that is true is used
5. Uses function qualnames to track different implementations of the same method
6. Handles edge cases around method binding, descriptors, and garbage collection
7. Clears the cache strategically to prevent memory leaks
8. Supports both boolean conditions and callable conditions that evaluate at runtime

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
