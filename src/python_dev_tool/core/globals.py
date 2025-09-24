"""
FUSE - Python Dev Tool
Core - Global Variables
"""

#  server variables
APP_HOST = ("127.0.0.1",)
APP_PORT = (8000,)
APP_UI_PORT = (8001,)
APP_DEBUG = (True,)
APP_RELOAD = (True,)
APP_OPEN_BROWSER = (True,)
APP_LOG_LEVEL = ("info",)
APP_UI_PORT = (8001,)
APP_WORKERS = (1,)
APP_TIMEOUT = (30,)

# logging config    variables
LOG_LEVEL = ("info",)
LOG_FORMAT = ("%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
LOG_FILE_ENABLED = (True,)
LOG_FILE_PATH = ("logs/fusetool.log",)
LOG_MAX_FILE_SIZE = (10 * 1024 * 1024,)  # 10MB
LOG_BACKUP_COUNT = (5,)


# Config -  project settings\
PROJECT_NAME = ("my project",)
PROJECT_ROOT = (".",)
FRAMEWORK = (None,)
PYTHON_VERSION = ("3.13",)


# suppported frameworks
SUPPORTED_FRAMEWORKS = ["django", "flask", "fastapi", "streamlit", "tornado", "sanic"]


# config file names


# config files
FUSE_CONFIG_FILE = ".fuse/config.toml"


# Framework signatures for detection
FRAMEWORK_SIGNATURES = {
    "django": {
        "files": ["manage.py", "settings.py", "wsgi.py", "asgi.py"],
        "directories": ["django", "migrations"],
        "imports": ["django", "django.conf", "django.core"],
        "patterns": [
            r"from\s+django\s+import",
            r"import\s+django",
            r"DJANGO_SETTINGS_MODULE",
            r"django\.setup\(\)",
        ],
        "requirements": ["django"],
        "commands": {
            "dev": "python manage.py runserver {host}:{port}",
            "migrate": "python manage.py migrate",
            "shell": "python manage.py shell",
            "test": "python manage.py test",
            "collectstatic": "python manage.py collectstatic",
            "createsuperuser": "python manage.py createsuperuser",
            "makemigrations": "python manage.py makemigrations",
        },
        "config_files": ["settings.py", "urls.py", "wsgi.py", "asgi.py"],
    },
    "flask": {
        "files": ["app.py", "application.py", "main.py", "run.py", "server.py"],
        "directories": ["flask"],
        "imports": ["flask", "Flask"],
        "patterns": [
            r"from\s+flask\s+import",
            r"import\s+flask",
            r"Flask\(__name__\)",
            r"app\s*=\s*Flask",
            r"@app\.route",
        ],
        "requirements": ["flask"],
        "commands": {
            "dev": "flask run --host {host} --port {port}",
            "shell": "flask shell",
        },
        "config_files": ["config.py", "instance/config.py"],
    },
    "fastapi": {
        "files": ["main.py", "app.py", "api.py"],
        "directories": ["fastapi"],
        "imports": ["fastapi", "FastAPI"],
        "patterns": [
            r"from\s+fastapi\s+import",
            r"import\s+fastapi",
            r"FastAPI\(\)",
            r"app\s*=\s*FastAPI",
            r"@app\.(get|post|put|delete)",
        ],
        "requirements": ["fastapi", "uvicorn"],
        "commands": {
            "dev": "uvicorn main:app --host {host} --port {port} --reload",
            "prod": "uvicorn main:app --host 0.0.0.0 --port 8000",
        },
        "config_files": ["main.py", "app.py"],
    },
    "streamlit": {
        "files": ["*.py"],
        "directories": ["streamlit"],
        "imports": ["streamlit"],
        "patterns": [
            r"import\s+streamlit",
            r"streamlit\s+as\s+st",
            r"st\.",
        ],
        "requirements": ["streamlit"],
        "commands": {
            "dev": "streamlit run app.py --server.port {port} --server.address {host}",
        },
        "config_files": [".streamlit/config.toml"],
    },
    "tornado": {
        "files": ["*.py"],
        "directories": ["tornado"],
        "imports": ["tornado", "tornado.web"],
        "patterns": [
            r"import\s+tornado",
            r"from\s+tornado\s+import",
            r"tornado\.web\.Application",
            r"tornado\.ioloop\.IOLoop",
        ],
        "requirements": ["tornado"],
        "commands": {
            "dev": "python app.py --port={port}",
        },
        "config_files": [],
    },
    "sanic": {
        "files": ["*.py"],
        "directories": ["sanic"],
        "imports": ["sanic", "Sanic"],
        "patterns": [
            r"from\s+sanic\s+import",
            r"import\s+sanic",
            r"Sanic\(__name__\)",
            r"app\s*=\s*Sanic",
            r"@app\.route",
        ],
        "requirements": ["sanic"],
        "commands": {
            "dev": "sanic app.py --host={host} --port={port} --debug",
        },
        "config_files": [],
    },
}


VERSION_PATTERNS = {
    "django": r"Django[=<>~!]*\s*([\d.]+)",
    "flask": r"Flask[=<>~!]*\s*([\d.]+)",
    "fastapi": r"fastapi[=<>~!]*\s*([\d.]+)",
    "streamlit": r"streamlit[=<>~!]*\s*([\d.]+)",
    "tornado": r"tornado[=<>~!]*\s*([\d.]+)",
    "sanic": r"sanic[=<>~!]*\s*([\d.]+)",
}


REQUIREMENTS_FILES = [
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "pipfile",
    "environment.yml",
    "poetry.lock",
]

FRAMEWORK_PATTERNS = {
    "django": {
        "files": ["manage.py", "wsgi.py", "asgi.py"],
        "directories": ["templates", "static", "migrations"],
        "config_files": ["settings.py", "urls.py"],
        "imports": ["django"],
        "patterns": [r"from\s+django", r"import\s+django"],
    },
    "flask": {
        "files": ["app.py", "main.py"],
        "directories": ["templates", "static"],
        "config_files": ["config.py"],
        "imports": ["flask"],
        "patterns": [r"from\s+flask", r"Flask\(__name__\)"],
    },
    "fastapi": {
        "files": ["main.py", "app.py"],
        "directories": ["app", "routers"],
        "config_files": [],
        "imports": ["fastapi"],
        "patterns": [r"from\s+fastapi", r"FastAPI\("],
    },
    "streamlit": {
        "files": ["*.py"],
        "directories": ["pages", ".streamlit"],
        "config_files": ["config.toml"],
        "imports": ["streamlit"],
        "patterns": [r"import\s+streamlit", r"st\."],
    },
}
