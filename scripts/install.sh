#!/bin/bash
# Modern Universal Installation Script for FUSE (Python Dev Tool)
# Compatible with Linux, macOS, Windows (WSL/Git Bash/MSYS2), and BSD systems

set -e

# ==============================================================================
# COLOR SUPPORT DETECTION
# ==============================================================================

# Check if terminal supports colors
supports_color() {
    if [ -t 1 ]; then
        # Check if we have tput and it reports color support
        if command -v tput >/dev/null 2>&1; then
            if [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
                return 0
            fi
        fi
        # Check TERM environment variable
        case "${TERM:-}" in
            *color*|*-256color|xterm*|screen*|tmux*)
                return 0
                ;;
        esac
    fi
    return 1
}

# Initialize color support
if supports_color && [ "${NO_COLOR:-}" != "1" ]; then
    USE_COLOR=true
else
    USE_COLOR=false
fi

# ==============================================================================
# COLOR PALETTE & STYLING
# ==============================================================================

# Modern color palette with fallback
if [ "$USE_COLOR" = true ]; then
    declare -A COLORS=(
        # Core colors
        ["RESET"]="\033[0m"
        ["BOLD"]="\033[1m"
        ["DIM"]="\033[2m"
        ["ITALIC"]="\033[3m"
        ["UNDERLINE"]="\033[4m"

        # Brand colors
        ["FUSE_BLUE"]="\033[38;5;39m"
        ["FUSE_PURPLE"]="\033[38;5;141m"
        ["FUSE_CYAN"]="\033[38;5;51m"

        # Status colors
        ["SUCCESS"]="\033[38;5;46m"
        ["ERROR"]="\033[38;5;196m"
        ["WARNING"]="\033[38;5;214m"
        ["INFO"]="\033[38;5;75m"
        ["MUTED"]="\033[38;5;240m"
        ["HIGHLIGHT"]="\033[38;5;226m"

        # Gradient colors for fancy output
        ["GRAD1"]="\033[38;5;39m"
        ["GRAD2"]="\033[38;5;45m"
        ["GRAD3"]="\033[38;5;51m"
        ["GRAD4"]="\033[38;5;87m"
    )
else
    # No color fallback
    declare -A COLORS=(
        ["RESET"]=""
        ["BOLD"]=""
        ["DIM"]=""
        ["ITALIC"]=""
        ["UNDERLINE"]=""
        ["FUSE_BLUE"]=""
        ["FUSE_PURPLE"]=""
        ["FUSE_CYAN"]=""
        ["SUCCESS"]=""
        ["ERROR"]=""
        ["WARNING"]=""
        ["INFO"]=""
        ["MUTED"]=""
        ["HIGHLIGHT"]=""
        ["GRAD1"]=""
        ["GRAD2"]=""
        ["GRAD3"]=""
        ["GRAD4"]=""
    )
fi

# Emoji collection with fallback
if [ "$USE_COLOR" = true ] && [ -z "${NO_EMOJI:-}" ]; then
    declare -A EMOJIS=(
        ["ROCKET"]="🚀"
        ["FIRE"]="🔥"
        ["SPARKLES"]="✨"
        ["GEAR"]="⚙️"
        ["SHIELD"]="🛡️"
        ["LIGHTNING"]="⚡"
        ["PACKAGE"]="📦"
        ["DOWNLOAD"]="⬇️"
        ["CHECK"]="✅"
        ["CROSS"]="❌"
        ["WARNING"]="⚠️"
        ["INFO"]="ℹ️"
        ["SEARCH"]="🔍"
        ["WRENCH"]="🔧"
        ["HAMMER"]="🔨"
        ["MAGIC"]="🪄"
        ["STAR"]="⭐"
        ["GLOBE"]="🌍"
        ["COMPUTER"]="💻"
        ["TERMINAL"]="🖥️"
        ["BOOK"]="📚"
        ["CHART"]="📊"
        ["CLEAN"]="🧹"
        ["LOCK"]="🔒"
        ["KEY"]="🗝️"
        ["FOLDER"]="📁"
        ["FILE"]="📄"
        ["LINK"]="🔗"
        ["CLOCK"]="⏰"
        ["HOURGLASS"]="⏳"
        ["PARTY"]="🎉"
        ["THUMBS_UP"]="👍"
        ["HEART"]="💙"
        ["WAVE"]="👋"
    )
