"""
PreenCut - AI-powered video/audio analysis and segmentation tool.
Main application entry point with proper configuration and error handling.
"""

import sys
import signal
import atexit
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import uvicorn

from config import get_config, validate_config
from core.logging import get_logger, log_business_event
from core.exceptions import handle_exceptions, ErrorHandler
from core.dependency_injection import configure_services
from web.gradio_ui import create_gradio_interface
from web.api import router as api_router


# Configure logging and services
logger = get_logger(__name__)
config = get_config()
configure_services()


class Application:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.app = None
        self.setup_complete = False
        
    @handle_exceptions('main')
    def setup(self):
        """Setup the application."""
        logger.info("Starting PreenCut application setup")
        
        # Validate configuration
        config_errors = validate_config()
        if config_errors:
            logger.error(f"Configuration errors: {', '.join(config_errors)}")
            for error in config_errors:
                logger.error(f"Config error: {error}")
            raise RuntimeError(f"Configuration validation failed: {config_errors}")
        
        # Log configuration
        self._log_configuration()
        
        # Check hardware availability
        self._check_hardware()
        
        # Create FastAPI app
        self.app = self._create_fastapi_app()
        
        # Mount Gradio interface
        self._mount_gradio_interface()
        
        # Setup cleanup handlers
        self._setup_cleanup_handlers()
        
        self.setup_complete = True
        logger.info("PreenCut application setup completed successfully")
        log_business_event('application_startup', config=config.name)
    
    def _log_configuration(self):
        """Log current configuration."""
        logger.info("Current Configuration:")
        logger.info(f"  Environment: {config.environment.value}")
        logger.info(f"  Debug mode: {config.debug}")
        logger.info(f"  Speech recognition module: {config.model.speech_recognizer_type}")
        logger.info(f"  Model size: {config.model.whisper_model_size}")
        logger.info(f"  Device: {config.gpu.whisper_device}")
        logger.info(f"  Compute type: {config.gpu.whisper_compute_type}")
        logger.info(f"  GPU IDs: {config.gpu.whisper_gpu_ids}")
        logger.info(f"  Batch size: {config.gpu.whisper_batch_size}")
        logger.info(f"  Ollama URL: {config.ollama.base_url}")
    
    def _check_hardware(self):
        """Check hardware availability."""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                logger.info(f"✅ GPU acceleration available - {gpu_count} GPU(s) detected")
                for i in range(gpu_count):
                    gpu_name = torch.cuda.get_device_name(i)
                    logger.info(f"  GPU {i}: {gpu_name}")
            else:
                logger.warning("⚠️ No GPU detected, using CPU processing")
        except ImportError:
            logger.warning("⚠️ PyTorch not available, GPU status unknown")
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        app = FastAPI(
            title=config.name,
            version=config.version,
            debug=config.debug
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add API routes
        app.include_router(api_router)
        
        # Add health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "version": config.version,
                "environment": config.environment.value
            }
        
        return app
    
    def _mount_gradio_interface(self):
        """Mount Gradio interface to FastAPI app."""
        try:
            gradio_app = create_gradio_interface()
            self.app = gr.mount_gradio_app(self.app, gradio_app, path="/web")
            logger.info("✅ Gradio interface mounted successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create Gradio interface: {str(e)}")
            raise
    
    def _setup_cleanup_handlers(self):
        """Setup cleanup handlers for graceful shutdown."""
        def cleanup():
            """Clean up resources."""
            self._cleanup_directories()
            log_business_event('application_shutdown')
        
        def signal_handler(signum, frame):
            """Handle termination signals."""
            logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
            cleanup()
            sys.exit(0)
        
        # Register cleanup function
        atexit.register(cleanup)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination
    
    def _cleanup_directories(self):
        """Clean up temporary directories."""
        try:
            import shutil
            temp_dir = Path(config.file.temp_folder)
            output_dir = Path(config.file.output_folder)
            
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"✅ Cleaned up {temp_dir}")
            
            if output_dir.exists():
                shutil.rmtree(output_dir)
                logger.info(f"✅ Cleaned up {output_dir}")
                
        except Exception as e:
            logger.error(f"⚠️ Error during cleanup: {e}")
    
    def run(self):
        """Run the application."""
        if not self.setup_complete:
            self.setup()
        
        try:
            logger.info(f"🚀 Starting PreenCut server at http://{config.host}:{config.port}")
            logger.info(f"📱 Web interface available at http://{config.host}:{config.port}/web")
            
            uvicorn.run(
                self.app,
                host=config.host,
                port=config.port,
                log_level=config.log_level.value.lower(),
                access_log=config.debug
            )
            
        except KeyboardInterrupt:
            logger.info("🛑 Application interrupted by user")
        except Exception as e:
            logger.error(f"❌ Application error: {e}")
            raise


def main():
    """Main entry point."""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
