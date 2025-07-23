# -------------------------------------------------------------
# Makefile for FUSE (python dev tool)
# -------------------------------------------------------------
# Author: Enos Muthiani <emuthiani26@gmail.com>

# Palette
RESET   := \033[0m
BOLD    := \033[1m
ITALIC  := \033[3m

# 256 Colors
EMERALD := \033[38;5;35m
GREEN   := \033[38;5;34m
CRIMSON := \033[38;5;197m
ORANGE  := \033[38;5;208m
SLATE   := \033[38;5;240m
PURPLE  := \033[38;5;129m
BLUE    := \033[38;5;33m

# 🎯 Emoji variables
EMOJI_ROCKET      := 🚀
EMOJI_DEV         := 🛠️
EMOJI_WATCH       := 🔁
EMOJI_CLI         := 💬
EMOJI_BUILD       := 🧱
EMOJI_RELEASE     := 🚀
EMOJI_TEST        := 🧪
EMOJI_LINT        := 🔍
EMOJI_FORMAT      := 🎨
EMOJI_DEPLOY      := 🚢
EMOJI_DOCS        := 📚
EMOJI_BENCHMARK   := 📊
EMOJI_CLEAN       := 🧹
EMOJI_SUCCESS     := ✅
EMOJI_ERROR       := ❌
EMOJI_WARNING     := ⚠️
EMOJI_PUBLISH     := 📦
EMOJI_VERSION     := 🏷️
EMOJI_LOCAL       := 🏠

# Simple ASCII alternatives
# EMOJI_ROCKET      := [*]
# EMOJI_DEV         := [+]
# EMOJI_WATCH       := [~]
# EMOJI_CLI         := [>]
# EMOJI_BUILD       := [#]
# EMOJI_SUCCESS     := [✓]
# EMOJI_ERROR       := [✗]

# Default variables
PORT ?= 8000
TEST_FILE ?= tests/
SCRIPT_FILE ?= scripts/


## Default target
.DEFAULT_GOAL := help

## Help
.PHONY: help
help:
	@echo -e ""
	@echo -e "$(BOLD)$(EMOJI_ROCKET) Fuse: Python Dev Tool - Developer CLI$(RESET)"
	@echo -e "$(SLATE)────────────────────────────────────────────────────$(RESET)"
	@echo -e "$(BOLD)$(EMERALD)[ Development Commands ]$(RESET)"
	@echo -e "  $(GREEN)make dev$(RESET)              $(EMOJI_DEV) Start dev server with live reload"
	@echo -e "  $(GREEN)make watch$(RESET)            $(EMOJI_WATCH) Watch files & reload on changes"
	@echo -e "  $(GREEN)make cli$(RESET)              $(EMOJI_CLI) Run CLI in interactive mode"
	@echo -e "  $(GREEN)make local-build$(RESET)      $(EMOJI_LOCAL) Build and install tool locally for testing"

	@echo -e "$(BOLD)$(EMERALD)[ Build & Release ]$(RESET)"
	@echo -e "  $(ORANGE)make build$(RESET)           $(EMOJI_BUILD) Build the package"
	@echo -e "  $(ORANGE)make release$(RESET)         $(EMOJI_RELEASE) Create new release"
	@echo -e "  $(ORANGE)make hatch-build$(RESET)     $(EMOJI_BUILD) Build package with hatch"
	@echo -e "  $(ORANGE)make hatch-publish$(RESET)   $(EMOJI_PUBLISH) Publish package with hatch"

	@echo -e "$(BOLD)$(EMERALD)[ Version Management ]$(RESET)"
	@echo -e "  $(PURPLE)make version$(RESET)         $(EMOJI_VERSION) Show current version"
	@echo -e "  $(PURPLE)make version-patch$(RESET)   $(EMOJI_VERSION) Bump patch version (1.0.0 -> 1.0.1)"
	@echo -e "  $(PURPLE)make version-minor$(RESET)   $(EMOJI_VERSION) Bump minor version (1.0.1 -> 1.1.0)"
	@echo -e "  $(PURPLE)make version-major$(RESET)   $(EMOJI_VERSION) Bump major version (1.1.0 -> 2.0.0)"
	@echo -e "  $(PURPLE)make version-set VER=x.y.z$(RESET) $(EMOJI_VERSION) Set specific version"

	@echo -e "$(BOLD)$(EMERALD)[ Testing & QA ]$(RESET)"
	@echo -e "  $(CRIMSON)make test$(RESET)           $(EMOJI_TEST) Run unit + integration tests"
	@echo -e "  $(CRIMSON)make test TEST_FILE=path$(RESET) $(EMOJI_TEST) Run specific test file"
	@echo -e "  $(CRIMSON)make lint$(RESET)           $(EMOJI_LINT) Run ruff linter + type check"
	@echo -e "  $(CRIMSON)make ruff-check$(RESET)     $(EMOJI_LINT) Run ruff check on current directory"
	@echo -e "  $(CRIMSON)make format$(RESET)         $(EMOJI_FORMAT) Auto-format using ruff"

	@echo -e "$(BOLD)$(EMERALD)[ Deploy & Docs ]$(RESET)"
	@echo -e "  $(PURPLE)make deploy$(RESET)          $(EMOJI_DEPLOY) Deploy to configured platform"
	@echo -e "  $(BLUE)make docs$(RESET)            $(EMOJI_DOCS) Serve documentation (default port 8000)"
	@echo -e "  $(BLUE)make docs PORT=8080$(RESET)  $(EMOJI_DOCS) Serve docs on custom port"

	@echo -e "$(BOLD)$(EMERALD)[ Benchmarks & Maintenance ]$(RESET)"
	@echo -e "  $(SLATE)make benchmark$(RESET)        $(EMOJI_BENCHMARK) Run performance benchmarks"
	@echo -e "  $(SLATE)make clean$(RESET)            $(EMOJI_CLEAN) Remove build artifacts"
	@echo -e ""

	@echo -e "$(BOLD)$(EMERALD)[ Scripts ]$(RESET)"
	@echo -e "  $(PURPLE)make install$(RESET)         $(EMOJI_CLI) run script to install python-dev-tool"
	@echo -e "  $(CRIMSON)make script SCRIPT_FILE=path$(RESET) $(EMOJI_RELEASE) Run specific script file"
	@echo -e ""
	@echo -e "$(SLATE)Run $(BOLD)make <command>$(RESET)$(SLATE) to execute any command$(RESET)"
# -------------------------------------
#  Development
# -------------------------------------

.PHONY: dev
dev:
	@echo -e "$(GREEN)$(EMOJI_DEV) Starting dev server...$(RESET)"
	@python scripts/setup.py --dev

.PHONY: watch
watch:
	@echo -e "$(GREEN)$(EMOJI_WATCH) Watching files...$(RESET)"
	@python scripts/setup.py --watch

.PHONY: cli
cli:
	@echo -e "$(GREEN)$(EMOJI_CLI) Running interactive CLI...$(RESET)"
	@python src/python_dev_tool/cli/main.py

.PHONY: local-build
local-build:
	@echo -e "$(GREEN)$(EMOJI_LOCAL) Building and installing tool locally for testing...$(RESET)"
	@pip install -e . || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Local build failed!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Local build and installation complete!$(RESET)"
	@echo -e "$(BLUE)$(EMOJI_CLI) You can now test the tool locally$(RESET)"

# -------------------------------------
#  Build & Release
# -------------------------------------

.PHONY: build
build:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building project...$(RESET)"
	@python scripts/build.py
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Build completed successfully!$(RESET)"

.PHONY: hatch-build
hatch-build:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building package with hatch...$(RESET)"
	@hatch build || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Hatch build failed!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Hatch build completed successfully!$(RESET)"

.PHONY: hatch-publish
hatch-publish:
	@echo -e "$(ORANGE)$(EMOJI_PUBLISH) Publishing package with hatch...$(RESET)"
	@hatch publish || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Hatch publish failed!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Package published successfully!$(RESET)"

.PHONY: release
release:
	@echo -e "$(ORANGE)$(EMOJI_RELEASE) Releasing new version...$(RESET)"
	@python scripts/release.py
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Release created successfully!$(RESET)"

# -------------------------------------
#  Version Management
# -------------------------------------

.PHONY: version
version:
	@echo -e "$(PURPLE)$(EMOJI_VERSION) Current version:$(RESET)"
	@hatch version

.PHONY: version-patch
version-patch:
	@echo -e "$(PURPLE)$(EMOJI_VERSION) Bumping patch version...$(RESET)"
	@hatch version patch
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Version bumped to: $$(hatch version)$(RESET)"

.PHONY: version-minor
version-minor:
	@echo -e "$(PURPLE)$(EMOJI_VERSION) Bumping minor version...$(RESET)"
	@hatch version minor
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Version bumped to: $$(hatch version)$(RESET)"

.PHONY: version-major
version-major:
	@echo -e "$(PURPLE)$(EMOJI_VERSION) Bumping major version...$(RESET)"
	@hatch version major
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Version bumped to: $$(hatch version)$(RESET)"

.PHONY: version-set
version-set:
ifndef VER
	@echo -e "$(CRIMSON)$(EMOJI_ERROR) Please specify version: make version-set VER=1.2.3$(RESET)"
	@exit 1
endif
	@echo -e "$(PURPLE)$(EMOJI_VERSION) Setting version to $(VER)...$(RESET)"
	@hatch version "$(VER)"
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Version set to: $$(hatch version)$(RESET)"

# -------------------------------------
#   Tests and Linting
# -------------------------------------

.PHONY: test
test:
	@echo -e "$(CRIMSON)$(EMOJI_TEST) Running tests on $(TEST_FILE)...$(RESET)"
	@pytest $(TEST_FILE) || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Tests failed!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Tests passed!$(RESET)"

.PHONY: lint
lint:
	@echo -e "$(CRIMSON)$(EMOJI_LINT) Linting with ruff...$(RESET)"
	@ruff check src/ tests/ || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Linting failed!$(RESET)" && exit 1)
	@echo -e "$(CRIMSON)$(EMOJI_LINT) Type checking with mypy...$(RESET)"
	@mypy src/ || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Type checking failed!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Linting and type checking passed!$(RESET)"

.PHONY: ruff-check
ruff-check:
	@echo -e "$(CRIMSON)$(EMOJI_LINT) Running ruff check on current directory...$(RESET)"
	@ruff check . || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Ruff check failed!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Ruff check passed!$(RESET)"

.PHONY: format
format:
	@echo -e "$(CRIMSON)$(EMOJI_FORMAT) Formatting with ruff...$(RESET)"
	@ruff format src/ tests/
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Formatting complete!$(RESET)"

# -------------------------------------
#   Deploy & Docs
# -------------------------------------

.PHONY: deploy
deploy:
	@echo -e "$(PURPLE)$(EMOJI_DEPLOY) Deploying...$(RESET)"
	@python scripts/deploy.py
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Deployment successful!$(RESET)"

.PHONY: docs
docs:
	@echo -e "$(BLUE)$(EMOJI_DOCS) Serving documentation on port $(PORT)...$(RESET)"
	@mkdocs serve --dev-addr=localhost:$(PORT)

# -------------------------------------
#   Benchmarks & Cleanup
# -------------------------------------

.PHONY: benchmark
benchmark:
	@echo -e "$(SLATE)$(EMOJI_BENCHMARK) Running benchmarks...$(RESET)"
	@python scripts/benchmark.py
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Benchmarking complete!$(RESET)"

.PHONY: clean
clean:
	@echo -e "$(SLATE)$(EMOJI_CLEAN) Cleaning build artifacts...$(RESET)"
	@rm -rf build dist __pycache__ *.egg-info .pytest_cache .mypy_cache .coverage htmlcov .ruff_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Cleanup complete!$(RESET)"

# -------------------------------------
#   Publish & Release
# -------------------------------------

.PHONY: publish
publish:
	@echo -e "$(PURPLE)$(EMOJI_PUBLISH) Publishing new version...$(RESET)"
	@python scripts/publish.sh
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Release created successfully!$(RESET)"


# -------------------------------------
#   Scripts File Running Commands
# -------------------------------------

.PHONY: install
install:
	@echo -e "$(PURPLE)$(EMOJI_CLI) Installing python-dev-tool...$(RESET)"
	@${SCRIPT_FILE}install.sh
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Installation completed successfully!$(RESET)"
	@echo -e "$(PURPLE)$(EMOJI_CLI) Running post-installation setup...$(RESET)"

.PHONY: script
script:
	@echo -e "$(PURPLE)$(EMOJI_CLI) Running script: $(SCRIPT_FILE)$(RESET)"
	@${SCRIPT_FILE}$(SCRIPT_FILE)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Script completed successfully!$(RESET)"