else
    # ASCII fallback
    declare -A EMOJIS=(
        ["ROCKET"]="[*]"
        ["FIRE"]="[~]"
        ["SPARKLES"]="[*]"
        ["GEAR"]="[*]"
        ["SHIELD"]="[*]"
        ["LIGHTNING"]="[!]"
        ["PACKAGE"]="[+]"
        ["DOWNLOAD"]="[v]"
        ["CHECK"]="[+]"
        ["CROSS"]="[x]"
        ["WARNING"]="[!]"
        ["INFO"]="[i]"
        ["SEARCH"]="[?]"
        ["WRENCH"]="[*]"
        ["HAMMER"]="[*]"
        ["MAGIC"]="[*]"
        ["STAR"]="[*]"
        ["GLOBE"]="[*]"
        ["COMPUTER"]="[*]"
        ["TERMINAL"]="[*]"
        ["BOOK"]="[*]"
        ["CHART"]="[*]"
        ["CLEAN"]="[*]"
        ["LOCK"]="[*]"
        ["KEY"]="[*]"
        ["FOLDER"]="[*]"
        ["FILE"]="[*]"
        ["LINK"]="[*]"
        ["CLOCK"]="[*]"
        ["HOURGLASS"]="[*]"
        ["PARTY"]="[!]"
        ["THUMBS_UP"]="[+]"
        ["HEART"]="[*]"
        ["WAVE"]="[*]"
    )
fi

# ==============================================================================
# CONFIGURATION & GLOBALS
# ==============================================================================

# Script configuration
readonly SCRIPT_NAME="FUSE Installer"
readonly SCRIPT_VERSION="0.0.1"
readonly PACKAGE_NAME="python-dev-tool"
readonly TOOL_NAME="FUSE"
readonly REQUIRED_PYTHON_VERSION="3.8"

# Installation options
INSTALL_METHOD=""
PYTHON_VERSION=""
FORCE_INSTALL=false
VERBOSE=false
QUIET=false
DRY_RUN=false
SKIP_POST_INSTALL=false

# System detection variables
OS=""
DISTRO=""
VERSION=""
ARCH=""
SHELL_TYPE=""

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

# Enhanced color printing functions
print_with_style() {
    local color="$1"
    local emoji="$2"
    local prefix="$3"
    local message="$4"

    if [ "$QUIET" = false ]; then
        echo -e "${COLORS[$color]}${EMOJIS[$emoji]} $prefix${COLORS[RESET]} $message"
    fi
}

print_header() {
    if [ "$QUIET" = false ]; then
        echo -e "\n"
        echo -e "${COLORS[BOLD]}${COLORS[FUSE_BLUE]}${EMOJIS[ROCKET]} ${TOOL_NAME}${COLORS[RESET]}${COLORS[BOLD]}${COLORS[FUSE_PURPLE]} Installation Script${COLORS[RESET]}"
        echo -e "${COLORS[MUTED]}${EMOJIS[SPARKLES]} Universal Python Development Tool Installer v${SCRIPT_VERSION}${COLORS[RESET]}"
        echo -e "${COLORS[MUTED]}────────────────────────────────────────────────────────────────${COLORS[RESET]}"
        echo -e "\n"
    fi
}

print_success() {
    print_with_style "SUCCESS" "CHECK" "SUCCESS" "$1"
}

print_error() {
    print_with_style "ERROR" "CROSS" "ERROR" "$1" >&2
}

print_warning() {
    print_with_style "WARNING" "WARNING" "WARNING" "$1"
}

print_info() {
    print_with_style "INFO" "INFO" "INFO" "$1"
}

print_step() {
    print_with_style "FUSE_CYAN" "GEAR" "STEP" "$1"
}

print_verbose() {
    if [ "$VERBOSE" = true ]; then
        print_with_style "MUTED" "SEARCH" "DEBUG" "$1"
    fi
}

