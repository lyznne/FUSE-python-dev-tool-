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
YELLOW  := \033[38;5;226m
CYAN    := \033[38;5;51m

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
EMOJI_NETWORK     := 🌐
EMOJI_UI          := 🎛️
EMOJI_DEBUG       := 🐛
EMOJI_DOCTOR      := 🏥
EMOJI_DEMO        := 🎬
EMOJI_FAST        := ⚡

# Simple ASCII alternatives
# EMOJI_ROCKET      := [*]
# EMOJI_DEV         := [+]
# EMOJI_WATCH       := [~]
# EMOJI_CLI         := [>]
# EMOJI_BUILD       := [#]
# EMOJI_SUCCESS     := [✓]
# EMOJI_ERROR       := [✗]

# Default variables
PORT ?= 8001
TEST_FILE ?= tests/
SCRIPT_FILE ?= scripts/
SRC_DIR := src
VENV_DIR := .fuse_env

# Repository Configuration
GITHUB_ORG := fuse-dev-tool
REPOS := core cli ui docs plugins templates releases community

# Git remote URLs
REMOTE_CORE := git@github.com:$(GITHUB_ORG)/fuse-core.git
REMOTE_CLI := git@github.com:$(GITHUB_ORG)/fuse-cli.git
REMOTE_UI := git@github.com:$(GITHUB_ORG)/fuse-ui.git
REMOTE_DOCS := git@github.com:$(GITHUB_ORG)/fuse-docs.git
REMOTE_PLUGINS := git@github.com:$(GITHUB_ORG)/fuse-plugins.git
REMOTE_TEMPLATES := git@github.com:$(GITHUB_ORG)/fuse-templates.git
REMOTE_COMMUNITY := git@github.com:$(GITHUB_ORG)/fuse-community.git



## Default target
.DEFAULT_GOAL := help

## Help
.PHONY: help
help:
	@echo -e ""
	@echo -e "$(BOLD)$(EMOJI_ROCKET) Fuse: Python Dev Tool - Developer CLI$(RESET)"
	@echo -e "$(SLATE)────────────────────────────────────────────────────$(RESET)"
	@echo -e "$(BOLD)$(EMERALD)[ Development Commands ]$(RESET)"
	@echo -e "  $(GREEN)make dev$(RESET)                       $(EMOJI_DEV) Start dev server with live reload"
	@echo -e "  $(GREEN)make dev-debug$(RESET)                 $(EMOJI_DEBUG) Start dev server with debug logging"
	@echo -e "  $(GREEN)make dev-clean$(RESET)                 $(EMOJI_CLEAN) Start dev server with clean environment"
	@echo -e "  $(GREEN)make dev-ui-only$(RESET)               $(EMOJI_UI) Start only the development UI"
	@echo -e "  $(GREEN)make watch$(RESET)                     $(EMOJI_WATCH) Watch files & reload on changes"
	@echo -e "  $(GREEN)make cli$(RESET)                       $(EMOJI_CLI) Run CLI in interactive mode"
	@echo -e "  $(GREEN)make local-build$(RESET)               $(EMOJI_LOCAL) Build and install tool locally for testing"


	@echo -e "$(BOLD)$(EMERALD)[ Git & Remote Repo Management ]$(RESET)"
	@echo -e "  $(YELLOW)make git-init-repos$(RESET)           $(EMOJI_DEV) Initialize Git repositories"
	@echo -e "  $(YELLOW)make git-check-subtrees$(RESET)       $(EMOJI_LOCAL) Check Git subtree paths"
	@echo -e "  $(YELLOW)make git-commit-current$(RESET)       $(EMOJI_LOCAL) Commit current state"
	@echo -e "  $(YELLOW)make git-setup-remotes$(RESET)        $(EMOJI_LOCAL) Setting up Git remotes"
	@echo -e "  $(YELLOW)make git-push-core$(RESET)            $(EMOJI_BUILD) Pushing Core module"
	@echo -e "  $(YELLOW)make git-push-cli$(RESET)             $(EMOJI_PUBLISH) Pushing CLI module"
	@echo -e "  $(YELLOW)make git-push-ui$(RESET)              $(EMOJI_BUILD) Pushing UI module"
	@echo -e "  $(YELLOW)make git-push-docs$(RESET)            $(EMOJI_PUBLISH) Pushing documentation"
	@echo -e "  $(YELLOW)make git-push-plugins$(RESET)         $(EMOJI_BUILD) Pushing FUSE Plugins"
	@echo -e "  $(YELLOW)make git-push-templates$(RESET)       $(EMOJI_BUILD) Pushing templates code"
	@echo -e "  $(YELLOW)make git-push-community$(RESET)       $(EMOJI_BUILD) Pushing FUSE Community code"
	@echo -e "  $(YELLOW)make git-push-all$(RESET)             $(EMOJI_ROCKET) Pushing to all repositories"
	@echo -e "  $(YELLOW)make git-pull-all$(RESET)             $(EMOJI_WATCH) Pulling from all repositories"
	@echo -e "  $(YELLOW)make git-status-all$(RESET)           $(EMOJI_FAST) Check Git status of all repositories"


	@echo -e "$(BOLD)$(EMERALD)[ Testing Commands ]$(RESET)"
	@echo -e "  $(CYAN)make test-app$(RESET)                  $(EMOJI_TEST) Test FUSE application components only"
	@echo -e "  $(CYAN)make test-ui$(RESET)                   $(EMOJI_UI) Test development UI components only"
	@echo -e "  $(CYAN)make test-network$(RESET)              $(EMOJI_NETWORK) Test network utilities (ports, domains)"
	@echo -e "  $(CYAN)make test-integration$(RESET)          $(EMOJI_TEST) Run integration tests with real project"
	@echo -e "  $(CYAN)make test-ports$(RESET)                $(EMOJI_NETWORK) Test port detection and assignment"
	@echo -e "  $(CYAN)make quick-test$(RESET)                $(EMOJI_FAST) Run all quick component tests"

	@echo -e "$(BOLD)$(EMERALD)[ Build & Release ]$(RESET)"
	@echo -e "  $(ORANGE)make build$(RESET)                   $(EMOJI_BUILD) Build the package"
	@echo -e "  $(ORANGE)make release$(RESET)                 $(EMOJI_RELEASE) Create new release"
	@echo -e "  $(ORANGE)make hatch-build$(RESET)             $(EMOJI_BUILD) Build package with hatch"
	@echo -e "  $(ORANGE)make hatch-publish$(RESET)           $(EMOJI_PUBLISH) Publish package with hatch"
	@echo -e "  $(ORANGE)make release-prepare$(RESET)         $(EMOJI_RELEASE) Prepare a new release"
	@echo -e "  $(ORANGE)make release-build$(RESET)           $(EMOJI_BUILD) Build release packages"
	@echo -e "  $(ORANGE)make release-publish$(RESET)         $(EMOJI_PUBLISH) Publish Release"


	@echo -e "$(BOLD)$(EMERALD)[ Version Management ]$(RESET)"
	@echo -e "  $(PURPLE)make version$(RESET)                  $(EMOJI_VERSION) Show current version"
	@echo -e "  $(PURPLE)make version-patch$(RESET)            $(EMOJI_VERSION) Bump patch version (1.0.0 -> 1.0.1)"
	@echo -e "  $(PURPLE)make version-minor$(RESET)            $(EMOJI_VERSION) Bump minor version (1.0.1 -> 1.1.0)"
	@echo -e "  $(PURPLE)make version-major$(RESET)            $(EMOJI_VERSION) Bump major version (1.1.0 -> 2.0.0)"
	@echo -e "  $(PURPLE)make version-set VER=x.y.z$(RESET)    $(EMOJI_VERSION) Set specific version"

	@echo -e "$(BOLD)$(EMERALD)[ Testing & QA ]$(RESET)"
	@echo -e "  $(CRIMSON)make test$(RESET)                     $(EMOJI_TEST) Run unit + integration tests"
	@echo -e "  $(CRIMSON)make test TEST_FILE=path$(RESET)      $(EMOJI_TEST) Run specific test file"
	@echo -e "  $(CRIMSON)make lint$(RESET)                     $(EMOJI_LINT) Run ruff linter + type check"
	@echo -e "  $(CRIMSON)make ruff-check$(RESET)               $(EMOJI_LINT) Run ruff check on current directory"
	@echo -e "  $(CRIMSON)make format$(RESET)                   $(EMOJI_FORMAT) Auto-format using ruff"

	@echo -e "$(BOLD)$(EMERALD)[ Deploy & Docs ]$(RESET)"
	@echo -e "  $(PURPLE)make deploy$(RESET)                    $(EMOJI_DEPLOY) Deploy to configured platform"
	@echo -e "  $(BLUE)make docs$(RESET)                        $(EMOJI_DOCS) Serve documentation (default port 8000)"
	@echo -e "  $(BLUE)make docs PORT=8080$(RESET)              $(EMOJI_DOCS) Serve docs on custom port"
	@echo -e "  $(BLUE)make docs-build$(RESET)                  $(EMOJI_DOCS) Build static documentation site"
	@echo -e "  $(BLUE)make docs-publish$(RESET)                $(EMOJI_DOCS) Publish static documentation site"

	@echo -e "$(BOLD)$(EMERALD)[ Benchmarks & Maintenance ]$(RESET)"
	@echo -e "  $(SLATE)make benchmark$(RESET)                  $(EMOJI_BENCHMARK) Run performance benchmarks"
	@echo -e "  $(SLATE)make clean$(RESET)                      $(EMOJI_CLEAN) Remove build artifacts"
	@echo -e "  $(SLATE)make doctor$(RESET)                     $(EMOJI_DOCTOR) Run FUSE diagnostics"
	@echo -e "  $(SLATE)make demo$(RESET)                       $(EMOJI_DEMO) Create demo project and test FUSE"

	@echo -e "$(BOLD)$(EMERALD)[ Scripts ]$(RESET)"
	@echo -e "  $(PURPLE)make install$(RESET)                    $(EMOJI_CLI) run script to install python-dev-tool"
	@echo -e "  $(CRIMSON)make script SCRIPT_FILE=path$(RESET)   $(EMOJI_RELEASE) Run specific script file"
	@echo -e ""
	@echo -e "$(SLATE)Run $(BOLD)make <command>$(RESET)$(SLATE) to execute any command$(RESET)"


## help release
# -------------------------------------
#  Help for Release Commands
# -------------------------------------

.PHONY: help-release
help-release:
	@echo -e ""
	@echo -e "$(BOLD)$(EMOJI_ROCKET) FUSE Release Management$(RESET)"
	@echo -e "$(SLATE)────────────────────────────────────────────────────$(RESET)"
	@echo -e ""
	@echo -e "$(BOLD)$(EMERALD)[ Build Platform Packages ]$(RESET)"
	@echo -e "  $(GREEN)make build-arch$(RESET)           Build Arch Linux package"
	@echo -e "  $(GREEN)make build-deb$(RESET)            Build Debian/Ubuntu package"
	@echo -e "  $(GREEN)make build-rpm$(RESET)            Build RPM package"
	@echo -e "  $(GREEN)make build-windows$(RESET)        Build Windows package"
	@echo -e "  $(GREEN)make build-macos$(RESET)          Build macOS package"
	@echo -e "  $(GREEN)make build-all-platforms$(RESET)  Build for all platforms"
	@echo -e ""
	@echo -e "$(BOLD)$(EMERALD)[ Publish & Update ]$(RESET)"
	@echo -e "  $(ORANGE)make publish-arch$(RESET)         Publish Arch Linux package"
	@echo -e "  $(ORANGE)make publish-deb$(RESET)          Publish Debian/Ubuntu package"
	@echo -e "  $(ORANGE)make publish-rpm$(RESET)          Publish RPM package"
	@echo -e "  $(ORANGE)make publish-pypi$(RESET)         Publish to PyPI"
	@echo -e "  $(ORANGE)make publish-test-pypi$(RESET)    Publish to Test PyPI"
	@echo -e "  $(ORANGE)make update-homebrew$(RESET)      Update Homebrew formula"
	@echo -e ""
	@echo -e "$(BOLD)$(EMERALD)[ Release Workflow ]$(RESET)"
	@echo -e "  $(PURPLE)make release-check$(RESET)       Run pre-release checks"
	@echo -e "  $(PURPLE)make release-tag$(RESET)         Create release tag"
	@echo -e "  $(PURPLE)make release-notes$(RESET)       Generate release notes"
	@echo -e "  $(PURPLE)make release-github$(RESET)      Create GitHub release"
	@echo -e "  $(PURPLE)make release-full$(RESET)        Build all packages and release"
	@echo -e "  $(PURPLE)make release-prepare$(RESET)     Prepare a new release"
	@echo -e "  $(PURPLE)make release-build$(RESET)       Build release packages"
	@echo -e "  $(PURPLE)make release-publish$(RESET)     Publish Release"
	@echo -e ""

# -------------------------------------
#  Git Repository Management
# -------------------------------------

.PHONY: git-init-repos
git-init-repos:
	@echo -e "$(GREEN)$(EMOJI_ROCKET) Initializing Git repositories...$(RESET)"
	@for repo in $(REPOS); do \
		echo -e "$(BLUE)Initializing $$repo repository...$(RESET)"; \
		git subtree push --prefix=src/python_dev_tool/$$repo $(REMOTE_$$repo) main || true; \
	done

.PHONY: git-check-subtrees
git-check-subtrees:
	@echo -e "$(BLUE)$(EMOJI_NETWORK) Checking subtree paths...$(RESET)"
	@echo "Core path: src/python_dev_tool/core - $([ -d src/python_dev_tool/core ] && echo 'EXISTS' || echo 'MISSING')"
	@echo "CLI path: src/python_dev_tool/cli - $([ -d src/python_dev_tool/cli ] && echo 'EXISTS' || echo 'MISSING')"
	@echo "Web path: src/python_dev_tool/web - $([ -d src/python_dev_tool/web ] && echo 'EXISTS' || echo 'MISSING')"
	@echo "Docs path: docs - $([ -d docs ] && echo 'EXISTS' || echo 'MISSING')"
	@echo "Plugins path: src/python_dev_tool/plugins - $([ -d src/python_dev_tool/plugins ] && echo 'EXISTS' || echo 'MISSING')"
	@echo "Templates path: src/python_dev_tool/templates - $([ -d src/python_dev_tool/templates ] && echo 'EXISTS' || echo 'MISSING')"


.PHONY: git-commit-current
git-commit-current:
	@echo -e "$(GREEN)$(EMOJI_ROCKET) Committing current state...$(RESET)"
	@git add .
	@git commit -m "Prepare for subtree distribution" || echo "Nothing to commit"
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Current state committed!$(RESET)"

.PHONY: git-setup-remotes
git-setup-remotes:
	@echo -e "$(GREEN)$(EMOJI_NETWORK) Setting up Git remotes...$(RESET)"
	@git remote add core $(REMOTE_CORE) 2>/dev/null || true
	@git remote add cli $(REMOTE_CLI) 2>/dev/null || true
	@git remote add ui $(REMOTE_UI) 2>/dev/null || true
	@git remote add docs $(REMOTE_DOCS) 2>/dev/null || true
	@git remote add plugins $(REMOTE_PLUGINS) 2>/dev/null || true
	@git remote add templates $(REMOTE_TEMPLATES) 2>/dev/null || true
	@git remote add community $(REMOTE_COMMUNITY) 2>/dev/null || true
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Git remotes configured!$(RESET)"

.PHONY: git-push-core
git-push-core:
	@echo -e "$(GREEN)$(EMOJI_ROCKET) Pushing core module...$(RESET)"
	@git subtree push --prefix=src/python_dev_tool/core core main
	@git subtree push --prefix=src/python_dev_tool/frameworks core main
	@git subtree push --prefix=src/python_dev_tool/monitoring core main
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Core pushed successfully!$(RESET)"

.PHONY: git-push-community
git-push-community:
	@echo -e "$(GREEN)$(EMOJI_ROCKET) Pushing community module...$(RESET)"
	@git subtree push --prefix=src/python_dev_tool/community community main
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Community pushed successfully!$(RESET)"
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Community pushed successfully!$(RESET)"

.PHONY: git-push-cli
git-push-cli:
	@echo -e "$(GREEN)$(EMOJI_CLI) Pushing CLI module...$(RESET)"
	@git subtree push --prefix=src/python_dev_tool/cli cli main
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) CLI pushed successfully!$(RESET)"

.PHONY: git-push-ui
git-push-ui:
	@echo -e "$(GREEN)$(EMOJI_UI) Pushing UI module...$(RESET)"
	@git subtree push --prefix=src/python_dev_tool/web ui main
	@git subtree push --prefix=frontend ui main
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) UI pushed successfully!$(RESET)"

