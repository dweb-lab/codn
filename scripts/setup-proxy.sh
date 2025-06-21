#!/bin/bash
# Proxy Setup Helper for Codn Development
# Helps configure proxy settings for faster GitHub access

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default proxy settings
DEFAULT_HTTP_PROXY="http://127.0.0.1:7890"
DEFAULT_HTTPS_PROXY="http://127.0.0.1:7890"
DEFAULT_SOCKS_PROXY="socks5://127.0.0.1:7890"

print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo
    print_colored "$CYAN" "🌐 Codn Proxy Setup Helper"
    print_colored "$CYAN" "=========================="
    echo
}

test_connectivity() {
    local url=$1
    local timeout=${2:-5}

    if curl -s --connect-timeout "$timeout" --max-time "$timeout" "$url" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

test_github_speed() {
    print_colored "$BLUE" "🔍 Testing GitHub connectivity..."

    # Test direct connection
    start_time=$(date +%s%N)
    if test_connectivity "https://api.github.com/zen" 10; then
        end_time=$(date +%s%N)
        duration=$((($end_time - $start_time) / 1000000))

        print_colored "$GREEN" "✅ Direct GitHub access works (${duration}ms)"

        if [ $duration -gt 3000 ]; then
            print_colored "$YELLOW" "⚠️  Connection is slow (>3s), proxy might help"
            return 1
        else
            print_colored "$GREEN" "🚀 Connection is fast, no proxy needed"
            return 0
        fi
    else
        print_colored "$RED" "❌ Direct GitHub access failed"
        return 1
    fi
}

test_proxy_connectivity() {
    local http_proxy=$1
    local https_proxy=$2

    print_colored "$BLUE" "🔍 Testing proxy connectivity..."

    # Test if proxy is reachable
    local proxy_host=$(echo "$http_proxy" | sed 's|.*://||' | cut -d: -f1)
    local proxy_port=$(echo "$http_proxy" | sed 's|.*://||' | cut -d: -f2)

    if nc -z "$proxy_host" "$proxy_port" 2>/dev/null; then
        print_colored "$GREEN" "✅ Proxy server is reachable"
    else
        print_colored "$RED" "❌ Proxy server is not reachable"
        return 1
    fi

    # Test GitHub access through proxy
    if https_proxy="$https_proxy" http_proxy="$http_proxy" test_connectivity "https://api.github.com/zen" 10; then
        print_colored "$GREEN" "✅ GitHub access through proxy works"
        return 0
    else
        print_colored "$RED" "❌ GitHub access through proxy failed"
        return 1
    fi
}

setup_shell_proxy() {
    local shell_config=""
    local shell_name=$(basename "$SHELL")

    case "$shell_name" in
        bash)
            shell_config="$HOME/.bashrc"
            ;;
        zsh)
            shell_config="$HOME/.zshrc"
            ;;
        fish)
            shell_config="$HOME/.config/fish/config.fish"
            ;;
        *)
            shell_config="$HOME/.profile"
            ;;
    esac

    print_colored "$BLUE" "📝 Setting up proxy for $shell_name shell..."

    # Create backup
    if [ -f "$shell_config" ]; then
        cp "$shell_config" "${shell_config}.backup.$(date +%Y%m%d-%H%M%S)"
        print_colored "$GREEN" "✅ Backup created: ${shell_config}.backup.*"
    fi

    # Add proxy functions
    cat >> "$shell_config" << 'EOF'

# Codn Proxy Helper Functions
proxy_on() {
    export https_proxy=http://127.0.0.1:7890
    export http_proxy=http://127.0.0.1:7890
    export all_proxy=socks5://127.0.0.1:7890
    export no_proxy="localhost,127.0.0.1,::1"
    echo "🌐 Proxy enabled"
}

proxy_off() {
    unset https_proxy
    unset http_proxy
    unset all_proxy
    unset no_proxy
    echo "🚫 Proxy disabled"
}