print_fancy_banner() {
    if [ "$QUIET" = false ]; then
        echo -e "\n"
        if [ "$USE_COLOR" = true ]; then
            echo -e "${COLORS[GRAD1]}███████${COLORS[GRAD2]}╗${COLORS[GRAD3]}██${COLORS[GRAD4]}╗   ██${COLORS[GRAD1]}╗${COLORS[GRAD2]}███████${COLORS[GRAD3]}╗${COLORS[GRAD4]}███████${COLORS[RESET]}"
            echo -e "${COLORS[GRAD2]}██${COLORS[GRAD3]}╔════╝${COLORS[GRAD4]}██${COLORS[GRAD1]}║   ██${COLORS[GRAD2]}║${COLORS[GRAD3]}██${COLORS[GRAD4]}╔════╝${COLORS[GRAD1]}██${COLORS[GRAD2]}╔════╝${COLORS[GRAD3]}${COLORS[RESET]}"
            echo -e "${COLORS[GRAD3]}█████${COLORS[GRAD4]}╗  ██${COLORS[GRAD1]}║   ██${COLORS[GRAD2]}║${COLORS[GRAD3]}███████${COLORS[GRAD4]}╗${COLORS[GRAD1]}█████${COLORS[GRAD2]}╗${COLORS[GRAD3]}${COLORS[RESET]}"
            echo -e "${COLORS[GRAD4]}██${COLORS[GRAD1]}╔══╝  ██${COLORS[GRAD2]}║   ██${COLORS[GRAD3]}║${COLORS[GRAD4]}╚════██${COLORS[GRAD1]}║${COLORS[GRAD2]}██${COLORS[GRAD3]}╔══╝${COLORS[GRAD4]}${COLORS[RESET]}"
            echo -e "${COLORS[GRAD1]}██${COLORS[GRAD2]}║     ╚██████${COLORS[GRAD3]}╔╝${COLORS[GRAD4]}███████${COLORS[GRAD1]}║${COLORS[GRAD2]}███████${COLORS[GRAD3]}╗${COLORS[GRAD4]}${COLORS[RESET]}"
            echo -e "${COLORS[GRAD2]}╚═╝${COLORS[GRAD3]}      ╚═════╝${COLORS[GRAD4]} ╚══════╝${COLORS[GRAD1]}╚══════╝${COLORS[GRAD2]}${COLORS[RESET]}"
        else
            echo -e "███████ ██   ██ ███████ ███████"
            echo -e "██      ██   ██ ██      ██     "
            echo -e "█████   ██   ██ ███████ █████  "
            echo -e "██      ██   ██      ██ ██     "
            echo -e "██       ██████  ███████ ███████"
            echo -e "                               "
        fi
        echo -e "\n"
        echo -e "${COLORS[HIGHLIGHT]}${EMOJIS[LIGHTNING]} Python Development Tool ${EMOJIS[LIGHTNING]}${COLORS[RESET]}"
        echo -e "\n"
    fi
}

# Progress spinner
show_spinner() {
    local pid=$1
    local message="$2"
    local delay=0.1
    local spinstr='|/-\'

    if [ "$QUIET" = false ] && [ "$VERBOSE" = false ]; then
        while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
            local temp=${spinstr#?}
            echo -ne " [${spinstr:0:1}] $message\r"
            local spinstr=$temp${spinstr%"$temp"}
            sleep $delay
        done
        echo -ne "    \r"
    fi
}

# ==============================================================================
# SYSTEM DETECTION
# ==============================================================================

detect_system() {
    print_step "Detecting system environment..."

    # Detect OS
    case "$(uname -s)" in
        Linux*)
            OS="Linux"
            detect_linux_distro
            ;;
        Darwin*)
            OS="macOS"
            VERSION=$(sw_vers -productVersion 2>/dev/null || echo "unknown")
            DISTRO="darwin"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            OS="Windows"
            VERSION=$(cmd.exe /c ver 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+' | head -1 || echo "unknown")
            DISTRO="windows"
            ;;
        FreeBSD*)
            OS="FreeBSD"
            VERSION=$(freebsd-version 2>/dev/null || uname -r)
            DISTRO="freebsd"
            ;;
        OpenBSD*)
            OS="OpenBSD"
            VERSION=$(uname -r)
            DISTRO="openbsd"
            ;;
        NetBSD*)
            OS="NetBSD"
            VERSION=$(uname -r)
            DISTRO="netbsd"
            ;;
        *)
            OS="Unknown"
            VERSION="unknown"
            DISTRO="unknown"
            ;;
    esac

    # Detect architecture
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64)
            ARCH="x86_64"
            ;;
        i*86)
            ARCH="i386"
            ;;
        arm64|aarch64)
            ARCH="arm64"
            ;;
        armv7l|armv6l)
            ARCH="arm"
            ;;
        *)
            ARCH="unknown"
            ;;
    esac

    # Detect shell
    SHELL_TYPE=$(basename "$SHELL" 2>/dev/null || echo "unknown")

    print_verbose "System: $OS $VERSION ($DISTRO)"
    print_verbose "Architecture: $ARCH"
    print_verbose "Shell: $SHELL_TYPE"
}

detect_linux_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO="$ID"
        VERSION="$VERSION_ID"
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
        VERSION=$(cat /etc/debian_version)
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
        VERSION=$(cat /etc/redhat-release | sed 's/.*release //' | sed 's/ .*//')
    elif [ -f /etc/arch-release ]; then
        DISTRO="arch"
        VERSION="rolling"
    elif [ -f /etc/alpine-release ]; then
        DISTRO="alpine"
        VERSION=$(cat /etc/alpine-release)
    elif [ -f /etc/gentoo-release ]; then
        DISTRO="gentoo"
        VERSION=$(cat /etc/gentoo-release | sed 's/.*release //' | sed 's/ .*//')
    else
        DISTRO="unknown"
        VERSION="unknown"
    fi
}

# ==============================================================================
# PYTHON DETECTION & VALIDATION
# ==============================================================================