.PHONY: git-push-docs
git-push-docs:
	@echo -e "$(GREEN)$(EMOJI_DOCS) Pushing documentation...$(RESET)"
	@git subtree push --prefix=docs docs main
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Docs pushed successfully!$(RESET)"

.PHONY: git-push-plugins
git-push-plugins:
	@echo -e "$(GREEN)$(EMOJI_BUILD) Pushing plugins...$(RESET)"
	@git subtree push --prefix=src/python_dev_tool/plugins plugins main
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Plugins pushed successfully!$(RESET)"

.PHONY: git-push-templates
git-push-templates:
	@echo -e "$(GREEN)$(EMOJI_BUILD) Pushing templates...$(RESET)"
	@git subtree push --prefix=src/python_dev_tool/templates templates main
	@git subtree push --prefix=examples templates main
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Templates pushed successfully!$(RESET)"

.PHONY: git-push-all
git-push-all: git-push-core git-push-cli git-push-ui git-push-docs git-push-plugins git-push-templates
	@echo -e "$(GREEN)$(EMOJI_ROCKET) All repositories pushed successfully!$(RESET)"

.PHONY: git-pull-all
git-pull-all:
	@echo -e "$(GREEN)$(EMOJI_NETWORK) Pulling from all repositories...$(RESET)"
	@git subtree pull --prefix=src/python_dev_tool/core core main --strategy=subtree -X subtree
	@git subtree pull --prefix=src/python_dev_tool/cli cli main --strategy=subtree -X subtree
	@git subtree pull --prefix=src/python_dev_tool/web ui main --strategy=subtree -X subtree
	@git subtree pull --prefix=docs docs main --strategy=subtree -X subtree
	@git subtree pull --prefix=src/python_dev_tool/plugins plugins main --strategy=subtree -X subtree
	@git subtree pull --prefix=src/python_dev_tool/templates templates main --strategy=subtree -X subtree
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) All repositories pulled successfully!$(RESET)"

