#!/bin/bash
# FUSE (python-dev-tool) - Enhanced Build and Publication Script

set -e

# ==============================================================================
# COLOR PALETTE & STYLING
# ==============================================================================

# Modern color palette with 256-color support
declare -A COLORS=(
    # Core colors
    ["RESET"]="\033[0m"
    ["BOLD"]="\033[1m"
    ["DIM"]="\033[2m"
    ["ITALIC"]="\033[3m"
    ["UNDERLINE"]="\033[4m"

    # Brand colors
    ["FUSE_BLUE"]="\033[38;5;39m"      # Electric blue
    ["FUSE_PURPLE"]="\033[38;5;141m"   # Soft purple
    ["FUSE_CYAN"]="\033[38;5;51m"      # Bright cyan

    # Status colors
    ["SUCCESS"]="\033[38;5;46m"        # Bright green
    ["ERROR"]="\033[38;5;196m"         # Bright red
    ["WARNING"]="\033[38;5;214m"       # Orange
    ["INFO"]="\033[38;5;75m"           # Light blue
    ["MUTED"]="\033[38;5;240m"         # Gray
    ["HIGHLIGHT"]="\033[38;5;226m"     # Yellow

    # Gradient colors for fancy output
    ["GRAD1"]="\033[38;5;39m"          # Blue
    ["GRAD2"]="\033[38;5;45m"          # Cyan
    ["GRAD3"]="\033[38;5;51m"          # Light cyan
    ["GRAD4"]="\033[38;5;87m"          # Aqua
)

# Emoji collection
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

# ==============================================================================
# CONFIGURATION & GLOBALS
# ==============================================================================

# Script configuration
readonly SCRIPT_NAME="FUSE Publisher"
readonly SCRIPT_VERSION="1.0.0"
readonly PACKAGE_NAME="python-dev-tool"
readonly TOOL_NAME="FUSE"
readonly REQUIRED_PYTHON_VERSION="3.8"
readonly GITHUB_REPO="lyznne/python-dev-tool"

# Publication options
PUBLISH_TARGET="all"
DRY_RUN=false
FORCE=false
VERBOSE=false
QUIET=false
SKIP_TESTS=false

# System detection variables
OS=""
DISTRO=""
VERSION=""
ARCH=""

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
PACKAGES_DIR="$PROJECT_ROOT/packages"
REPO_DIR="$PROJECT_ROOT/repo"

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

print_with_style() {
    local color="$1"
    local emoji="$2"
    local prefix="$3"
    local message="$4"

    if [ "$QUIET" = false ]; then
        echo -e "${COLORS[$color]}${EMOJIS[$emoji]} ${prefix}${COLORS[RESET]} $message"
    fi
}

