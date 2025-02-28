# Conditional Method


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

The `@conditional_method` decorator allows you to define method implementations that are conditionally activated based on runtime conditions.

### Basic Example

```python
from conditional_method import conditional_method

class FileProcessor:
    @conditional_method(condition=lambda: True)
    def process_file(self, file_path):
        """This implementation will be used because the condition is True."""
        print(f"Processing file: {file_path}")
        
    @conditional_method(condition=lambda: False)
    def process_file(self, file_path):
        """This implementation will not be used because the condition is False."""
        print(f"Alternative processing: {file_path}")
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
