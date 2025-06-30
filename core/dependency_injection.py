"""
Dependency injection container for PreenCut application.
Manages service lifecycle and provides clean dependency resolution.
"""

from typing import Dict, Any, Callable, TypeVar, Type, Optional, Protocol
from dataclasses import dataclass
import threading
from abc import ABC, abstractmethod
from enum import Enum


T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime options."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceDescriptor:
    """Describes how a service should be created and managed."""
    service_type: Type
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT


class IServiceScope(Protocol):
    """Protocol for service scope."""
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance."""
        ...
    
    def dispose(self):
        """Dispose of scoped services."""
        ...


class ServiceScope:
    """Manages scoped service instances."""
    
    def __init__(self, container: 'ServiceContainer'):
        self._container = container
        self._scoped_services: Dict[Type, Any] = {}
        self._disposed = False
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance within this scope."""
        if self._disposed:
            raise RuntimeError("Service scope has been disposed")
        
        descriptor = self._container._services.get(service_type)
        if not descriptor:
            raise ValueError(f"Service {service_type} is not registered")
        
        if descriptor.lifetime == ServiceLifetime.SCOPED:
            if service_type not in self._scoped_services:
                self._scoped_services[service_type] = self._container._create_instance(descriptor, self)
            return self._scoped_services[service_type]
        
        return self._container._create_instance(descriptor, self)
    
    def dispose(self):
        """Dispose of all scoped services."""
        for service in self._scoped_services.values():
            if hasattr(service, 'dispose'):
                try:
                    service.dispose()
                except Exception:
                    pass  # Log error in production
        
        self._scoped_services.clear()
        self._disposed = True


