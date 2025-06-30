"""
Centralized logging configuration for PreenCut application.
Provides structured logging with JSON format, file rotation, and context management.
"""

import logging
import logging.handlers
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

from config.settings import get_config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ContextFormatter(logging.Formatter):
    """Human-readable formatter for console output."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console."""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Color codes for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset_color = '\033[0m'
        
        color = colors.get(record.levelname, '')
        
        base_msg = f"{timestamp} | {color}{record.levelname:8}{reset_color} | {record.name} | {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"
        
        return base_msg


class TaskContextFilter(logging.Filter):
    """Filter to add task context to log records."""
    
    def __init__(self):
        super().__init__()
        self.task_id = None
        self.user_id = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to log record."""
        if hasattr(self, 'task_id') and self.task_id:
            if not hasattr(record, 'extra_fields'):
                record.extra_fields = {}
            record.extra_fields['task_id'] = self.task_id
        
        if hasattr(self, 'user_id') and self.user_id:
            if not hasattr(record, 'extra_fields'):
                record.extra_fields = {}
            record.extra_fields['user_id'] = self.user_id
        
        return True


class LoggerManager:
    """Centralized logger management."""
    
    def __init__(self):
        self._loggers: Dict[str, logging.Logger] = {}
        self._context_filter = TaskContextFilter()
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        config = get_config()
        
        # Create logs directory
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.log_level.value))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.log_level.value))
        
        if config.log_format == "json":
            console_formatter = JSONFormatter()
        else:
            console_formatter = ContextFormatter()
        
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(self._context_filter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            config.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(JSONFormatter())
        file_handler.addFilter(self._context_filter)
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            str(log_path.parent / "error.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        error_handler.addFilter(self._context_filter)
        root_logger.addHandler(error_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the given name."""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        return self._loggers[name]
    
    @contextmanager
    def task_context(self, task_id: str, user_id: Optional[str] = None):
        """Context manager for adding task information to logs."""
        old_task_id = getattr(self._context_filter, 'task_id', None)
        old_user_id = getattr(self._context_filter, 'user_id', None)
        
        self._context_filter.task_id = task_id
        if user_id:
            self._context_filter.user_id = user_id
        
        try:
            yield
        finally:
            self._context_filter.task_id = old_task_id
            self._context_filter.user_id = old_user_id
    
    def log_performance(self, name: str, duration: float, **extra):
        """Log performance metrics."""
        perf_logger = self.get_logger('performance')
        extra_fields = {'duration_ms': duration * 1000, **extra}
        
        record = logging.LogRecord(
            name='performance',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=f"Performance: {name} took {duration:.3f}s",
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        perf_logger.handle(record)
    
    def log_business_event(self, event: str, **data):
        """Log business events for analytics."""
        business_logger = self.get_logger('business')
        extra_fields = {'event_type': event, **data}
        
        record = logging.LogRecord(
            name='business',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=f"Business Event: {event}",
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        business_logger.handle(record)


# Global logger manager instance
_logger_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return _logger_manager.get_logger(name)


def task_context(task_id: str, user_id: Optional[str] = None):
    """Context manager for task logging."""
    return _logger_manager.task_context(task_id, user_id)


def log_performance(name: str, duration: float, **extra):
    """Log performance metrics."""
    _logger_manager.log_performance(name, duration, **extra)


def log_business_event(event: str, **data):
    """Log business events."""
    _logger_manager.log_business_event(event, **data)


# Performance measurement decorator
def measure_performance(operation_name: str = None):
    """Decorator to measure and log function performance."""
    import time
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_performance(name, duration, status='success')
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_performance(name, duration, status='error', error=str(e))
                raise
        
        return wrapper
    return decorator


# Exception logging decorator
def log_exceptions(logger_name: str = None):
    """Decorator to automatically log exceptions."""
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__name__}: {str(e)}",
                    exc_info=True,
                    extra={'function': func.__name__, 'args': str(args)[:200]}
                )
                raise
        
        return wrapper
    return decorator