find_python() {
    print_step "Detecting Python installation..."

    local python_candidates=()

    if [ -n "$PYTHON_VERSION" ]; then
        python_candidates=("python$PYTHON_VERSION" "python${PYTHON_VERSION%.*}")
    else
        python_candidates=(
            "python3" "python" "python3.12" "python3.11" "python3.10" "python3.9" "python3.8"
            "py" "python.exe" "python3.exe"
        )
    fi

    for cmd in "${python_candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            PYTHON_CMD="$cmd"
            break
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        print_error "Python not found. Please install Python ${REQUIRED_PYTHON_VERSION}+ first."
        suggest_python_installation
        exit 1
    fi

    validate_python_version
}

validate_python_version() {
    local python_version_full
    python_version_full=$($PYTHON_CMD --version 2>&1 | sed 's/Python //')

    local major minor patch
    major=$(echo "$python_version_full" | cut -d. -f1)
    minor=$(echo "$python_version_full" | cut -d. -f2)
    patch=$(echo "$python_version_full" | cut -d. -f3)

    # Check minimum version requirement
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
        print_error "Python ${REQUIRED_PYTHON_VERSION}+ is required. Found: $python_version_full"
        suggest_python_installation
        exit 1
    fi

    print_verbose "Using Python: $PYTHON_CMD ($python_version_full)"
    print_success "Python $python_version_full detected"
}

suggest_python_installation() {
    print_info "Python installation suggestions:"
    case "$OS" in
        "Linux")
            case "$DISTRO" in
                "ubuntu"|"debian")
                    echo -e "  sudo apt update && sudo apt install python3 python3-pip"
                    ;;
                "fedora"|"rhel"|"centos")
                    echo -e "  sudo dnf install python3 python3-pip"
                    ;;
                "arch")
                    echo -e "  sudo pacman -S python python-pip"
                    ;;
                "alpine")
                    echo -e "  apk add python3 py3-pip"
                    ;;
                *)
                    echo -e "  Please install Python ${REQUIRED_PYTHON_VERSION}+ using your system package manager"
                    ;;
            esac
            ;;
        "macOS")
            echo -e "  brew install python3"
            echo -e "  Or download from: https://www.python.org/downloads/"
            ;;
        "Windows")
            echo -e "  Download from: https://www.python.org/downloads/"
            echo -e "  Or use: winget install Python.Python.3"
            ;;
    esac
}

check_pip() {
    print_step "Checking pip availability..."

    if ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
        print_warning "pip not found, attempting to install..."

        # Try to install pip
        if ! $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null; then
            print_error "pip installation failed. Please install pip manually."
            suggest_pip_installation
            exit 1
        fi
    fi

    print_success "pip is available"
}

suggest_pip_installation() {
    print_info "pip installation suggestions:"
    case "$OS" in
        "Linux")
            case "$DISTRO" in
                "ubuntu"|"debian")
                    echo -e "  sudo apt install python3-pip"
                    ;;
                "fedora"|"rhel"|"centos")
                    echo -e "  sudo dnf install python3-pip"
                    ;;
                "arch")
                    echo -e "  sudo pacman -S python-pip"
                    ;;
                "alpine")
                    echo -e "  apk add py3-pip"
                    ;;
            esac
            ;;
        "macOS")
            echo -e "  python3 -m ensurepip --upgrade"
            ;;
        "Windows")
            echo -e "  python -m ensurepip --upgrade"
            ;;
    esac
}

# ==============================================================================
# INSTALLATION METHODS
# ==============================================================================

install_via_pip() {
    print_step "Installing $TOOL_NAME via pip..."

    find_python
    check_pip

    # Check if already installed
    if $PYTHON_CMD -m pip show "$PACKAGE_NAME" >/dev/null 2>&1 && [ "$FORCE_INSTALL" = false ]; then
        local current_version
        current_version=$($PYTHON_CMD -m pip show "$PACKAGE_NAME" | grep "Version:" | cut -d' ' -f2)
        print_warning "$TOOL_NAME v$current_version is already installed. Use --force to reinstall."
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would install $PACKAGE_NAME via pip"
        return 0
    fi

    # Prepare pip command
    local pip_args=()
    [ "$FORCE_INSTALL" = true ] && pip_args+=("--upgrade" "--force-reinstall")
    [ "$VERBOSE" = true ] && pip_args+=("--verbose")

    # Install package
    print_info "Installing $PACKAGE_NAME..."
    if $PYTHON_CMD -m pip install "${pip_args[@]}" "$PACKAGE_NAME"; then
        print_success "$TOOL_NAME installed successfully via pip"
        return 0
    else
        print_error "Failed to install $TOOL_NAME via pip"
        return 1
    fi
}