proxy_status() {
    if [ -n "$https_proxy" ]; then
        echo "🌐 Proxy is ON: $https_proxy"
    else
        echo "🚫 Proxy is OFF"
    fi
}

# Auto-enable proxy for git and package managers
git() {
    if [ -n "$AUTO_PROXY" ]; then
        https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 command git "$@"
    else
        command git "$@"
    fi
}

EOF

    print_colored "$GREEN" "✅ Proxy functions added to $shell_config"
    print_colored "$YELLOW" "💡 Run 'source $shell_config' or restart terminal to use"
}

setup_git_proxy() {
    print_colored "$BLUE" "🔧 Configuring Git proxy..."

    # Set Git proxy
    git config --global http.proxy "$DEFAULT_HTTP_PROXY"
    git config --global https.proxy "$DEFAULT_HTTPS_PROXY"

    print_colored "$GREEN" "✅ Git proxy configured"
    print_colored "$BLUE" "📋 Git proxy settings:"
    git config --global --get http.proxy 2>/dev/null && echo "  HTTP: $(git config --global --get http.proxy)"
    git config --global --get https.proxy 2>/dev/null && echo "  HTTPS: $(git config --global --get https.proxy)"
}

remove_git_proxy() {
    print_colored "$BLUE" "🧹 Removing Git proxy configuration..."

    git config --global --unset http.proxy 2>/dev/null || true
    git config --global --unset https.proxy 2>/dev/null || true

    print_colored "$GREEN" "✅ Git proxy configuration removed"
}

setup_npm_proxy() {
    if command -v npm >/dev/null 2>&1; then
        print_colored "$BLUE" "📦 Configuring npm proxy..."

        npm config set proxy "$DEFAULT_HTTP_PROXY"
        npm config set https-proxy "$DEFAULT_HTTPS_PROXY"
        npm config set registry "https://registry.npmjs.org/"

        print_colored "$GREEN" "✅ npm proxy configured"
    fi
}

setup_pip_proxy() {
    print_colored "$BLUE" "🐍 Setting up pip proxy configuration..."

    local pip_config_dir=""
    if [ "$(uname)" = "Darwin" ]; then
        pip_config_dir="$HOME/Library/Application Support/pip"
    else
        pip_config_dir="$HOME/.config/pip"
    fi

    mkdir -p "$pip_config_dir"

    cat > "$pip_config_dir/pip.conf" << EOF
[global]
proxy = $DEFAULT_HTTP_PROXY
trusted-host = pypi.org
               pypi.python.org
               files.pythonhosted.org
EOF

    print_colored "$GREEN" "✅ pip proxy configured"
}

create_proxy_script() {
    local script_path="$HOME/.local/bin/codn-proxy"

    mkdir -p "$HOME/.local/bin"

    cat > "$script_path" << 'EOF'
#!/bin/bash
# Codn Proxy Control Script

case "$1" in
    on|enable)
        export https_proxy=http://127.0.0.1:7890
        export http_proxy=http://127.0.0.1:7890
        export all_proxy=socks5://127.0.0.1:7890
        echo "🌐 Proxy enabled for current session"
        ;;
    off|disable)
        unset https_proxy http_proxy all_proxy
        echo "🚫 Proxy disabled for current session"
        ;;
    status)
        if [ -n "$https_proxy" ]; then
            echo "🌐 Proxy is ON: $https_proxy"
        else
            echo "🚫 Proxy is OFF"
        fi
        ;;
    test)
        echo "🔍 Testing connectivity..."
        if curl -s --connect-timeout 5 https://api.github.com/zen >/dev/null; then
            echo "✅ GitHub access works"
        else
            echo "❌ GitHub access failed"
        fi
        ;;
    *)
        echo "Usage: codn-proxy {on|off|status|test}"
        echo "  on     - Enable proxy"
        echo "  off    - Disable proxy"
        echo "  status - Check proxy status"
        echo "  test   - Test GitHub connectivity"
        ;;
esac
EOF

    chmod +x "$script_path"

    print_colored "$GREEN" "✅ Proxy control script created: $script_path"
    print_colored "$BLUE" "💡 Usage: codn-proxy {on|off|status|test}"
}