print_header() {
    if [ "$QUIET" = false ]; then
        echo
        echo -e "${COLORS[BOLD]}${COLORS[FUSE_BLUE]}${EMOJIS[ROCKET]} ${TOOL_NAME} ${COLORS[RESET]}${COLORS[BOLD]}${COLORS[FUSE_PURPLE]}Publication Script${COLORS[RESET]}"
        echo -e "${COLORS[MUTED]}${EMOJIS[SPARKLES]} Version ${SCRIPT_VERSION}${COLORS[RESET]}"
        echo -e "${COLORS[MUTED]}────────────────────────────────────────────────────────────────${COLORS[RESET]}"
        echo
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
        echo
        echo -e "${COLORS[GRAD1]}███████${COLORS[GRAD2]}╗${COLORS[GRAD3]}██${COLORS[GRAD4]}╗${COLORS[GRAD1]}   ██${COLORS[GRAD2]}╗${COLORS[GRAD3]}███████${COLORS[GRAD4]}╗${COLORS[GRAD1]}███████${COLORS[RESET]}"
        echo -e "${COLORS[GRAD2]}██${COLORS[GRAD3]}╔════╝${COLORS[GRAD4]}██${COLORS[GRAD1]}║${COLORS[GRAD2]}   ██${COLORS[GRAD3]}║${COLORS[GRAD4]}██${COLORS[GRAD1]}╔════╝${COLORS[GRAD2]}██${COLORS[GRAD3]}╔════╝${COLORS[RESET]}"
        echo -e "${COLORS[GRAD3]}█████${COLORS[GRAD4]}╗${COLORS[GRAD1]}  ██${COLORS[GRAD2]}║${COLORS[GRAD3]}   ██${COLORS[GRAD4]}║${COLORS[GRAD1]}███████${COLORS[GRAD2]}╗${COLORS[GRAD3]}█████${COLORS[GRAD4]}╗${COLORS[RESET]}"
        echo -e "${COLORS[GRAD4]}██${COLORS[GRAD1]}╔══╝${COLORS[GRAD2]}  ██${COLORS[GRAD3]}║${COLORS[GRAD4]}   ██${COLORS[GRAD1]}║${COLORS[GRAD2]}╚════██${COLORS[GRAD3]}║${COLORS[GRAD4]}██${COLORS[GRAD1]}╔══╝${COLORS[RESET]}"
        echo -e "${COLORS[GRAD1]}██${COLORS[GRAD2]}║${COLORS[GRAD3]}     ╚██████${COLORS[GRAD4]}╔╝${COLORS[GRAD1]}███████${COLORS[GRAD2]}║${COLORS[GRAD3]}███████${COLORS[GRAD4]}╗${COLORS[RESET]}"
        echo -e "${COLORS[GRAD2]}╚═╝${COLORS[GRAD3]}      ╚═════╝${COLORS[GRAD4]} ╚══════╝${COLORS[GRAD1]}╚══════╝${COLORS[RESET]}"
        echo
        echo -e "${COLORS[HIGHLIGHT]}${EMOJIS[LIGHTNING]} Python Development Tool ${EMOJIS[LIGHTNING]}${COLORS[RESET]}"
        echo
    fi
}