install_via_system() {
    print_step "Installing $TOOL_NAME via system package manager..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would install $PACKAGE_NAME via system package manager"
        return 0
    fi

    case "$DISTRO" in
        "ubuntu"|"debian")
            install_deb_package
            ;;
        "fedora"|"rhel"|"centos"|"rocky"|"alma")
            install_rpm_package
            ;;
        "arch"|"manjaro")
            install_arch_package
            ;;
        "alpine")
            install_alpine_package
            ;;
        "darwin")
            install_macos_package
            ;;
        *)
            print_warning "System package manager not supported for $DISTRO"
            print_info "Falling back to pip installation..."
            install_via_pip
            ;;
    esac
}

install_deb_package() {
    print_info "Setting up APT repository..."

    # Install required packages
    if ! command -v curl >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y curl gpg
    fi

    # Add GPG key and repository
    curl -fsSL "https://releases.fuse-tool.com/gpg" | sudo gpg --dearmor -o /usr/share/keyrings/fuse-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/fuse-archive-keyring.gpg] https://releases.fuse-tool.com/apt stable main" | sudo tee /etc/apt/sources.list.d/fuse.list

    sudo apt-get update
    sudo apt-get install -y "$PACKAGE_NAME"
}

install_rpm_package() {
    print_info "Setting up YUM/DNF repository..."

    sudo tee /etc/yum.repos.d/fuse.repo <<EOF
[fuse]
name=FUSE Repository
baseurl=https://releases.fuse-tool.com/rpm/\$basearch
enabled=1
gpgcheck=1
gpgkey=https://releases.fuse-tool.com/gpg
EOF

    if command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y "$PACKAGE_NAME"
    else
        sudo yum install -y "$PACKAGE_NAME"
    fi
}

install_arch_package() {
    print_info "Installing from AUR..."

    if command -v yay >/dev/null 2>&1; then
        yay -S --noconfirm "$PACKAGE_NAME"
    elif command -v paru >/dev/null 2>&1; then
        paru -S --noconfirm "$PACKAGE_NAME"
    elif command -v makepkg >/dev/null 2>&1; then
        # Manual AUR installation
        local temp_dir
        temp_dir=$(mktemp -d)
        cd "$temp_dir"
        curl -L "https://aur.archlinux.org/cgit/aur.git/snapshot/${PACKAGE_NAME}.tar.gz" | tar xz
        cd "$PACKAGE_NAME"
        makepkg -si --noconfirm
        cd /
        rm -rf "$temp_dir"
    else
        print_error "AUR helper or makepkg required for Arch Linux installation"
        print_info "Falling back to pip installation..."
        install_via_pip
    fi
}

install_alpine_package() {
    print_info "Installing via apk..."

    # Add community repository if not present
    if ! grep -q "community" /etc/apk/repositories; then
        echo "https://dl-cdn.alpinelinux.org/alpine/v$(cat /etc/alpine-release | cut -d. -f1-2)/community" | sudo tee -a /etc/apk/repositories
    fi

    sudo apk update
    sudo apk add "$PACKAGE_NAME" || {
        print_warning "Package not available in Alpine repositories"
        print_info "Falling back to pip installation..."
        install_via_pip
    }
}

install_macos_package() {
    print_info "Installing via Homebrew..."

    if command -v brew >/dev/null 2>&1; then
        brew tap fuse-tool/tap
        brew install "$PACKAGE_NAME"
    else
        print_error "Homebrew not found. Please install Homebrew first:"
        print_info "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        print_info "Falling back to pip installation..."
        install_via_pip
    fi
}

# ==============================================================================
# AUTO-DETECTION & SMART INSTALLATION
# ==============================================================================

auto_detect_method() {
    print_step "Auto-detecting best installation method..."

    local score_pip=0
    local score_system=0

    # Score pip method
    if find_python 2>/dev/null && check_pip 2>/dev/null; then
        score_pip=$((score_pip + 10))
    fi

    # Score system method based on OS support
    case "$DISTRO" in
        "ubuntu"|"debian"|"fedora"|"rhel"|"centos"|"arch"|"alpine"|"darwin")
            score_system=$((score_system + 8))
            ;;
        *)
            score_system=$((score_system + 2))
            ;;
    esac

    # Check for package manager availability
    case "$DISTRO" in
        "ubuntu"|"debian")
            command -v apt-get >/dev/null 2>&1 && score_system=$((score_system + 5))
            ;;
        "fedora"|"rhel"|"centos")
            (command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1) && score_system=$((score_system + 5))
            ;;
        "arch")
            (command -v yay >/dev/null 2>&1 || command -v paru >/dev/null 2>&1 || command -v makepkg >/dev/null 2>&1) && score_system=$((score_system + 5))
            ;;
        "alpine")
            command -v apk >/dev/null 2>&1 && score_system=$((score_system + 5))
            ;;
        "darwin")
            command -v brew >/dev/null 2>&1 && score_system=$((score_system + 5))
            ;;
    esac

    print_verbose "Installation method scores - pip: $score_pip, system: $score_system"

    if [ $score_pip -gt $score_system ]; then
        print_info "Auto-selected: pip installation"
        install_via_pip
    else
        print_info "Auto-selected: system package manager"
        install_via_system
    fi
}