show_manual_setup() {
    print_colored "$CYAN" "📋 Manual Proxy Setup"
    print_colored "$CYAN" "====================="
    echo
    print_colored "$YELLOW" "🔧 Environment Variables:"
    echo "export https_proxy=http://127.0.0.1:7890"
    echo "export http_proxy=http://127.0.0.1:7890"
    echo "export all_proxy=socks5://127.0.0.1:7890"
    echo
    print_colored "$YELLOW" "🔧 Git Configuration:"
    echo "git config --global http.proxy http://127.0.0.1:7890"
    echo "git config --global https.proxy http://127.0.0.1:7890"
    echo
    print_colored "$YELLOW" "🔧 For Makefile commands:"
    echo "make install-hooks  # (already includes proxy)"
    echo "make test-hooks     # (already includes proxy)"
    echo
    print_colored "$YELLOW" "🔧 Temporary proxy (current shell only):"
    echo "proxy_on    # Enable proxy"
    echo "proxy_off   # Disable proxy"
    echo "proxy_status # Check status"
}

main() {
    print_header

    # Test current connectivity
    if test_github_speed; then
        print_colored "$GREEN" "🎉 Your connection to GitHub is already fast!"
        echo
        read -p "Do you still want to set up proxy? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_colored "$BLUE" "👋 No proxy setup needed. Have a great day!"
            exit 0
        fi
    fi

    # Test proxy availability
    if ! test_proxy_connectivity "$DEFAULT_HTTP_PROXY" "$DEFAULT_HTTPS_PROXY"; then
        print_colored "$RED" "❌ Proxy server is not available or not working"
        print_colored "$YELLOW" "💡 Please check if your proxy is running on 127.0.0.1:7890"
        echo
        show_manual_setup
        exit 1
    fi

    print_colored "$GREEN" "✅ Proxy is working! Setting up automatic configuration..."
    echo

    # Setup options
    echo "📋 Setup options:"
    echo "1. 🛠️  Full setup (shell functions + git + tools)"
    echo "2. 🔧 Git only"
    echo "3. 📝 Show manual setup commands"
    echo "4. 🗑️  Remove proxy configuration"
    echo

    read -p "👉 Choose an option (1-4): " -n 1 -r
    echo

    case $REPLY in
        1)
            print_colored "$BLUE" "🛠️  Setting up full proxy configuration..."
            setup_shell_proxy
            setup_git_proxy
            setup_npm_proxy
            setup_pip_proxy
            create_proxy_script

            print_colored "$GREEN" "🎉 Full proxy setup complete!"
            print_colored "$YELLOW" "💡 Next steps:"
            echo "  1. Restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
            echo "  2. Use 'proxy_on' to enable proxy"
            echo "  3. Use 'proxy_off' to disable proxy"
            echo "  4. Use 'codn-proxy status' to check proxy status"
            ;;
        2)
            setup_git_proxy
            print_colored "$GREEN" "🎉 Git proxy setup complete!"
            ;;
        3)
            show_manual_setup
            ;;
        4)
            print_colored "$BLUE" "🗑️  Removing proxy configuration..."
            remove_git_proxy
            print_colored "$GREEN" "✅ Proxy configuration removed"
            ;;
        *)
            print_colored "$RED" "❌ Invalid option"
            exit 1
            ;;
    esac

    echo
    print_colored "$CYAN" "📚 Useful Commands:"
    echo "  • Test connectivity: codn-proxy test"
    echo "  • Check proxy status: proxy_status"
    echo "  • Codn with proxy: make install-hooks"
    echo "  • Manual proxy: export https_proxy=http://127.0.0.1:7890"

    print_colored "$GREEN" "🚀 Happy coding with faster GitHub access!"
}

# Check if running in a terminal
if [ -t 0 ]; then
    main "$@"
else
    print_colored "$RED" "❌ This script needs to run in an interactive terminal"
    exit 1
fi
