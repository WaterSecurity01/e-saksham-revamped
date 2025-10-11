import logging
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict
from flask import jsonify, render_template, request
from sqlalchemy.exc import PendingRollbackError
from werkzeug.exceptions import HTTPException
from jinja2 import TemplateNotFound

from app import db


LOG_ROOT = Path(__file__).resolve().parents[2] / 'logs'
LOG_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class RouteLoggers:
    access: logging.Logger
    error: logging.Logger
    activity: logging.Logger


class LoggingManager:
    """Centralized rotating logger registry for route modules."""

    _registry: Dict[str, RouteLoggers] = {}
    _log_format = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')

    @classmethod
    def get_route_loggers(cls, key: str, *, activity_level: int = logging.INFO) -> RouteLoggers:
        route_key = key.lower().strip()
        if not route_key:
            raise ValueError('Logger key is required')

        if route_key not in cls._registry:
            route_dir = LOG_ROOT / route_key
            route_dir.mkdir(parents=True, exist_ok=True)

            access_logger = cls._build_logger(
                name=f'{route_key}.access',
                file_path=route_dir / f'{route_key}_access.log',
                level=logging.INFO
            )
            error_logger = cls._build_logger(
                name=f'{route_key}.error',
                file_path=route_dir / f'{route_key}_error.log',
                level=logging.ERROR
            )
            activity_logger = cls._build_logger(
                name=f'{route_key}.activity',
                file_path=route_dir / f'{route_key}_activity.log',
                level=activity_level
            )

            cls._registry[route_key] = RouteLoggers(
                access=access_logger,
                error=error_logger,
                activity=activity_logger
            )

        return cls._registry[route_key]

    @classmethod
    def _build_logger(cls, *, name: str, file_path: Path, level: int) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        if not any(getattr(h, 'baseFilename', None) == str(file_path) for h in logger.handlers):
            handler = RotatingFileHandler(file_path, maxBytes=1_048_576, backupCount=5)
            handler.setLevel(level)
            handler.setFormatter(cls._log_format)
            logger.addHandler(handler)

        return logger


def get_route_loggers(route_key: str, *, activity_level: int = logging.INFO) -> RouteLoggers:
    """Convenience wrapper to fetch the three core loggers for a route module."""

    return LoggingManager.get_route_loggers(route_key, activity_level=activity_level)

def _client_ip() -> str:
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'

error_logger_cache = {}

def _resolve_error_logger():
    blueprint = request.blueprint or 'app'
    logger = error_logger_cache.get(blueprint)
    if logger is None:
        logger = get_route_loggers(blueprint).error
        error_logger_cache[blueprint] = logger
    return logger

def _error_response(status_code, message):
    payload = {'status': status_code, 'message': message}
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(payload), status_code
    error_meta = {
        403: {
            'title': 'Access Restricted',
            'subtitle': "You don't have permission to view this resource.",
            'accent': 'warning'
        },
        404: {
            'title': 'Page Not Found',
            'subtitle': "We looked everywhere but couldn't find what you were after.",
            'accent': 'info'
        },
        500: {
            'title': 'Internal Server Error',
            'subtitle': 'Something went wrong on our side. We are looking into it.',
            'accent': 'danger'
        }
    }
    defaults = {
        'title': 'Something unexpected happened',
        'subtitle': 'An error occurred while processing your request.',
        'accent': 'secondary'
    }
    meta = error_meta.get(status_code, defaults)

    context = {
        'status_code': status_code,
        'message': message,
        'request_path': request.path,
        'method': request.method,
        'title': meta['title'],
        'subtitle': meta['subtitle'],
        'accent': meta['accent']
    }
    try:
        return render_template("errors/error.html", **context), status_code
    except TemplateNotFound:
        pass
    return f"{message}", status_code

def _handle_exception(exc):
    logger = _resolve_error_logger()
    exc_info = (type(exc), exc, getattr(exc, '__traceback__', None))

    if isinstance(exc, PendingRollbackError):
        db.session.rollback()
        logger.error('Database transaction rollback required', exc_info=exc_info)
        return _error_response(500, 'A database transaction error occurred.')

    if isinstance(exc, HTTPException):
        status_code = exc.code or 500
        if status_code == 404:
            logger.warning('Resource not found | method=%s | path=%s', request.method, request.path, exc_info=exc_info)
            return _error_response(404, 'Resource not found.')
        if status_code == 403:
            logger.warning('Access forbidden | method=%s | path=%s', request.method, request.path, exc_info=exc_info)
            return _error_response(403, 'Access denied.')
        if status_code == 500:
            logger.error('Internal server error', exc_info=exc_info)
            return _error_response(500, 'An internal server error occurred.')
        logger.warning('HTTP error | status=%s | method=%s | path=%s', status_code, request.method, request.path, exc_info=exc_info)
        description = getattr(exc, 'description', 'Unexpected error.')
        return _error_response(status_code, description)

    logger.error('Unhandled application exception', exc_info=exc_info)
    return _error_response(500, 'An unexpected error occurred.')
