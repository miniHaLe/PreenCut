"""
Core package for PreenCut application.
Provides foundational services like logging, exceptions, and dependency injection.
"""

from .logging import (
    get_logger,
    task_context,
    log_performance,
    log_business_event,
    measure_performance,
    log_exceptions
)

from .exceptions import (
    PreenCutException,
    ErrorCode,
    ErrorDetails,
    ErrorHandler,
    FileProcessingError,
    ModelError,
    ConfigurationError,
    HardwareError,
    NetworkError,
    BusinessLogicError,
    handle_exceptions
)

from .dependency_injection import (
    ServiceContainer,
    ServiceLifetime,
    IServiceScope,
    get_container,
    configure_services,
    service,
    singleton,
    transient,
    scoped
)


__all__ = [
    # Logging
    'get_logger',
    'task_context',
    'log_performance',
    'log_business_event',
    'measure_performance',
    'log_exceptions',
    
    # Exceptions
    'PreenCutException',
    'ErrorCode',
    'ErrorDetails',
    'ErrorHandler',
    'FileProcessingError',
    'ModelError',
    'ConfigurationError',
    'HardwareError',
    'NetworkError',
    'BusinessLogicError',
    'handle_exceptions',
    
    # Dependency Injection
    'ServiceContainer',
    'ServiceLifetime',
    'IServiceScope',
    'get_container',
    'configure_services',
    'service',
    'singleton',
    'transient',
    'scoped',
]