# ==============================================================================
# POST-INSTALLATION SETUP
# ==============================================================================

verify_installation() {
    print_step "Verifying installation..."

    local cmd_variants=("fuse" "python-dev-tool" "$PACKAGE_NAME")
    local found_cmd=""

    for cmd in "${cmd_variants[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            found_cmd="$cmd"
            break
        fi
    done

    if [ -z "$found_cmd" ]; then
        # Try with Python module
        if $PYTHON_CMD -c "import $PACKAGE_NAME" 2>/dev/null; then
            found_cmd="$PYTHON_CMD -m $PACKAGE_NAME"
        fi
    fi

    if [ -n "$found_cmd" ]; then
        local version
        version=$($found_cmd --version 2>/dev/null || echo "unknown")
        print_success "$TOOL_NAME $version installed and verified!"
        return 0
    else
        print_error "Installation verification failed - command not found"
        return 1
    fi
}

setup_shell_integration() {
    print_step "Setting up shell integration..."

    local shell_configs=()
    case "$SHELL_TYPE" in
        "bash")
            shell_configs=("$HOME/.bashrc" "$HOME/.bash_profile")
            ;;
        "zsh")
            shell_configs=("$HOME/.zshrc")
            ;;
        "fish")
            shell_configs=("$HOME/.config/fish/config.fish")
            ;;
        *)
            print_verbose "Shell integration not available for $SHELL_TYPE"
            return 0
            ;;
    esac

    local integration_line="# FUSE completion"
    local completion_cmd="eval \"\$(fuse completion $SHELL_TYPE)\""

    for config in "${shell_configs[@]}"; do
        if [ -f "$config" ]; then
            if ! grep -q "$integration_line" "$config"; then
                echo -e "\n$integration_line\n$completion_cmd\n" >> "$config"
                print_verbose "Added shell completion to $config"
            fi
        fi
    done

    print_success "Shell integration configured"
}

create_initial_config() {
    print_step "Creating initial configuration..."

    local config_dir="$HOME/.fuse"
    local config_file="$config_dir/config.toml"

    if [ ! -d "$config_dir" ]; then
        mkdir -p "$config_dir"
    fi

    if [ ! -f "$config_file" ] || [ "$FORCE_INSTALL" = true ]; then
        cat > "$config_file" <<EOF
# FUSE Configuration File
# Generated by installer on $(date)

[general]
version = "1.0"
auto_update = true
telemetry = false

[development]
default_port = 8000
hot_reload = true
open_browser = true

[build]
output_dir = "dist"
minify = true
source_maps = true

[theme]
color_scheme = "dark"
accent_color = "blue"
EOF
        print_success "Initial configuration created at $config_file"
    else
        print_info "Configuration file already exists"
    fi
}

show_next_steps() {
    if [ "$QUIET" = false ]; then
        echo -e "\n"
        print_fancy_banner

        echo -e "${COLORS[SUCCESS]}${EMOJIS[PARTY]}${EMOJIS[PARTY]} Installation completed successfully! ${EMOJIS[PARTY]}${COLORS[RESET]}"
        echo -e "\n"

        echo -e "${COLORS[BOLD]}${EMOJIS[ROCKET]}${EMOJIS[ROCKET]} Quick Start Guide:${COLORS[RESET]}"
        echo -e "  ${COLORS[FUSE_CYAN]}1.${COLORS[RESET]} Navigate to your Python project directory"
        echo -e "  ${COLORS[FUSE_CYAN]}2.${COLORS[RESET]} Run: ${COLORS[HIGHLIGHT]}fuse init${COLORS[RESET]}"
        echo -e "  ${COLORS[FUSE_CYAN]}3.${COLORS[RESET]} Run: ${COLORS[HIGHLIGHT]}fuse dev${COLORS[RESET]}"
        echo -e "  ${COLORS[FUSE_CYAN]}4.${COLORS[RESET]} Open your browser to the provided URL"
        echo -e "\n"

        echo -e "${COLORS[BOLD]}${EMOJIS[BOOK]}${EMOJIS[BOOK]} Resources:${COLORS[RESET]}"
        echo -e "  ${COLORS[MUTED]}${EMOJIS[LINK]} Documentation:${COLORS[RESET]} https://fuse-tool.readthedocs.io"
        echo -e "  ${COLORS[MUTED]}${EMOJIS[TERMINAL]} Help:${COLORS[RESET]} ${COLORS[HIGHLIGHT]}fuse --help${COLORS[RESET]}"
        echo -e "  ${COLORS[MUTED]}${EMOJIS[MAGIC]} Examples:${COLORS[RESET]} ${COLORS[HIGHLIGHT]}fuse examples${COLORS[RESET]}"
        echo -e "  ${COLORS[MUTED]}${EMOJIS[GEAR]} Config:${COLORS[RESET]} ${COLORS[HIGHLIGHT]}fuse config${COLORS[RESET]}"
        echo -e "\n"

        echo -e "${COLORS[MUTED]}${EMOJIS[HEART]}${EMOJIS[HEART]} Thank you for using FUSE! ${EMOJIS[HEART]}${COLORS[RESET]}"
        echo -e "\n"
    fi
}

