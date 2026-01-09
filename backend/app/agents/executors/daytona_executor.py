"""
Daytona Executor Implementation

Provides code execution using Daytona's cloud-based development environments.
Daytona creates isolated sandboxes for secure code execution.

Installation: pip install daytona
Documentation: https://daytona.io/docs
"""

import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DaytonaExecutorError(Exception):
    """Raised when Daytona executor operations fail."""

    pass


class DaytonaExecutor:
    """
    Daytona executor for running code in isolated cloud sandboxes.

    Uses the Daytona SDK to create and manage development environments
    and execute Python code securely.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.daytona.io",
        auto_cleanup: bool = True,
    ):
        """
        Initialize Daytona executor.

        Args:
            api_key: Daytona API key
            base_url: Daytona API base URL
            auto_cleanup: Whether to auto-cleanup sandboxes after execution
        """
        self.api_key = api_key
        self.base_url = base_url
        self.auto_cleanup = auto_cleanup
        self._client = None
        self._sandbox = None

        if api_key:
            self._initialize_client()

    def _initialize_client(self):
        """Initialize the Daytona client."""
        try:
            from daytona_sdk import Daytona

            self._client = Daytona(api_key=self.api_key, base_url=self.base_url)
            logger.info("daytona_client_initialized", base_url=self.base_url)

        except ImportError:
            logger.error(
                "daytona_sdk_not_installed",
                message="Install with: pip install daytona",
            )
            raise DaytonaExecutorError(
                "Daytona SDK not installed. Install with: pip install daytona"
            )
        except Exception as e:
            logger.error("daytona_client_init_failed", error=str(e))
            raise DaytonaExecutorError(f"Failed to initialize Daytona client: {e}")

    def _ensure_sandbox(self, language: str = "python"):
        """
        Create a sandbox if one doesn't exist.

        Args:
            language: Programming language for the sandbox
        """
        if self._sandbox is None:
            try:
                self._sandbox = self._client.create(language=language)
                logger.info("daytona_sandbox_created", sandbox_id=self._sandbox.id)
            except Exception as e:
                logger.error("daytona_sandbox_creation_failed", error=str(e))
                raise DaytonaExecutorError(f"Failed to create sandbox: {e}")

    def execute(
        self,
        code: str,
        globals_dict: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> dict:
        """
        Execute Python code in a Daytona sandbox.

        Args:
            code: Python code to execute
            globals_dict: Global variables (Note: Daytona handles state internally)
            timeout_seconds: Maximum execution time

        Returns:
            dict: Execution result with output, logs, and error info
        """
        if not self.is_configured():
            return {
                "success": False,
                "output": None,
                "logs": [],
                "error": "Daytona executor not configured (missing API key)",
            }

        start_time = time.time()

        try:
            # Ensure we have a sandbox
            self._ensure_sandbox()

            # If globals provided, prepend them as variable assignments
            if globals_dict:
                globals_code = "\n".join(
                    [f"{key} = {repr(value)}" for key, value in globals_dict.items()]
                )
                code = f"{globals_code}\n\n{code}"

            # Execute code using Daytona's code_run method
            result = self._sandbox.process.code_run(code=code, language="python")

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Parse Daytona result
            if hasattr(result, "error") and result.error:
                logger.error("daytona_code_execution_error", error=result.error)
                return {
                    "success": False,
                    "output": getattr(result, "output", None),
                    "logs": getattr(result, "logs", []),
                    "error": result.error,
                    "execution_time_ms": execution_time_ms,
                }

            logger.info(
                "daytona_code_executed_successfully",
                execution_time_ms=execution_time_ms,
            )

            return {
                "success": True,
                "output": getattr(result, "output", None),
                "logs": getattr(result, "logs", []),
                "error": None,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error("daytona_execution_failed", error=str(e), exc_info=True)

            return {
                "success": False,
                "output": None,
                "logs": [],
                "error": str(e),
                "execution_time_ms": execution_time_ms,
            }

    def is_configured(self) -> bool:
        """Check if Daytona is properly configured."""
        return self.api_key is not None

    def cleanup(self):
        """Clean up the sandbox if it exists."""
        if self._sandbox is not None:
            try:
                self._sandbox.delete()
                logger.info("daytona_sandbox_deleted", sandbox_id=self._sandbox.id)
                self._sandbox = None
            except Exception as e:
                logger.warning("daytona_sandbox_cleanup_failed", error=str(e))

    def __del__(self):
        """Cleanup on deletion."""
        if self.auto_cleanup:
            self.cleanup()


# Usage example (for reference):
"""
from app.agents.executors.daytona_executor import DaytonaExecutor

# Initialize with API key
executor = DaytonaExecutor(api_key="your-api-key-here")

# Execute code
result = executor.execute('''
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3]})
len(df)
''')

print(result['output'])  # 3
print(result['logs'])    # Any print statements
print(result['error'])   # None if successful

# Cleanup
executor.cleanup()
"""