.PHONY: git-status-all
git-status-all:
	@echo -e "$(BLUE)$(EMOJI_NETWORK) Git status for all repositories...$(RESET)"
	@echo -e "$(YELLOW)Main repository:$(RESET)"
	@git status --short
	@for remote in core cli ui docs plugins templates; do \
		echo -e "$(YELLOW)$$remote repository:$(RESET)"; \
		git ls-remote --heads $$remote 2>/dev/null || echo "Remote not configured"; \
	done

# -------------------------------------
#  Release Management
# -------------------------------------

.PHONY: release-prepare
release-prepare:
	@echo -e "$(ORANGE)$(EMOJI_RELEASE) Preparing release...$(RESET)"
	@echo -e "$(BLUE)Running tests...$(RESET)"
	@make test
	@echo -e "$(BLUE)Running linting...$(RESET)"
	@make lint
	@echo -e "$(BLUE)Building documentation...$(RESET)"
	@make docs-build
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Release preparation complete!$(RESET)"

.PHONY: release-build
release-build:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building release packages...$(RESET)"
	@python scripts/build_release.py
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Release packages built!$(RESET)"

.PHONY: release-publish
release-publish:
	@echo -e "$(ORANGE)$(EMOJI_PUBLISH) Publishing release...$(RESET)"
	@python scripts/publish_release.py
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Release published!$(RESET)"