# ==============================================================================
# HELP & USAGE
# ==============================================================================

show_usage() {
    echo -e "${COLORS[BOLD]}${EMOJIS[ROCKET]} FUSE Universal Installer v${SCRIPT_VERSION}${COLORS[RESET]}\n"

    echo -e "${COLORS[BOLD]}USAGE:${COLORS[RESET]}"
    echo -e "    $0 [OPTIONS]\n"

    echo -e "${COLORS[BOLD]}DESCRIPTION:${COLORS[RESET]}"
    echo -e "    Universal installation script for FUSE (Python Development Tool)\n"
    echo -e "    Compatible with Linux, macOS, Windows, and BSD systems\n"

    echo -e "${COLORS[BOLD]}OPTIONS:${COLORS[RESET]}"
    echo -e "    ${COLORS[FUSE_CYAN]}-m, --method METHOD${COLORS[RESET]}     Installation method: pip, system, or auto (default: auto)"
    echo -e "    ${COLORS[FUSE_CYAN]}-p, --python VERSION${COLORS[RESET]}    Python version to use (default: auto-detect)"
    echo -e "    ${COLORS[FUSE_CYAN]}-f, --force${COLORS[RESET]}             Force installation even if already installed"
    echo -e "    ${COLORS[FUSE_CYAN]}-v, --verbose${COLORS[RESET]}           Enable verbose output"
    echo -e "    ${COLORS[FUSE_CYAN]}-q, --quiet${COLORS[RESET]}             Suppress non-essential output"
    echo -e "    ${COLORS[FUSE_CYAN]}-n, --dry-run${COLORS[RESET]}           Show what would be done without executing"
    echo -e "    ${COLORS[FUSE_CYAN]}--skip-post-install${COLORS[RESET]}     Skip post-installation setup"
    echo -e "    ${COLORS[FUSE_CYAN]}-h, --help${COLORS[RESET]}              Show this help message"
    echo -e "    ${COLORS[FUSE_CYAN]}--version${COLORS[RESET]}               Show installer version\n"

    echo -e "${COLORS[BOLD]}INSTALLATION METHODS:${COLORS[RESET]}"
    echo -e "    ${COLORS[SUCCESS]}pip${COLORS[RESET]}                    Install via pip (recommended, universal)"
    echo -e "    ${COLORS[SUCCESS]}system${COLORS[RESET]}                 Install via system package manager"
    echo -e "    ${COLORS[SUCCESS]}auto${COLORS[RESET]}                   Auto-detect best method (default)\n"

    echo -e "${COLORS[BOLD]}EXAMPLES:${COLORS[RESET]}"
    echo -e "    ${COLORS[MUTED]}# Basic installation with auto-detection${COLORS[RESET]}"
    echo -e "    $0"
    echo -e "    ${COLORS[MUTED]}# Install via pip with specific Python version${COLORS[RESET]}"
    echo -e "    $0 --method pip --python 3.11"
    echo -e "    ${COLORS[MUTED]}# Force reinstall via system package manager${COLORS[RESET]}"
    echo -e "    $0 --method system --force"
    echo -e "    ${COLORS[MUTED]}# Dry run to see what would be installed${COLORS[RESET]}"
    echo -e "    $0 --dry-run --verbose"
    echo -e "    ${COLORS[MUTED]}# Quiet installation for scripts${COLORS[RESET]}"
    echo -e "    $0 --quiet --skip-post-install\n"

    echo -e "${COLORS[BOLD]}SUPPORTED SYSTEMS:${COLORS[RESET]}"
    echo -e "    ${COLORS[SUCCESS]}Linux:${COLORS[RESET]}   Ubuntu, Debian, Fedora, RHEL, CentOS, Arch, Alpine, Gentoo"
    echo -e "    ${COLORS[SUCCESS]}macOS:${COLORS[RESET]}   10.14+ (Homebrew recommended)"
    echo -e "    ${COLORS[SUCCESS]}Windows:${COLORS[RESET]} WSL, Git Bash, MSYS2, Cygwin"
    echo -e "    ${COLORS[SUCCESS]}BSD:${COLORS[RESET]}     FreeBSD, OpenBSD, NetBSD\n"

    echo -e "${COLORS[BOLD]}REQUIREMENTS:${COLORS[RESET]}"
    echo -e "    ${COLORS[MUTED]}•${COLORS[RESET]} Python ${REQUIRED_PYTHON_VERSION}+ with pip"
    echo -e "    ${COLORS[MUTED]}•${COLORS[RESET]} Internet connection"
    echo -e "    ${COLORS[MUTED]}•${COLORS[RESET]} Appropriate permissions for installation\n"

    echo -e "${COLORS[MUTED]}For more information, visit: https://fuse-tool.com${COLORS[RESET]}"
}

