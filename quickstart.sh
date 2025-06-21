#!/bin/bash

# Codn Quick Start Script
# Automatically detects and sets up the best installation method

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print colored output
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo
    print_colored "$CYAN" "🔍 Codn Quick Start"
    print_colored "$CYAN" "==================="
    echo
}

print_success() {
    print_colored "$GREEN" "✅ $1"
}

print_warning() {
    print_colored "$YELLOW" "⚠️  $1"
}

print_error() {
    print_colored "$RED" "❌ $1"
}

print_info() {
    print_colored "$BLUE" "ℹ️  $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if we're in a virtual environment
in_virtual_env() {
    [[ -n "${VIRTUAL_ENV:-}" ]] || [[ -n "${CONDA_DEFAULT_ENV:-}" ]]
}

# Check if this is a development setup
is_dev_setup() {
    [[ -f "pyproject.toml" ]] && grep -q 'name = "codn"' pyproject.toml 2>/dev/null
}

# Install uv
install_uv() {
    print_info "Installing uv..."
    if command_exists curl; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Source the shell to make uv available
        export PATH="$HOME/.cargo/bin:$PATH"
        if command_exists uv; then
            print_success "uv installed successfully!"
            return 0
        fi
    fi
    return 1
}

# Main installation function
main() {
    print_header

    # Detect environment
    local is_dev=$(is_dev_setup && echo "yes" || echo "no")
    local in_venv=$(in_virtual_env && echo "yes" || echo "no")
    local has_uv=$(command_exists uv && echo "yes" || echo "no")
    local has_pip=$(command_exists pip && echo "yes" || echo "no")

    print_info "Environment Detection:"
    echo "   Development setup: $is_dev"
    echo "   Virtual environment: $in_venv"
    echo "   uv available: $has_uv"
    echo "   pip available: $has_pip"
    echo

    # Development setup
    if [[ "$is_dev" == "yes" ]]; then
        print_colored "$YELLOW" "📚 Development Setup Detected"
        echo

        if [[ "$has_uv" == "yes" ]]; then
            print_success "Using uv for development setup..."
            if uv sync; then
                print_success "Development environment ready!"
                echo
                print_info "Try these commands:"
                echo "   uv run codn --help"
                echo "   uv run codn"
                echo "   make demo"
                return 0
            else
                print_error "uv sync failed"
            fi
        elif [[ "$has_pip" == "yes" ]]; then
            print_warning "Using pip for development setup..."
            if pip install -e .; then
                print_success "Development environment ready!"
                echo
                print_info "Try these commands:"
                echo "   codn --help"
                echo "   codn"
                return 0
            else
                print_error "pip install failed"
            fi
        else
            print_error "No package manager available!"
            return 1
        fi
    fi

    # User installation
    print_colored "$BLUE" "👤 User Installation"
    echo

    # Try uv first
    if [[ "$has_uv" == "yes" ]]; then
        print_success "Using uv (recommended)..."
        if uv tool install codn; then
            print_success "codn installed successfully with uv!"
            echo
            print_info "Try these commands:"
            echo "   codn --help"
            echo "   codn"
            echo "   codn unused"
            return 0
        else
            print_warning "uv tool install failed, trying pip..."
        fi
    else
        print_info "uv not found. Checking if we should install it..."
        echo
        read -p "Would you like to install uv for faster package management? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            if install_uv; then
                if uv tool install codn; then
                    print_success "codn installed successfully with uv!"
                    echo
                    print_info "Try these commands:"
                    echo "   codn --help"
                    echo "   codn"
                    return 0
                fi
            fi
            print_warning "uv installation failed, falling back to pip..."
        fi
    fi

    # Fallback to pip
    if [[ "$has_pip" == "yes" ]]; then
        print_info "Using pip..."

        # Check if in virtual environment
        if [[ "$in_venv" == "no" ]]; then
            print_warning "Not in a virtual environment!"
            echo
            read -p "Create a virtual environment? [Y/n] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                python3 -m venv codn-env
                print_success "Virtual environment created: codn-env"
                print_info "Activate it with: source codn-env/bin/activate"
                print_info "Then run this script again, or use: pip install codn"
                return 0
            fi
        fi

        if pip install codn; then
            print_success "codn installed successfully with pip!"
            echo
            print_info "Try these commands:"
            echo "   codn --help"
            echo "   codn"
            echo "   codn unused"
            return 0
        else
            print_error "pip install failed"
        fi
    else
        print_error "No package manager available!"
        print_info "Please install pip or uv first:"
        echo "   # Install pip:"
        echo "   python3 -m ensurepip --upgrade"
        echo
        echo "   # Or install uv:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi
}

# Show usage examples
show_examples() {
    echo
    print_colored "$CYAN" "📖 Quick Usage Examples"
    print_colored "$CYAN" "======================="
    echo "Most common commands (save typing!):"
    echo
    print_colored "$GREEN" "   codn                    # Analyze current project"
    print_colored "$GREEN" "   codn unused             # Find unused imports"
    print_colored "$GREEN" "   codn refs main          # Find function references"
    print_colored "$GREEN" "   codn funcs              # List all functions"
    echo
    echo "Traditional commands (also available):"
    echo "   codn analyze project"
    echo "   codn analyze unused-imports"
    echo "   codn analyze find-refs main"
    echo "   codn analyze functions"
    echo
    print_info "Use 'codn --help' to see all available commands"
}

# Cleanup on exit
cleanup() {
    if [[ $? -ne 0 ]]; then
        echo
        print_error "Installation failed!"
        print_info "For manual installation, see: https://github.com/dweb-lab/codn"
        print_info "Or run: python3 install.py"
    fi
}

trap cleanup EXIT

# Run main function
if main; then
    show_examples
    echo
    print_success "🎉 Setup complete! Start analyzing your code with 'codn'"
fi
