# 📦 Installation Guide

This guide covers all the ways to install and set up codn for different use cases.

## 🚀 Quick Install (Recommended)

### Option 1: Using uv (Fastest)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install codn
uv tool install codn
```

### Option 2: Using pip (Traditional)

```bash
pip install codn
```

### Option 3: One-click Setup

```bash
# Download and run our setup script
curl -sSL https://raw.githubusercontent.com/dweb-lab/codn/main/quickstart.sh | bash
```

## 📋 Detailed Installation Options

### For Regular Users

#### uv (Recommended)
- **Pros**: Faster installs, better dependency resolution, automatic virtual environments
- **Cons**: Requires uv installation first

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install codn globally
uv tool install codn

# Verify installation
codn --help
```

#### pip (Universal)
- **Pros**: Available everywhere, no additional setup
- **Cons**: Slower, potential dependency conflicts

```bash
# In a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install codn

# Or globally (not recommended)
pip install codn

# Verify installation
codn --help
```

### For Developers

#### Development Setup with uv

```bash
# Clone the repository
git clone https://github.com/dweb-lab/codn.git
cd codn

# Install in development mode
uv sync --group dev

# Run codn
uv run codn --help

# Run tests
uv run pytest
```

#### Development Setup with pip

```bash
# Clone the repository
git clone https://github.com/dweb-lab/codn.git
cd codn

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .[dev]

# Run codn
codn --help

# Run tests
pytest
```

## 🔧 Environment Management

### Virtual Environments

#### Why Use Virtual Environments?
- Isolate project dependencies
- Avoid conflicts between packages
- Easy to reproduce environments
- Clean uninstall (just delete the folder)

#### With uv (Automatic)
```bash
# uv automatically manages virtual environments
uv tool install codn  # Creates isolated environment for codn
```

#### With pip (Manual)
```bash
# Create virtual environment
python -m venv codn-env

# Activate it
source codn-env/bin/activate  # Linux/Mac
# or
codn-env\Scripts\activate     # Windows

# Install codn
pip install codn

# When done, deactivate
deactivate
```

### System-wide Installation

#### With uv
```bash
uv tool install codn
# Installs in isolated environment but available globally
```

#### With pip
```bash
pip install codn
# Installs to system Python (may cause conflicts)
```

## 🐍 Python Version Support

- **Required**: Python 3.8 or higher
- **Recommended**: Python 3.10+
- **Tested**: Python 3.8, 3.9, 3.10, 3.11, 3.12

### Check Your Python Version
```bash
python --version
# or
python3 --version
```

## 🔍 Installation Verification

### Basic Check
```bash
codn --version
codn --help
```

### Full Test
```bash
# Create a test directory
mkdir test-codn
cd test-codn

# Create a simple Python file
echo "import os, sys\ndef main():\n    print('hello')" > test.py

# Run codn analysis
codn                    # Project analysis
codn unused             # Check imports
codn refs main          # Find references
codn funcs             # List functions
```

## 🛠️ Common Installation Issues

### uv Not Found
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart your terminal or source your shell config
source ~/.bashrc  # or ~/.zshrc
```

### Permission Errors with pip
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install codn

# Or install with --user flag
pip install --user codn
```

### Import Errors
```bash
# Check if codn is properly installed
python -c "import codn; print(codn.__version__)"

# If using virtual environment, make sure it's activated
which python
which codn
```

### Command Not Found
```bash
# Check if codn is in PATH
which codn

# For pip --user installs, add to PATH
export PATH="$HOME/.local/bin:$PATH"

# For uv tool installs, PATH is usually handled automatically
```

## 📊 Installation Methods Comparison

| Method | Speed | Isolation | Global Access | Dev Mode |
|--------|-------|-----------|---------------|----------|
| `uv tool install` | ⚡⚡⚡ | ✅ | ✅ | ❌ |
| `pip install` | ⚡ | ❌ | ✅ | ❌ |
| `pip + venv` | ⚡ | ✅ | ❌ | ❌ |
| `uv sync` (dev) | ⚡⚡⚡ | ✅ | ❌ | ✅ |
| `pip -e .` (dev) | ⚡ | ❌ | ✅ | ✅ |

## 🚀 Quick Start After Installation

### Most Common Commands
```bash
codn                    # Analyze current project
codn unused             # Find unused imports  
codn refs <function>    # Find function references
codn funcs              # List all functions
```

### Traditional Commands (Also Available)
```bash
codn analyze project
codn analyze unused-imports
codn analyze find-refs <function>
codn analyze functions
```

## 🤝 Getting Help

### Installation Helper
```bash
# Run our installation diagnostic
python -c "
import subprocess, sys
subprocess.run([sys.executable, '-c', '''
try:
    import codn
    print(f\"✅ codn {codn.__version__} installed successfully\")
except ImportError:
    print(\"❌ codn not found\")
'''])
"
```

### Manual Setup Check
```bash
# Check if in development directory
if [ -f "pyproject.toml" ] && grep -q 'name = "codn"' pyproject.toml; then
    echo "📚 Development setup detected"
    echo "Use: uv sync && uv run codn"
else
    echo "👤 User installation"
    echo "Use: uv tool install codn"
fi
```

### Support Resources
- 📖 [Documentation](https://github.com/dweb-lab/codn/tree/main/docs)
- 🐛 [Issue Tracker](https://github.com/dweb-lab/codn/issues)
- 💬 [Discussions](https://github.com/dweb-lab/codn/discussions)

## 📝 Next Steps

After installation, check out:
- [CLI Guide](cli-guide.md) - Learn all the commands
- [Examples](examples/) - See codn in action
- [API Documentation](api/) - Use codn in your Python code

---

**Need help?** Run our installation helper:
```bash
curl -sSL https://raw.githubusercontent.com/dweb-lab/codn/main/install.py | python3
```
