"""
Executor Abstraction Layer

Provides a unified interface for code execution with multiple backend options.
Uses dependency injection pattern to select executor at runtime without modifying
the underlying executor implementations.
"""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ExecutorType(str, Enum):
    """Available executor backends."""

    SMOLAGENTS = "smolagents"
    DAYTONA = "daytona"


@dataclass
class ExecutionResult:
    """Result of code execution."""

    success: bool
    output: Any
    logs: list[str]
    error: str | None = None
    execution_time_ms: int | None = None


class CodeExecutor(ABC):
    """Abstract base class for code executors."""

    @abstractmethod
    def execute(
        self,
        code: str,
        globals_dict: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> ExecutionResult:
        """
        Execute Python code in a sandboxed environment.

        Args:
            code: Python code to execute
            globals_dict: Global variables to inject into execution context
            timeout_seconds: Maximum execution time

        Returns:
            ExecutionResult with output and logs
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this executor is available/configured."""
        pass


class SmolagentsExecutor(CodeExecutor):
    """Wrapper for smolagents Python executor."""

    def __init__(self, authorized_imports: list[str] | None = None):
        """
        Initialize smolagents executor wrapper.

        Args:
            authorized_imports: List of allowed module imports
        """
        # Import smolagents module locally to avoid top-level import
        from app.agents.executors.smolagents_executor import (
            BASE_BUILTIN_MODULES,
            BASE_PYTHON_TOOLS,
            PrintContainer,
            evaluate_python_code,
        )

        self.evaluate_python_code = evaluate_python_code
        self.BASE_PYTHON_TOOLS = BASE_PYTHON_TOOLS
        self.PrintContainer = PrintContainer

        # Default to base builtin modules plus common data science libraries
        self.authorized_imports = authorized_imports or [
            *BASE_BUILTIN_MODULES,
            "pandas",
            "numpy",
            "json",
        ]

    def execute(
        self,
        code: str,
        globals_dict: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> ExecutionResult:
        """Execute code using smolagents executor."""
        import time

        start_time = time.time()

        try:
            # Prepare state with provided globals
            state = globals_dict or {}

            # Create print container for capturing output
            print_container = self.PrintContainer()
            static_tools = {**self.BASE_PYTHON_TOOLS, "print": print_container.append}

            # Execute code - returns (result, is_final_answer) tuple
            result_tuple = self.evaluate_python_code(
                code=code,
                state=state,
                static_tools=static_tools,
                custom_tools={},
                authorized_imports=self.authorized_imports,
            )

            # Extract actual result from tuple
            result = (
                result_tuple[0] if isinstance(result_tuple, tuple) else result_tuple
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "code_executed_successfully",
                execution_time_ms=execution_time_ms,
                output_length=len(str(result)),
            )

            # Get logs from state where PrintContainer stores output
            logs = []
            if "_print_outputs" in state:
                print_output = state["_print_outputs"]
                if hasattr(print_output, "value") and print_output.value:
                    # Split by newlines and filter empty strings
                    logs = [
                        line.strip()
                        for line in str(print_output.value).split("\n")
                        if line.strip()
                    ]

            return ExecutionResult(
                success=True,
                output=result,
                logs=logs,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error("code_execution_failed", error=str(e), exc_info=True)

            return ExecutionResult(
                success=False,
                output=None,
                logs=[],
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

    def is_available(self) -> bool:
        """Smolagents is always available as it's built-in."""
        return True


class DaytonaExecutor(CodeExecutor):
    """Wrapper for Daytona cloud-based executor."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize Daytona executor wrapper.

        Args:
            api_key: Daytona API key
        """
        # Import Daytona module locally
        from app.agents.executors.daytona_executor import (
            DaytonaExecutor as DaytonaExecutorImpl,
        )
        from app.config import settings

        # Use provided API key or fall back to settings
        api_key = api_key or settings.daytona_api_key

        self.executor_impl = DaytonaExecutorImpl(api_key=api_key, auto_cleanup=True)

        if not self.is_available():
            logger.warning(
                "daytona_executor_not_configured",
                message="Daytona API key not provided",
            )

    def execute(
        self,
        code: str,
        globals_dict: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> ExecutionResult:
        """Execute code using Daytona executor."""
        result_dict = self.executor_impl.execute(code, globals_dict, timeout_seconds)

        return ExecutionResult(
            success=result_dict["success"],
            output=result_dict.get("output"),
            logs=result_dict.get("logs", []),
            error=result_dict.get("error"),
            execution_time_ms=result_dict.get("execution_time_ms"),
        )

    def is_available(self) -> bool:
        """Check if Daytona is configured."""
        return self.executor_impl.is_configured()

    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, "executor_impl"):
            self.executor_impl.cleanup()


class ExecutorFactory:
    """Factory for creating executor instances."""

    _executors: dict[ExecutorType, CodeExecutor] = {}
    _lock = threading.Lock()

    @classmethod
    def get_executor(
        cls, executor_type: ExecutorType = ExecutorType.SMOLAGENTS
    ) -> CodeExecutor:
        """
        Get or create an executor instance.

        Args:
            executor_type: Type of executor to use

        Returns:
            CodeExecutor instance

        Raises:
            ValueError: If executor type is not available
        """
        # Return cached instance if available
        if executor_type in cls._executors:
            return cls._executors[executor_type]

        with cls._lock:
            # Double-check inside lock
            if executor_type in cls._executors:
                return cls._executors[executor_type]

            # Create new instance
            if executor_type == ExecutorType.SMOLAGENTS:
                executor = SmolagentsExecutor()
            elif executor_type == ExecutorType.DAYTONA:
                executor = DaytonaExecutor()
            else:
                raise ValueError(f"Unknown executor type: {executor_type}")

            # Verify availability
            if not executor.is_available():
                raise ValueError(f"Executor {executor_type} is not available")

            # Cache and return
            cls._executors[executor_type] = executor
            return executor

    @classmethod
    def get_default_executor(cls) -> CodeExecutor:
        """Get the default executor (smolagents)."""
        return cls.get_executor(ExecutorType.SMOLAGENTS)


# Convenience function for direct use
def execute_code(
    code: str,
    globals_dict: dict[str, Any] | None = None,
    executor_type: ExecutorType = ExecutorType.SMOLAGENTS,
    timeout_seconds: int = 30,
) -> ExecutionResult:
    """
    Execute Python code using specified executor.

    Args:
        code: Python code to execute
        globals_dict: Global variables for execution context
        executor_type: Which executor backend to use
        timeout_seconds: Maximum execution time

    Returns:
        ExecutionResult with output and logs
    """
    executor = ExecutorFactory.get_executor(executor_type)
    return executor.execute(code, globals_dict, timeout_seconds)