.PHONY: release-complete
release-complete: release-prepare release-build release-publish
	@echo -e "$(GREEN)$(EMOJI_ROCKET) Full release process completed!$(RESET)"



# -------------------------------------
#  Development
# -------------------------------------

.PHONY: dev
dev:
	@echo -e "$(GREEN)$(EMOJI_DEV) Starting dev server...$(RESET)"
	@PYTHONDONTWRITEBYTECODE=1 python -m python_dev_tool.cli.main dev

.PHONY: dev-debug
dev-debug:
	@echo -e "$(GREEN)$(EMOJI_DEBUG) Starting dev server with debug logging...$(RESET)"
	@PYTHONDONTWRITEBYTECODE=1 FUSE_DEBUG=1 python -m python_dev_tool.cli.main dev --debug

.PHONY: dev-clean
dev-clean:
	@echo -e "$(GREEN)$(EMOJI_CLEAN) Starting dev server with clean environment...$(RESET)"
	@rm -rf .fuse/logs/* 2>/dev/null || true
	@rm -rf __pycache__ **/__pycache__ 2>/dev/null || true
	@PYTHONDONTWRITEBYTECODE=1 python -m python_dev_tool.cli.main dev --debug

.PHONY: dev-ui-only
dev-ui-only:
	@echo -e "$(GREEN)$(EMOJI_UI) Starting FUSE Development UI only...$(RESET)"
	@DEVTOOL_PROJECT_PATH=$$(pwd) PYTHONDONTWRITEBYTECODE=1 python -m uvicorn python_dev_tool.web.app:create_dev_ui_app --factory --host 127.0.0.1 --port 8001 --reload