show_version() {
    echo -e "${COLORS[BOLD]}${EMOJIS[ROCKET]} FUSE Universal Installer${COLORS[RESET]}"
    echo -e "${COLORS[MUTED]}Version: ${SCRIPT_VERSION}${COLORS[RESET]}"
    echo -e "${COLORS[MUTED]}Target: ${PACKAGE_NAME}${COLORS[RESET]}"
    echo -e "${COLORS[MUTED]}Python: ${REQUIRED_PYTHON_VERSION}+${COLORS[RESET]}"
}

# ==============================================================================
# ARGUMENT PARSING
# ==============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--method)
                INSTALL_METHOD="$2"
                if [[ ! "$INSTALL_METHOD" =~ ^(pip|system|auto)$ ]]; then
                    print_error "Invalid installation method: $INSTALL_METHOD"
                    print_info "Valid methods: pip, system, auto"
                    exit 1
                fi
                shift 2
                ;;
            -p|--python)
                PYTHON_VERSION="$2"
                if [[ ! "$PYTHON_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
                    print_error "Invalid Python version format: $PYTHON_VERSION"
                    print_info "Expected format: X.Y (e.g., 3.11)"
                    exit 1
                fi
                shift 2
                ;;
            -f|--force)
                FORCE_INSTALL=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-post-install)
                SKIP_POST_INSTALL=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            --version)
                show_version
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                print_info "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Validate conflicting options
    if [ "$VERBOSE" = true ] && [ "$QUIET" = true ]; then
        print_error "Cannot use --verbose and --quiet together"
        exit 1
    fi

    # Set default method
    if [ -z "$INSTALL_METHOD" ]; then
        INSTALL_METHOD="auto"
    fi
}

# ==============================================================================
# CLEANUP & ERROR HANDLING
# ==============================================================================

cleanup() {
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        print_error "Installation failed with exit code $exit_code"

        if [ "$VERBOSE" = true ]; then
            print_info "Debug information:"
            print_info "  OS: $OS $VERSION ($DISTRO)"
            print_info "  Architecture: $ARCH"
            print_info "  Python: ${PYTHON_CMD:-not found}"
            print_info "  Method: $INSTALL_METHOD"
            print_info "  Shell: $SHELL_TYPE"
        fi

        print_info "For help, visit: https://fuse-tool.com/docs/installation"
        print_info "Or report issues at: https://github.com/fuse-tool/fuse/issues"
    fi

    exit $exit_code
}

# Set up signal handlers
trap cleanup EXIT
trap 'print_error "Installation interrupted by user"; exit 130' INT TERM

# ==============================================================================
# MAIN INSTALLATION LOGIC
# ==============================================================================

run_installation() {
    print_header

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN MODE - No actual installation will be performed"
        echo -e "\n"
    fi

    # System detection
    detect_system

    # Execute installation method
    case "$INSTALL_METHOD" in
        "pip")
            install_via_pip
            ;;
        "system")
            install_via_system
            ;;
        "auto")
            auto_detect_method
            ;;
        *)
            print_error "Invalid installation method: $INSTALL_METHOD"
            exit 1
            ;;
    esac

    # Post-installation setup
    if [ "$SKIP_POST_INSTALL" = false ] && [ "$DRY_RUN" = false ]; then
        if verify_installation; then
            setup_shell_integration
            create_initial_config
            show_next_steps
        else
            print_error "Installation verification failed"
            exit 1
        fi
    elif [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would verify installation and run post-install setup"
    fi

    print_success "Installation process completed successfully!"
}

# ==============================================================================
# ENTRY POINT
# ==============================================================================

main() {
    # Parse command line arguments
    parse_arguments "$@"

    # Check for required tools
    if ! command -v uname >/dev/null 2>&1; then
        print_error "Required command 'uname' not found"
        exit 1
    fi

    # Run the installation
    run_installation
}

# Only run main if script is executed directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