class ServiceContainer:
    """Dependency injection container."""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.Lock()
    
    def register_singleton(self, service_type: Type[T], implementation_type: Type[T] = None) -> 'ServiceContainer':
        """Register a singleton service."""
        return self._register_service(
            service_type, 
            implementation_type or service_type, 
            lifetime=ServiceLifetime.SINGLETON
        )
    
    def register_transient(self, service_type: Type[T], implementation_type: Type[T] = None) -> 'ServiceContainer':
        """Register a transient service."""
        return self._register_service(
            service_type, 
            implementation_type or service_type, 
            lifetime=ServiceLifetime.TRANSIENT
        )
    
    def register_scoped(self, service_type: Type[T], implementation_type: Type[T] = None) -> 'ServiceContainer':
        """Register a scoped service."""
        return self._register_service(
            service_type, 
            implementation_type or service_type, 
            lifetime=ServiceLifetime.SCOPED
        )
    
    def register_factory(self, service_type: Type[T], factory: Callable[['ServiceScope'], T], 
                        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> 'ServiceContainer':
        """Register a service with a factory function."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        self._services[service_type] = descriptor
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """Register a specific instance as a singleton."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._services[service_type] = descriptor
        self._singletons[service_type] = instance
        return self
    
    def _register_service(self, service_type: Type[T], implementation_type: Type[T], 
                         lifetime: ServiceLifetime) -> 'ServiceContainer':
        """Internal method to register a service."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=lifetime
        )
        self._services[service_type] = descriptor
        return self
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance."""
        descriptor = self._services.get(service_type)
        if not descriptor:
            raise ValueError(f"Service {service_type} is not registered")
        
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._get_singleton(descriptor)
        
        return self._create_instance(descriptor, None)
    
    def create_scope(self) -> ServiceScope:
        """Create a new service scope."""
        return ServiceScope(self)
    
    def _get_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """Get or create singleton instance."""
        service_type = descriptor.service_type
        
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        with self._lock:
            # Double-check locking
            if service_type in self._singletons:
                return self._singletons[service_type]
            
            instance = self._create_instance(descriptor, None)
            self._singletons[service_type] = instance
            return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope]) -> Any:
        """Create an instance of the service."""
        if descriptor.instance is not None:
            return descriptor.instance
        
        if descriptor.factory is not None:
            return descriptor.factory(scope) if scope else descriptor.factory(self)
        
        if descriptor.implementation_type is None:
            raise ValueError(f"No implementation or factory for {descriptor.service_type}")
        
        # Try to resolve constructor dependencies
        return self._create_with_dependencies(descriptor.implementation_type, scope)
    
    def _create_with_dependencies(self, implementation_type: Type, scope: Optional[ServiceScope]) -> Any:
        """Create instance with dependency injection."""
        try:
            # Simple constructor injection - gets first constructor
            import inspect
            sig = inspect.signature(implementation_type.__init__)
            params = list(sig.parameters.values())[1:]  # Skip 'self'
            
            args = []
            for param in params:
                if param.annotation and param.annotation != inspect.Parameter.empty:
                    if scope:
                        dep = scope.get_service(param.annotation)
                    else:
                        dep = self.get_service(param.annotation)
                    args.append(dep)
                else:
                    # No type annotation, can't resolve
                    break
            
            return implementation_type(*args)
        
        except Exception:
            # Fallback to parameterless constructor
            return implementation_type()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the container."""
        services_count = len(self._services)
        singletons_count = len(self._singletons)
        
        failed_services = []
        for service_type, descriptor in self._services.items():
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                try:
                    self.get_service(service_type)
                except Exception as e:
                    failed_services.append({
                        "service": service_type.__name__,
                        "error": str(e)
                    })
        
        return {
            "status": "healthy" if not failed_services else "unhealthy",
            "services_registered": services_count,
            "singletons_created": singletons_count,
            "failed_services": failed_services
        }


# Global container instance
_container = ServiceContainer()


def get_container() -> ServiceContainer:
    """Get the global service container."""
    return _container


def configure_services(container: ServiceContainer = None) -> ServiceContainer:
    """Configure default services."""
    if container is None:
        container = get_container()
    
    # Import here to avoid circular dependencies
    from config.settings import get_config, ApplicationConfig
    from core.logging import get_logger
    
    # Register configuration
    container.register_instance(ApplicationConfig, get_config())
    
    # Register logger factory
    container.register_factory(
        'logger',
        lambda scope: get_logger('application'),
        ServiceLifetime.SINGLETON
    )
    
    return container


def configure_default_services(container: ServiceContainer = None) -> None:
    """Configure default services in the container."""
    from core.logging import get_logger
    
    logger = get_logger(__name__)
    
    try:
        if container is None:
            container = get_container()
        
        # Import service implementations
        from services.video_service import VideoService
        from services.speech_recognition_service import SpeechRecognitionService
        from services.llm_service import LLMService
        from services.file_service import FileService
        from services.interfaces import (
            VideoServiceInterface,
            SpeechRecognitionServiceInterface,
            LLMServiceInterface,
            FileServiceInterface
        )
        from config.settings import get_settings
        
        settings = get_settings()
        
        # Register core services
        container.register_singleton(VideoServiceInterface, VideoService)
        container.register_singleton(FileServiceInterface, FileService)
        
        # Register speech recognition service with configuration
        speech_service = SpeechRecognitionService(settings.speech_recognizer_type)
        container.register_instance(SpeechRecognitionServiceInterface, speech_service)
        
        # Register LLM service with default model
        if settings.llm_model_options:
            default_model = settings.llm_model_options[0]['label']
            llm_service = LLMService(default_model)
            container.register_instance(LLMServiceInterface, llm_service)
        else:
            logger.warning("No LLM models configured")
        
        logger.info("Default services registered successfully")
        
    except Exception as e:
        logger.error("Failed to configure default services", {"error": str(e)})
        # Don't raise to avoid breaking the container initialization


# Service decorators
def service(lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
    """Decorator to automatically register a class as a service."""
    def decorator(cls):
        get_container()._register_service(cls, cls, lifetime)
        return cls
    return decorator


def singleton(cls):
    """Decorator to register a class as a singleton service."""
    get_container().register_singleton(cls)
    return cls


def transient(cls):
    """Decorator to register a class as a transient service."""
    get_container().register_transient(cls)
    return cls


def scoped(cls):
    """Decorator to register a class as a scoped service."""
    get_container().register_scoped(cls)
    return cls