.PHONY: watch
watch:
	@echo -e "$(GREEN)$(EMOJI_WATCH) Watching files...$(RESET)"
	@python scripts/setup.py --watch

.PHONY: cli
cli:
	@echo -e "$(GREEN)$(EMOJI_CLI) Running interactive CLI...$(RESET)"
	@python src/python_dev_tool/cli/fuse.py

.PHONY: local-build
local-build:
	@echo -e "$(GREEN)$(EMOJI_LOCAL) Building and installing tool locally for testing...$(RESET)"
	@pip install -e . || (echo -e "$(CRIMSON)$(EMOJI_ERROR) Local build failed!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Local build and installation complete!$(RESET)"
	@echo -e "$(BLUE)$(EMOJI_CLI) You can now test the tool locally$(RESET)"

# -------------------------------------
#  Testing Commands
# -------------------------------------

.PHONY: test-app
test-app:
	@echo -e "$(CYAN)$(EMOJI_TEST) Testing FUSE application components...$(RESET)"
	@echo -e "$(SLATE)Testing DevCommand import...$(RESET)"
	@PYTHONDONTWRITEBYTECODE=1 python -c "\
	import sys; \
	sys.path.insert(0, '$(SRC_DIR)'); \
	from python_dev_tool.cli.commands.dev import DevCommand; \
	from pathlib import Path; \
	print('$(GREEN)$(EMOJI_SUCCESS) DevCommand import successful$(RESET)')" || \
	(echo -e "$(CRIMSON)$(EMOJI_ERROR) DevCommand import failed!$(RESET)" && exit 1)

	@echo -e "$(SLATE)Testing Config loading...$(RESET)"
	@PYTHONDONTWRITEBYTECODE=1 python -c "\
	import sys; \
	sys.path.insert(0, '$(SRC_DIR)'); \
	from python_dev_tool.core.config import Config; \
	print('$(GREEN)$(EMOJI_SUCCESS) Config import successful$(RESET)')" || \
	(echo -e "$(CRIMSON)$(EMOJI_ERROR) Config import failed!$(RESET)" && exit 1)

	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Application components test passed!$(RESET)"



.PHONY: test-ui
test-ui:
	@echo -e "$(CYAN)$(EMOJI_UI) Testing FUSE Development UI...$(RESET)"
	@echo -e "$(SLATE)Testing web app creation...$(RESET)"
	@PYTHONDONTWRITEBYTECODE=1 python scripts/test_dev_ui.py



.PHONY: test-network
test-network:
	@echo -e "$(CYAN)$(EMOJI_NETWORK) Testing network utilities...$(RESET)"
	@PYTHONDONTWRITEBYTECODE=1 python -c "\
	import sys; \
	sys.path.insert(0, '$(SRC_DIR)'); \
	from python_dev_tool.utils.network_utils import NetworkUtils, DomainUtils; \
	print('$(SLATE)Testing port availability...$(RESET)'); \
	result = NetworkUtils.check_port_available('127.0.0.1', 9999); \
	print(f'Port 9999 available: {result}'); \
	port = NetworkUtils.find_free_port('127.0.0.1', 8000); \
	print(f'Found free port: {port}'); \
	domain = DomainUtils(); \
	domain.configure('127.0.0.1', 8000, 8001); \
	print(f'App URL: {domain.get_app_url()}'); \
	print(f'UI URL: {domain.get_ui_url()}'); \
	print('$(GREEN)$(EMOJI_SUCCESS) Network utilities test passed$(RESET)')" || \
	(echo -e "$(CRIMSON)$(EMOJI_ERROR) Network utilities test failed!$(RESET)" && exit 1)

.PHONY: test-integration
test-integration:
	@echo -e "$(CYAN)$(EMOJI_TEST) Running integration tests...$(RESET)"
	@echo -e "$(SLATE)Creating test project...$(RESET)"
	@mkdir -p test_project/.fuse
	@echo '[project]\nname = "test-project"\nframework = "flask"\n\n[server]\nhost = "127.0.0.1"\nport = 8000\n\n[dashboard]\nport = 8001\n\n[commands]\ndev = "echo Hello from test project"\ntest = "echo Running tests"' > test_project/.fuse/config.toml
	@echo -e "$(SLATE)Testing FUSE initialization...$(RESET)"
	@cd test_project && PYTHONDONTWRITEBYTECODE=1 python -c "\
	import sys; \
	sys.path.insert(0, '../$(SRC_DIR)'); \
	from python_dev_tool.core.config import Config; \
	from pathlib import Path; \
	config = Config.load_from_project(Path.cwd()); \
	print(f'$(GREEN)$(EMOJI_SUCCESS) Project loaded: {config.project_name}$(RESET)'); \
	print(f'$(GREEN)$(EMOJI_SUCCESS) Framework: {config.framework}$(RESET)'); \
	print(f'$(GREEN)$(EMOJI_SUCCESS) Commands: {list(config.commands.keys())}$(RESET)')" || \
	(echo -e "$(CRIMSON)$(EMOJI_ERROR) Integration test failed!$(RESET)" && rm -rf test_project && exit 1)
	@rm -rf test_project
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Integration test passed!$(RESET)"

.PHONY: test-ports
test-ports:
	@echo -e "$(CYAN)$(EMOJI_NETWORK) Testing port detection and assignment...$(RESET)"
	@PYTHONDONTWRITEBYTECODE=1 python -c "\
	import sys; \
	sys.path.insert(0, '$(SRC_DIR)'); \
	from python_dev_tool.utils.network_utils import NetworkUtils; \
	print('$(SLATE)Testing port 8000:$(RESET)', NetworkUtils.check_port_available('127.0.0.1', 8000)); \
	print('$(SLATE)Testing port 8001:$(RESET)', NetworkUtils.check_port_available('127.0.0.1', 8001)); \
	print('$(SLATE)Finding free port from 8000:$(RESET)', NetworkUtils.find_free_port('127.0.0.1', 8000)); \
	print('$(SLATE)Finding free port from 8001:$(RESET)', NetworkUtils.find_free_port('127.0.0.1', 8001)); \
	print('$(GREEN)$(EMOJI_SUCCESS) Port detection test passed$(RESET)')" || \
	(echo -e "$(CRIMSON)$(EMOJI_ERROR) Port detection test failed!$(RESET)" && exit 1)

.PHONY: quick-test
quick-test: test-app test-ui test-network
	@echo -e "$(GREEN)$(EMOJI_FAST) All quick component tests completed!$(RESET)"

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

.PHONY: docs-build
docs-build:
	@echo -e "$(BLUE)$(EMOJI_DOCS) Building documentation...$(RESET)"
	@mkdocs build
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Documentation built!$(RESET)"

.PHONY: docs-publish
docs-publish:
	@echo -e "$(BLUE)$(EMOJI_DOCS) Publishing documentation...$(RESET)"
	@mkdocs gh-deploy --force --remote-name docs
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Documentation published!$(RESET)"

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

.PHONY: doctor
doctor:
	@echo -e "$(SLATE)$(EMOJI_DOCTOR) Running FUSE diagnostics...$(RESET)"
	@echo -e "$(YELLOW)Python version:$(RESET)"
	@python --version
	@echo -e "$(YELLOW)Python path:$(RESET)"
	@python -c "import sys; print('\n'.join(sys.path))"
	@echo -e "$(YELLOW)FUSE module path:$(RESET)"
	@python -c "import sys; sys.path.insert(0, '$(SRC_DIR)'); import python_dev_tool; print(python_dev_tool.__file__)" 2>/dev/null || echo "$(CRIMSON)$(EMOJI_ERROR) FUSE module not found$(RESET)"
	@echo -e "$(YELLOW)Available ports:$(RESET)"
	@python -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(f'Sample available port: {s.getsockname()[1]}'); s.close()"
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Diagnostics complete!$(RESET)"

.PHONY: demo
demo:
	@echo -e "$(CYAN)$(EMOJI_DEMO) Creating FUSE demo project...$(RESET)"
	@mkdir -p demo_project/.fuse
	@echo 'from flask import Flask\n\napp = Flask(__name__)\n\n@app.route("/")\ndef hello():\n    return "Hello from FUSE Demo!"\n\nif __name__ == "__main__":\n    app.run(host="127.0.0.1", port=8000, debug=True)' > demo_project/app.py
	@echo '[project]\nname = "fuse-demo"\nframework = "flask"\nversion = "1.0.0"\n\n[server]\nhost = "127.0.0.1"\nport = 8000\nauto_reload = true\n\n[dashboard]\nport = 8001\nauto_open = true\n\n[commands]\ndev = "python app.py"\ntest = "echo No tests configured"\nlint = "echo No linting configured"' > demo_project/.fuse/config.toml
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Demo project created in demo_project/$(RESET)"
	@echo -e "$(YELLOW)To run demo: cd demo_project && make dev$(RESET)"

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



# -------------------------------------
#  Platform-Specific Package Building
# -------------------------------------

.PHONY: build-arch
build-arch:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building Arch Linux package...$(RESET)"
	@bash $(SCRIPT_FILE)build_arch.sh $(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Arch package built!$(RESET)"

.PHONY: build-deb
build-deb:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building Debian/Ubuntu package...$(RESET)"
	@bash $(SCRIPT_FILE)build_deb.sh $(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Debian package built!$(RESET)"

.PHONY: build-rpm
build-rpm:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building RPM package...$(RESET)"
	@bash $(SCRIPT_FILE)build_rpm.sh $(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) RPM package built!$(RESET)"

.PHONY: build-windows
build-windows:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building Windows package...$(RESET)"
	@bash $(SCRIPT_FILE)build_windows.sh $(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Windows package built!$(RESET)"

.PHONY: build-macos
build-macos:
	@echo -e "$(ORANGE)$(EMOJI_BUILD) Building macOS package...$(RESET)"
	@bash $(SCRIPT_FILE)build_macos.sh $(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) macOS package built!$(RESET)"

.PHONY: build-all-platforms
build-all-platforms:
	@echo -e "$(ORANGE)$(EMOJI_ROCKET) Building packages for all platforms...$(RESET)"
	@python scripts/build_release.py --platform all
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) All platform packages built!$(RESET)"

# -------------------------------------
#  Package Manager Updates
# -------------------------------------

.PHONY: update-homebrew
update-homebrew:
	@echo -e "$(BLUE)$(EMOJI_PUBLISH) Updating Homebrew formula...$(RESET)"
	@cd ../fuse-homebrew && \
	git pull && \
	sed -i '' 's/version ".*"/version "$(shell hatch version)"/' Formula/fuse.rb && \
	git add Formula/fuse.rb && \
	git commit -m "Update to version $(shell hatch version)" && \
	git push
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Homebrew formula updated!$(RESET)"

.PHONY: update-aur
update-aur:
	@echo -e "$(BLUE)$(EMOJI_PUBLISH) Updating AUR package...$(RESET)"
	@cd packaging/build/arch && \
	makepkg --printsrcinfo > .SRCINFO && \
	git add PKGBUILD .SRCINFO && \
	git commit -m "Update to version $(shell hatch version)" && \
	git push
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) AUR package updated!$(RESET)"

.PHONY: publish-pypi
publish-pypi:
	@echo -e "$(ORANGE)$(EMOJI_PUBLISH) Publishing to PyPI...$(RESET)"
	@python -m build
	@twine upload dist/*
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Published to PyPI!$(RESET)"

.PHONY: publish-test-pypi
publish-test-pypi:
	@echo -e "$(ORANGE)$(EMOJI_PUBLISH) Publishing to Test PyPI...$(RESET)"
	@python -m build
	@twine upload --repository testpypi dist/*
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Published to Test PyPI!$(RESET)"

# -------------------------------------
#  Release Workflow
# -------------------------------------

.PHONY: release-check
release-check:
	@echo -e "$(BLUE)$(EMOJI_TEST) Running pre-release checks...$(RESET)"
	@echo -e "$(YELLOW)Checking tests...$(RESET)"
	@make test || (echo -e "$(RED)$(EMOJI_ERROR) Tests failed!$(RESET)" && exit 1)
	@echo -e "$(YELLOW)Checking linting...$(RESET)"
	@make lint || (echo -e "$(RED)$(EMOJI_ERROR) Linting failed!$(RESET)" && exit 1)
	@echo -e "$(YELLOW)Checking git status...$(RESET)"
	@git diff --exit-code || (echo -e "$(RED)$(EMOJI_ERROR) Uncommitted changes!$(RESET)" && exit 1)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) All pre-release checks passed!$(RESET)"

.PHONY: release-tag
release-tag:
	@echo -e "$(BLUE)$(EMOJI_VERSION) Creating release tag...$(RESET)"
	@git tag -a v$(shell hatch version) -m "Release version $(shell hatch version)"
	@git push origin v$(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Tag created and pushed!$(RESET)"

.PHONY: release-notes
release-notes:
	@echo -e "$(BLUE)$(EMOJI_DOCS) Generating release notes...$(RESET)"
	@python scripts/generate_release_notes.py $(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Release notes generated!$(RESET)"

.PHONY: release-github
release-github:
	@echo -e "$(BLUE)$(EMOJI_ROCKET) Creating GitHub release...$(RESET)"
	@gh release create v$(shell hatch version) \
		--title "FUSE v$(shell hatch version)" \
		--notes-file releases/RELEASE_NOTES.md \
		releases/*
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) GitHub release created!$(RESET)"

.PHONY: release-full
release-full: release-check version-patch release-tag build-all-platforms publish-pypi release-github
	@echo -e "$(GREEN)$(EMOJI_ROCKET) Full release completed!$(RESET)"
	@echo -e "$(BLUE)Version: $(shell hatch version)$(RESET)"
	@echo -e "$(BLUE)Released to:$(RESET)"
	@echo -e "  - PyPI: https://pypi.org/project/fuse-dev-tool/$(shell hatch version)/"
	@echo -e "  - GitHub: https://github.com/fuse-dev-tool/fuse-core/releases/tag/v$(shell hatch version)"

# -------------------------------------
#  Distribution Verification
# -------------------------------------

.PHONY: verify-packages
verify-packages:
	@echo -e "$(BLUE)$(EMOJI_TEST) Verifying release packages...$(RESET)"
	@cd releases && sha256sum -c SHA256SUMS
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) All packages verified!$(RESET)"

.PHONY: test-install-local
test-install-local:
	@echo -e "$(BLUE)$(EMOJI_TEST) Testing local installation...$(RESET)"
	@pip install -e .
	@fuse --version
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Local installation works!$(RESET)"

.PHONY: test-install-pypi
test-install-pypi:
	@echo -e "$(BLUE)$(EMOJI_TEST) Testing PyPI installation...$(RESET)"
	@python -m venv test_env
	@./test_env/bin/pip install fuse-dev-tool
	@./test_env/bin/fuse --version
	@rm -rf test_env
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) PyPI installation works!$(RESET)"

# -------------------------------------
#  Repository Management
# -------------------------------------

.PHONY: sync-all-repos
sync-all-repos: git-commit-current git-push-all
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) All repositories synchronized!$(RESET)"

.PHONY: repo-status
repo-status:
	@echo -e "$(BLUE)$(EMOJI_NETWORK) Repository status:$(RESET)"
	@echo -e "$(YELLOW)Main repository:$(RESET)"
	@git status -s
	@echo -e "\n$(YELLOW)Remote repositories:$(RESET)"
	@for remote in core cli ui docs plugins templates; do \
		echo -e "$(CYAN)$$remote:$(RESET) $$(git ls-remote --get-url $$remote 2>/dev/null || echo 'Not configured')"; \
	done

.PHONY: create-release-branch
create-release-branch:
	@echo -e "$(BLUE)$(EMOJI_ROCKET) Creating release branch...$(RESET)"
	@git checkout -b release/v$(shell hatch version)
	@git push -u origin release/v$(shell hatch version)
	@echo -e "$(GREEN)$(EMOJI_SUCCESS) Release branch created!$(RESET)"


# -------------------------------------
#  Community Management
# -------------------------------------

.PHONY: announce-release
announce-release:
	@echo -e "$(BLUE)$(EMOJI_ROCKET) Announcing release...$(RESET)"
	@echo "Please manually announce the release on:"
	@echo "  - Discord: #announcements channel"
	@echo "  - Twitter/X: @fuse_dev_tool"
	@echo "  - Reddit: r/Python"
	@echo "  - Dev.to: FUSE Team blog"
	@echo ""
	@echo "Announcement template saved to: releases/ANNOUNCEMENT.md"