show_spinner() {
    local pid=$1
    local message="$2"
    local delay=0.1
    local spinstr='|/-\'

    if [ "$QUIET" = false ] && [ "$VERBOSE" = false ]; then
        while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
            local temp=${spinstr#?}
            printf " [%c] %s\r" "$spinstr" "$message"
            local spinstr=$temp${spinstr%"$temp"}
            sleep $delay
        done
        printf "    \r"
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

    print_verbose "System: $OS $VERSION ($DISTRO)"
    print_verbose "Architecture: $ARCH"
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
# BUILD ENVIRONMENT SETUP
# ==============================================================================

setup_build_env() {
    print_step "Setting up build environment..."

    mkdir -p "$BUILD_DIR" "$DIST_DIR" "$PACKAGES_DIR" "$REPO_DIR"

    # Clean previous builds
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "${BUILD_DIR:?}"/*
    fi
    if [ -d "$PACKAGES_DIR" ]; then
        rm -rf "${PACKAGES_DIR:?}"/*
    fi

    print_success "Build environment ready"
}

# ==============================================================================
# VERSION MANAGEMENT
# ==============================================================================

update_version() {
    local version=$1
    print_step "Updating version to $version..."

    # Update pyproject.toml
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        sed -i.bak "s/^version = .*/version = \"$version\"/" "$PROJECT_ROOT/pyproject.toml"
        rm -f "$PROJECT_ROOT/pyproject.toml.bak"
    fi

    # Update __init__.py
    if [ -f "$PROJECT_ROOT/src/python_dev_tool/__init__.py" ]; then
        sed -i.bak "s/^__version__ = .*/__version__ = \"$version\"/" "$PROJECT_ROOT/src/python_dev_tool/__init__.py"
        rm -f "$PROJECT_ROOT/src/python_dev_tool/__init__.py.bak"
    fi

    # Update CHANGELOG.md
    if [ -f "$PROJECT_ROOT/CHANGELOG.md" ]; then
        local date=$(date +%Y-%m-%d)
        sed -i.bak "s/^## \[Unreleased\]/## [Unreleased]\n\n## [$version] - $date/" "$PROJECT_ROOT/CHANGELOG.md"
        rm -f "$PROJECT_ROOT/CHANGELOG.md.bak"
    fi

    print_success "Version updated to $version"
}

# ==============================================================================
# TESTING
# ==============================================================================

run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests as requested"
        return 0
    fi

    print_step "Running tests..."

    cd "$PROJECT_ROOT"

    # Install development dependencies
    if ! python3 -m pip install -e ".[dev]"; then
        print_error "Failed to install development dependencies"
        exit 1
    fi

    # Run tests
    if ! python3 -m pytest tests/ -v --cov=src/python_dev_tool --cov-report=term-missing; then
        print_error "Tests failed"
        exit 1
    fi

    # Run linting
    if ! python3 -m flake8 src/; then
        print_error "Linting failed"
        exit 1
    fi

    print_success "All tests passed"
}

# ==============================================================================
# PACKAGE BUILDING
# ==============================================================================

build_wheel() {
    print_step "Building Python wheel..."

    cd "$PROJECT_ROOT"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would build wheel package"
        return 0
    fi

    if ! python3 -m build --wheel --outdir "$DIST_DIR"; then
        print_error "Failed to build wheel"
        exit 1
    fi

    # Move the wheel to packages directory
    mv "$DIST_DIR"/*.whl "$PACKAGES_DIR/"

    print_success "Python wheel built successfully"
}

build_deb() {
    print_step "Building Debian package..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would build Debian package"
        return 0
    fi

    if ! command -v dpkg-deb >/dev/null 2>&1; then
        print_warning "dpkg-deb not available, skipping Debian package"
        return 0
    fi

    local deb_dir="$BUILD_DIR/debian"
    local install_dir="$deb_dir/opt/$PACKAGE_NAME"
    local bin_dir="$deb_dir/usr/local/bin"

    mkdir -p "$install_dir" "$bin_dir" "$deb_dir/DEBIAN"

    # Copy application files
    cp -r "$PROJECT_ROOT/src/"* "$install_dir/"

    # Create wrapper script
    cat > "$bin_dir/$PACKAGE_NAME" << 'EOF'
#!/bin/bash
export PYTHONPATH="/opt/$PACKAGE_NAME:$PYTHONPATH"
python3 -m python_dev_tool.cli.main "$@"
EOF
    chmod +x "$bin_dir/$PACKAGE_NAME"

    # Create control file
    cat > "$deb_dir/DEBIAN/control" << EOF
Package: $PACKAGE_NAME
Version: $PACKAGE_VERSION
Section: devel
Priority: optional
Architecture: all
Depends: python3 (>= $REQUIRED_PYTHON_VERSION), python3-pip
Maintainer: $MAINTAINER
Description: $DESCRIPTION
Homepage: $HOMEPAGE
EOF

    # Build package
    if ! dpkg-deb --build "$deb_dir" "$PACKAGES_DIR/${PACKAGE_NAME}_${PACKAGE_VERSION}_all.deb"; then
        print_error "Failed to build Debian package"
        exit 1
    fi

    print_success "Debian package built successfully"
}

build_rpm() {
    print_step "Building RPM package..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would build RPM package"
        return 0
    fi

    if ! command -v rpmbuild >/dev/null 2>&1; then
        print_warning "rpmbuild not available, skipping RPM package"
        return 0
    fi

    local rpm_dir="$BUILD_DIR/rpm"
    local spec_file="$rpm_dir/$PACKAGE_NAME.spec"

    mkdir -p "$rpm_dir"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

    # Create source tarball
    cd "$PROJECT_ROOT"
    if ! tar -czf "$rpm_dir/SOURCES/${PACKAGE_NAME}-${PACKAGE_VERSION}.tar.gz" \
        --exclude='.git' \
        --exclude='build' \
        --exclude='dist' \
        --exclude='packages' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        .; then
        print_error "Failed to create source tarball"
        exit 1
    fi

    # Create spec file
    cat > "$spec_file" << EOF
Name:           $PACKAGE_NAME
Version:        $PACKAGE_VERSION
Release:        1%{?dist}
Summary:        $DESCRIPTION
License:        $LICENSE
URL:            $HOMEPAGE
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

Requires:       python3 >= $REQUIRED_PYTHON_VERSION
Requires:       python3-pip

%description
$DESCRIPTION

%prep
%autosetup

%build
# Nothing to build

%install
mkdir -p %{buildroot}/opt/$PACKAGE_NAME
mkdir -p %{buildroot}/usr/local/bin

# Copy application files
cp -r src/* %{buildroot}/opt/$PACKAGE_NAME/

# Create wrapper script
cat > %{buildroot}/usr/local/bin/$PACKAGE_NAME << 'WRAPPER_EOF'
#!/bin/bash
export PYTHONPATH="/opt/$PACKAGE_NAME:\$PYTHONPATH"
python3 -m python_dev_tool.cli.main "\$@"
WRAPPER_EOF
chmod +x %{buildroot}/usr/local/bin/$PACKAGE_NAME

%files
/opt/$PACKAGE_NAME/*
/usr/local/bin/$PACKAGE_NAME

%post
# Create symlinks
ln -sf /usr/local/bin/$PACKAGE_NAME /usr/bin/$PACKAGE_NAME
ln -sf /usr/local/bin/$PACKAGE_NAME /usr/bin/pdt
ln -sf /usr/local/bin/$PACKAGE_NAME /usr/bin/devtool

%preun
# Remove symlinks
rm -f /usr/bin/$PACKAGE_NAME
rm -f /usr/bin/pdt
rm -f /usr/bin/devtool

%changelog
* $(date +'%a %b %d %Y') $MAINTAINER - $PACKAGE_VERSION-1
- Initial package
EOF

    # Build RPM
    if ! rpmbuild --define "_topdir $rpm_dir" -ba "$spec_file"; then
        print_error "Failed to build RPM package"
        exit 1
    fi

    # Copy built RPM to packages directory
    cp "$rpm_dir/RPMS/noarch/"*.rpm "$PACKAGES_DIR/"

    print_success "RPM package built successfully"
}

build_arch() {
    print_step "Building Arch Linux package..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would build Arch Linux package"
        return 0
    fi

    if ! command -v makepkg >/dev/null 2>&1; then
        print_warning "makepkg not available, skipping Arch Linux package"
        return 0
    fi

    local arch_dir="$BUILD_DIR/arch"
    local pkgbuild_file="$arch_dir/PKGBUILD"

    mkdir -p "$arch_dir"

    # Create PKGBUILD
    cat > "$pkgbuild_file" << EOF
# Maintainer: $MAINTAINER
pkgname=$PACKAGE_NAME
pkgver=$PACKAGE_VERSION
pkgrel=1
pkgdesc="$DESCRIPTION"
arch=('any')
url="$HOMEPAGE"
license=('$LICENSE')
depends=('python>=$REQUIRED_PYTHON_VERSION' 'python-pip')
makedepends=('python-build' 'python-installer' 'python-wheel')
source=("https://github.com/yourusername/$PACKAGE_NAME/archive/v\$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "\$srcdir/$PACKAGE_NAME-\$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "\$srcdir/$PACKAGE_NAME-\$pkgver"
    python -m installer --destdir="\$pkgdir" dist/*.whl

    # Install license
    install -Dm644 LICENSE "\$pkgdir/usr/share/licenses/\$pkgname/LICENSE"

    # Create symlinks
    mkdir -p "\$pkgdir/usr/bin"
    ln -sf /usr/bin/$PACKAGE_NAME "\$pkgdir/usr/bin/pdt"
    ln -sf /usr/bin/$PACKAGE_NAME "\$pkgdir/usr/bin/devtool"
}
EOF

    cd "$arch_dir"

    # Build package
    if ! makepkg -sf; then
        print_error "Failed to build Arch Linux package"
        exit 1
    fi

    # Copy built package to packages directory
    cp *.pkg.tar.* "$PACKAGES_DIR/"

    print_success "Arch Linux package built successfully"
}

build_macos() {
    print_step "Building macOS package..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would build macOS package"
        return 0
    fi

    local macos_dir="$BUILD_DIR/macos"
    local app_dir="$macos_dir/$PACKAGE_NAME"

    mkdir -p "$app_dir/usr/local/bin" "$app_dir/opt/$PACKAGE_NAME"

    # Copy application files
    cp -r "$PROJECT_ROOT/src/"* "$app_dir/opt/$PACKAGE_NAME/"

    # Create wrapper script
    cat > "$app_dir/usr/local/bin/$PACKAGE_NAME" << 'EOF'
#!/bin/bash
export PYTHONPATH="/opt/$PACKAGE_NAME:$PYTHONPATH"
python3 -m python_dev_tool.cli.main "$@"
EOF
    chmod +x "$app_dir/usr/local/bin/$PACKAGE_NAME"

    # Create installer script
    cat > "$macos_dir/install.sh" << 'EOF'
#!/bin/bash
set -e

echo "Installing $PACKAGE_NAME..."

# Check if Python 3.8+ is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python $REQUIRED_PYTHON_VERSION+ is required but not installed."
    echo "Please install Python from https://python.org or use Homebrew: brew install python"
    exit 1
fi

# Copy files
sudo cp -r opt/$PACKAGE_NAME /opt/
sudo cp usr/local/bin/$PACKAGE_NAME /usr/local/bin/

# Create symlinks
sudo ln -sf /usr/local/bin/$PACKAGE_NAME /usr/local/bin/pdt
sudo ln -sf /usr/local/bin/$PACKAGE_NAME /usr/local/bin/devtool

echo "$PACKAGE_NAME installed successfully!"
echo "You can now use '$PACKAGE_NAME', 'pdt', or 'devtool' commands."
EOF
    chmod +x "$macos_dir/install.sh"

    # Create tarball
    cd "$macos_dir"
    if ! tar -czf "$PACKAGES_DIR/${PACKAGE_NAME}-${PACKAGE_VERSION}-macos.tar.gz" "$PACKAGE_NAME" install.sh; then
        print_error "Failed to create macOS package"
        exit 1
    fi

    print_success "macOS package built successfully"
}

build_windows() {
    print_step "Building Windows package..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would build Windows package"
        return 0
    fi

    local windows_dir="$BUILD_DIR/windows"
    mkdir -p "$windows_dir"

    # Create PowerShell installer script
    cat > "$windows_dir/install.ps1" << EOF
# PowerShell installer for $PACKAGE_NAME
param(
    [switch]\$Force = \$false,
    [string]\$InstallPath = "\$env:LOCALAPPDATA\\$PACKAGE_NAME"
)

Write-Host "Installing $PACKAGE_NAME..." -ForegroundColor Green

# Check if Python is available
try {
    \$pythonVersion = python --version 2>&1
    Write-Host "Found Python: \$pythonVersion" -ForegroundColor Blue
} catch {
    Write-Host "Error: Python $REQUIRED_PYTHON_VERSION+ is required but not found." -ForegroundColor Red
    Write-Host "Please install Python from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Install via pip
try {
    if (\$Force) {
        pip install --upgrade $PACKAGE_NAME
    } else {
        pip install $PACKAGE_NAME
    }
    Write-Host "Successfully installed $PACKAGE_NAME via pip" -ForegroundColor Green
} catch {
    Write-Host "Error: Failed to install $PACKAGE_NAME via pip" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installation completed successfully!" -ForegroundColor Green
Write-Host "You can now use '$PACKAGE_NAME' command in your terminal." -ForegroundColor Blue
EOF

    # Create ZIP package
    cd "$windows_dir"
    if ! zip -r "$PACKAGES_DIR/${PACKAGE_NAME}-${PACKAGE_VERSION}-windows.zip" install.ps1; then
        print_error "Failed to create Windows package"
        exit 1
    fi

    print_success "Windows package built successfully"
}

# ==============================================================================
# PUBLICATION
# ==============================================================================

publish_pypi() {
    print_step "Publishing to PyPI..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would publish to PyPI"
        return 0
    fi

    cd "$PROJECT_ROOT"

    # Check if twine is available
    if ! command -v twine >/dev/null 2>&1; then
        print_error "twine not found. Please install it with: pip install twine"
        exit 1
    fi

    # Check if we have credentials
    if [ -z "$PYPI_USERNAME" ] || [ -z "$PYPI_PASSWORD" ]; then
        print_error "PyPI credentials not set. Please set PYPI_USERNAME and PYPI_PASSWORD"
        exit 1
    fi

    # Upload package
    if ! twine upload "$DIST_DIR"/*; then
        print_error "Failed to upload to PyPI"
        exit 1
    fi

    print_success "Package published to PyPI successfully"
}

publish_github() {
    print_step "Creating GitHub release..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would create GitHub release"
        return 0
    fi

    # Check if gh is available
    if ! command -v gh >/dev/null 2>&1; then
        print_error "GitHub CLI (gh) not found. Please install it first."
        exit 1
    fi

    # Check if we're authenticated
    if ! gh auth status >/dev/null 2>&1; then
        print_error "Not authenticated with GitHub. Please run 'gh auth login'"
        exit 1
    fi

    # Create release
    if ! gh release create "v$PACKAGE_VERSION" "$PACKAGES_DIR"/* \
        --title "v$PACKAGE_VERSION" \
        --notes "Release $PACKAGE_VERSION of $PACKAGE_NAME"; then
        print_error "Failed to create GitHub release"
        exit 1
    fi

    print_success "GitHub release created successfully"
}

publish_system_repos() {
    print_step "Updating system package repositories..."

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would update system package repositories"
        return 0
    fi

    # APT repository
    if [ -f "$PACKAGES_DIR"/*.deb ]; then
        mkdir -p "$REPO_DIR/apt"
        cp "$PACKAGES_DIR"/*.deb "$REPO_DIR/apt/"
        cd "$REPO_DIR/apt"
        dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz
        print_success "APT repository updated"
    fi

    # YUM repository
    if [ -f "$PACKAGES_DIR"/*.rpm ]; then
        mkdir -p "$REPO_DIR/yum"
        cp "$PACKAGES_DIR"/*.rpm "$REPO_DIR/yum/"
        cd "$REPO_DIR/yum"
        createrepo .
        print_success "YUM repository updated"
    fi

    print_success "System package repositories updated"
}

# ==============================================================================
# MAIN PUBLICATION FLOW
# ==============================================================================

pre_publication_checks() {
    print_step "Running pre-publication checks..."

    # Check if we're in the right directory
    if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
        print_error "Not in project root directory"
        exit 1
    fi

    # Check if git is clean
    if ! git diff --quiet || ! git diff --cached --quiet; then
        print_error "Git working directory is not clean"
        print_error "Please commit all changes before publishing"
        exit 1
    fi

    # Check if on main branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
        print_warning "Not on main/master branch (current: $current_branch)"
        if [ "$FORCE" = false ]; then
            print_error "Use --force to publish from non-main branch"
            exit 1
        fi
    fi

    # Check if version tag already exists
    if git tag -l | grep -q "^v$PACKAGE_VERSION$"; then
        print_warning "Version tag v$PACKAGE_VERSION already exists"
        if [ "$FORCE" = false ]; then
            print_error "Use --force to overwrite existing tag"
            exit 1
        fi
    fi

    # Check required tools
    local required_tools=("python3" "pip" "git")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            print_error "Required tool not found: $tool"
            exit 1
        fi
    done

    print_success "Pre-publication checks passed"
}

build_all_packages() {
    print_step "Building all packages..."

    setup_build_env
    update_version "$PACKAGE_VERSION"
    run_tests
    build_wheel

    # Build system-specific packages
    case "$OS" in
        "Linux")
            build_deb
            build_rpm
            build_arch
            ;;
        "macOS")
            build_macos
            ;;
        "Windows")
            build_windows
            ;;
    esac

    print_header "Package building completed!"
    print_status "Built packages:"
    ls -la "$PACKAGES_DIR"
}

publish_all() {
    print_step "Publishing to all targets..."

    case "$PUBLISH_TARGET" in
        "pypi")
            publish_pypi
            ;;
        "github")
            publish_github
            ;;
        "system")
            publish_system_repos
            ;;
        "all")
            publish_pypi
            publish_github
            publish_system_repos
            ;;
        *)
            print_error "Invalid publish target: $PUBLISH_TARGET"
            exit 1
            ;;
    esac

    print_success "Publication completed successfully!"
}

show_next_steps() {
    if [ "$QUIET" = false ]; then
        echo
        print_fancy_banner

        echo -e "${COLORS[SUCCESS]}${EMOJIS[PARTY]} Publication completed successfully! ${EMOJIS[PARTY]}${COLORS[RESET]}"
        echo

        echo -e "${COLORS[BOLD]}${EMOJIS[ROCKET]} Next Steps:${COLORS[RESET]}"
        echo -e "  ${COLORS[FUSE_CYAN]}1.${COLORS[RESET]} Verify the release:"
        echo -e "     ${COLORS[MUTED]}${EMOJIS[SEARCH]} PyPI:${COLORS[RESET]} https://pypi.org/project/$PACKAGE_NAME/"
        echo -e "     ${COLORS[MUTED]}${EMOJIS[SEARCH]} GitHub:${COLORS[RESET]} https://github.com/$GITHUB_REPO/releases"
        echo -e "  ${COLORS[FUSE_CYAN]}2.${COLORS[RESET]} Update documentation if needed"
        echo -e "  ${COLORS[FUSE_CYAN]}3.${COLORS[RESET]} Announce the new release to your users"
        echo

        echo -e "${COLORS[MUTED]}${EMOJIS[HEART]} Thank you for using FUSE! ${EMOJIS[HEART]}${COLORS[RESET]}"
        echo
    fi
}

# ==============================================================================
# USAGE & HELP
# ==============================================================================

show_usage() {
    cat << EOF
${COLORS[BOLD]}${EMOJIS[ROCKET]} FUSE Universal Publisher v$SCRIPT_VERSION${COLORS[RESET]}

${COLORS[BOLD]}USAGE:${COLORS[RESET]}
    $0 [OPTIONS] VERSION

${COLORS[BOLD]}DESCRIPTION:${COLORS[RESET]}
    Build and publish FUSE (Python Development Tool) packages
    Compatible with Linux, macOS, and Windows systems

${COLORS[BOLD]}ARGUMENTS:${COLORS[RESET]}
    VERSION                Version to publish (e.g., 1.0.0)

${COLORS[BOLD]}OPTIONS:${COLORS[RESET]}
    -t, --target TARGET    Publication target: pypi, github, system, all (default: all)
    -d, --dry-run          Dry run mode (don't actually publish)
    -f, --force            Force publication even if version exists
    -v, --verbose          Verbose output
    -q, --quiet            Suppress non-essential output
    --skip-tests           Skip running tests before building
    -h, --help             Show this help message
    --version              Show version information

${COLORS[BOLD]}EXAMPLES:${COLORS[RESET]}
    $0 1.0.0                    # Publish version 1.0.0 to all targets
    $0 -t pypi 1.0.0           # Publish only to PyPI
    $0 -d 1.0.0                # Dry run
    $0 -f 1.0.0                # Force publish even if version exists

${COLORS[BOLD]}REQUIREMENTS:${COLORS[RESET]}
    ${COLORS[MUTED]}•${COLORS[RESET]} Python ${REQUIRED_PYTHON_VERSION}+ with pip
    ${COLORS[MUTED]}•${COLORS[RESET]} Git
    ${COLORS[MUTED]}•${COLORS[RESET]} Appropriate build tools for each target

${COLORS[MUTED]}For more information, visit: $HOMEPAGE${COLORS[RESET]}

EOF
}

show_version() {
    echo -e "${COLORS[BOLD]}${EMOJIS[ROCKET]} FUSE Universal Publisher${COLORS[RESET]}"
    echo -e "${COLORS[MUTED]}Version: $SCRIPT_VERSION${COLORS[RESET]}"
    echo -e "${COLORS[MUTED]}Target: $PACKAGE_NAME${COLORS[RESET]}"
    echo -e "${COLORS[MUTED]}Python: ${REQUIRED_PYTHON_VERSION}+${COLORS[RESET]}"
}

# ==============================================================================
# ARGUMENT PARSING
# ==============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--target)
                PUBLISH_TARGET="$2"
                if [[ ! "$PUBLISH_TARGET" =~ ^(pypi|github|system|all)$ ]]; then
                    print_error "Invalid publication target: $PUBLISH_TARGET"
                    print_info "Valid targets: pypi, github, system, all"
                    exit 1
                fi
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE=true
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
            --skip-tests)
                SKIP_TESTS=true
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
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [ -z "$PACKAGE_VERSION" ]; then
                    PACKAGE_VERSION="$1"
                else
                    print_error "Too many arguments"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Validate version format
    if [ -z "$PACKAGE_VERSION" ]; then
        print_error "Version is required"
        show_usage
        exit 1
    fi

    if ! echo "$PACKAGE_VERSION" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$' >/dev/null; then
        print_error "Invalid version format: $PACKAGE_VERSION"
        print_error "Expected format: X.Y.Z or X.Y.Z-suffix"
        exit 1
    fi

    # Validate conflicting options
    if [ "$VERBOSE" = true ] && [ "$QUIET" = true ]; then
        print_error "Cannot use --verbose and --quiet together"
        exit 1
    fi
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

main() {
    print_header
    detect_system
    parse_arguments "$@"
    pre_publication_checks
    build_all_packages
    publish_all
    show_next_steps
}

# Only run main if script is executed directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
