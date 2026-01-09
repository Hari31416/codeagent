"""
Datara Base Agent Classes

Two types of agents following patterns from how_to_create_agents.md:
1. SimpleLLMAgent: For routing, classification, simple decisions
2. CodingAgent: For code generation with ReAct loop (uses yield for streaming)
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

import pandas as pd
import structlog
from app.agents.executors.executor import ExecutorFactory
from app.core.memory import SessionMemory
from app.shared.llm import LLMService
from app.shared.models import AgentStatus, AgentStatusType

logger = structlog.get_logger(__name__)


# =============================================================================
# Base Agent
# =============================================================================


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Provides:
    - LLM service integration
    - Memory service integration
    - Usage tracking
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        memory_service: SessionMemory | None = None,
    ):
        """
        Initialize base agent.

        Args:
            llm_service: LLM service instance
            memory_service: Memory service instance
        """
        self.llm = llm_service or LLMService()
        self.memory = memory_service or SessionMemory()
        self.agent_name = self.__class__.__name__

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """
        System prompt for the agent.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute the agent.

        Must be implemented by subclasses.
        """
        pass

    def get_usage_stats(self) -> dict[str, Any]:
        """Get LLM usage statistics for this agent."""
        stats = self.llm.get_usage_stats()
        stats["agent_name"] = self.agent_name
        return stats

    def _create_status(
        self,
        status_type: AgentStatusType,
        message: str,
        iteration: int | None = None,
        total_iterations: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> AgentStatus:
        """Helper to create AgentStatus updates."""
        return AgentStatus(
            agent_name=self.agent_name,
            status_type=status_type,
            message=message,
            iteration=iteration,
            total_iterations=total_iterations,
            data=data,
        )


# =============================================================================
# Simple LLM Agent
# =============================================================================


class SimpleLLMAgent(BaseAgent):
    """
    Simple LLM agent for routing, classification, and simple decisions.

    Makes a single LLM call with system prompt + user prompt.
    Can return text or JSON based on json_mode parameter.

    Usage:
        class MyRouterAgent(SimpleLLMAgent):
            @property
            def system_prompt(self) -> str:
                return "You are a routing agent that decides..."

        agent = MyRouterAgent()
        result = await agent.execute(user_prompt="Should I use SQL or RAG?", json_mode=True)
    """

    async def execute(
        self,
        user_prompt: str,
        json_mode: bool = False,
        session_id: str | None = None,
        include_context: bool = False,
    ) -> str | dict[str, Any]:
        """
        Execute the simple LLM agent.

        Args:
            user_prompt: User's input/question
            json_mode: If True, force JSON response
            session_id: Optional session ID for context
            include_context: Include conversation history from session

        Returns:
            LLM response (text or JSON dict)
        """
        logger.info(
            "Executing SimpleLLMAgent",
            agent=self.agent_name,
            json_mode=json_mode,
        )

        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add context from session if requested
        if session_id and include_context:
            context_messages = await self.memory.get_session_context(
                session_id=session_id,
                include_system=False,
            )
            messages.extend(context_messages)

        # Add user prompt
        messages.append({"role": "user", "content": user_prompt})

        # Call LLM
        try:
            response = await self.llm.simple_call(
                messages=messages,
                json_mode=json_mode,
            )

            # Store in session if provided
            if session_id:
                await self.memory.add_message(
                    session_id=session_id,
                    role="user",
                    content=user_prompt,
                )
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=str(response),
                    metadata={"agent": self.agent_name},
                )

            logger.info(
                "SimpleLLMAgent execution completed",
                agent=self.agent_name,
                response_type=type(response).__name__,
            )

            return response

        except Exception as e:
            logger.error(
                "SimpleLLMAgent execution failed",
                agent=self.agent_name,
                error=str(e),
                exc_info=True,
            )
            raise


# =============================================================================
# Coding Agent (ReAct Loop with Streaming)
# =============================================================================


class CodingAgent(BaseAgent):
    """
    Coding agent with ReAct loop for code generation and execution.

    Uses async generators (yield) to stream status updates during execution,
    enabling real-time progress updates to the frontend.

    Follows the ReAct pattern:
    1. Thoughts: Reason about the problem
    2. Code: Generate Python code to solve it
    3. Observation: Execute code and observe output/errors
    4. Repeat if needed (max iterations)

    Self-healing: If code fails, error is passed as observation for retry.

    Usage:
        class MyAnalystAgent(CodingAgent):
            @property
            def system_prompt(self) -> str:
                return '''You are an analyst agent...'''

        agent = MyAnalystAgent()

        # Stream execution with live updates
        async for status in agent.execute_stream(user_prompt="Analyze data", context={"df": df}):
            print(f"Status: {status.status_type} - {status.message}")
            if status.status_type == AgentStatusType.COMPLETED:
                result = status.data
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        memory_service: SessionMemory | None = None,
        executor_type: str | None = None,
        authorized_imports: list[str] | None = None,
    ):
        """
        Initialize coding agent.

        Args:
            llm_service: LLM service instance
            memory_service: Memory service instance
            executor_type: Code executor type ('smolagents' or 'daytona')
            authorized_imports: List of allowed imports for smolagents executor
        """
        super().__init__(llm_service, memory_service)

        from app.config import settings

        self.executor_type = executor_type or settings.executor_type
        self.authorized_imports = authorized_imports

        # Create executor - use custom imports if provided for smolagents
        if self.executor_type == "smolagents" and authorized_imports is not None:
            from app.agents.executors.executor import SmolagentsExecutor

            self.executor = SmolagentsExecutor(authorized_imports=authorized_imports)
        else:
            self.executor = ExecutorFactory.get_executor(self.executor_type)

    async def execute_stream(
        self,
        user_prompt: str,
        context: dict[str, Any] | None = None,
        max_iterations: int = 5,
        session_id: str | None = None,
        include_context: bool = False,
    ) -> AsyncGenerator[AgentStatus, None]:
        """
        Execute the coding agent with ReAct loop, yielding status updates.

        This is the streaming version that yields AgentStatus updates
        throughout execution for real-time frontend updates.

        Args:
            user_prompt: User's request/question
            context: Additional context (file IDs, data, etc.)
            max_iterations: Maximum ReAct iterations
            session_id: Optional session ID for memory
            include_context: Include conversation history from session

        Yields:
            AgentStatus updates during execution

        The final yield with status_type=COMPLETED contains the result in data.
        """
        logger.info(
            "Executing CodingAgent (streaming)",
            agent=self.agent_name,
            max_iterations=max_iterations,
        )

        # Yield: Started
        yield self._create_status(
            AgentStatusType.STARTED,
            f"Starting {self.agent_name}",
            total_iterations=max_iterations,
        )

        # Combine global and specific prompts
        full_system_prompt = f"{self.system_prompt}"

        # Initial messages
        messages = [{"role": "system", "content": full_system_prompt}]

        # Add context from session if requested (makes the agent stateful)
        has_conversation_history = False
        if session_id and include_context:
            context_messages = await self.memory.get_session_context(
                session_id=session_id,
                include_system=False,
            )
            messages.extend(context_messages)
            has_conversation_history = len(context_messages) > 0
            logger.debug(
                f"A total of {len(context_messages)} context messages added to messages",
                agent=self.agent_name,
                session_id=session_id,
            )

        # Add user prompt
        messages.append(
            {
                "role": "user",
                "content": self._build_initial_prompt(
                    user_prompt, context, has_conversation_history
                ),
            }
        )

        code_history = []
        observations = []
        final_result = None
        is_complete = False

        for iteration in range(max_iterations):
            current_iter = iteration + 1

            # Yield: Thinking
            yield self._create_status(
                AgentStatusType.THINKING,
                f"Iteration {current_iter}: Reasoning about the problem",
                iteration=current_iter,
                total_iterations=max_iterations,
            )

            logger.debug(
                "ReAct iteration",
                agent=self.agent_name,
                iteration=current_iter,
            )

            # Get LLM response
            try:
                # Yield: Generating code
                yield self._create_status(
                    AgentStatusType.GENERATING_CODE,
                    f"Iteration {current_iter}: Generating code",
                    iteration=current_iter,
                    total_iterations=max_iterations,
                )

                response = await self.llm.simple_call(
                    messages=messages,
                    json_mode=True,
                )

                thoughts = response.get("thoughts", "")
                code = response.get("code", "")
                final_answer = response.get("final_answer", False)

                # If no code was generated
                if not code:
                    logger.info(
                        "No code generated in this iteration",
                        iteration=current_iter,
                        final_answer=final_answer,
                        thoughts=thoughts[:100] if thoughts else "",
                    )

                    # If the agent signals completion without code, that's valid
                    if final_answer:
                        logger.info(
                            "Agent signaled completion without code",
                            iteration=current_iter,
                        )
                        # Store this as a text-only response
                        observations.append(f"Agent response (no code): {thoughts}")
                        final_result = thoughts  # Use thoughts as the final result
                        is_complete = True
                        break

                    # Otherwise, add thoughts to conversation and continue
                    logger.debug(
                        "No code but not final answer, continuing loop",
                        iteration=current_iter,
                    )
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Thoughts: {thoughts}\nFinal Answer: {final_answer}",
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": "You didn't generate any code. If you need to generate code to complete the task, please do so. Otherwise, if the task is complete, set final_answer to true.",
                        }
                    )
                    continue  # Skip to next iteration

                logger.debug(
                    "Code generated",
                    iteration=current_iter,
                    thoughts=thoughts[:100],
                    final_answer=final_answer,
                )

                # Yield: Executing
                yield self._create_status(
                    AgentStatusType.EXECUTING,
                    f"Iteration {current_iter}: Executing code",
                    iteration=current_iter,
                    total_iterations=max_iterations,
                    data={"thoughts": thoughts, "code": code},
                )

                # Execute code
                execution_result = await self._execute_code(code, context)

                code_history.append(
                    {
                        "iteration": current_iter,
                        "thoughts": thoughts,
                        "code": code,
                        "success": execution_result["success"],
                        "output": execution_result.get("output"),
                        "error": execution_result.get("error"),
                        "final_answer": final_answer,
                    }
                )

                # If execution succeeded
                if execution_result["success"]:
                    output_val = execution_result["output"]

                    # Handle DataFrame/Series for formatted output
                    output_str = "No return value"
                    if output_val is not None:
                        # Check for pandas DataFrame/Series via duck typing to avoid hard dependency
                        if hasattr(output_val, "to_markdown"):
                            try:
                                # Use markdown for better readability in generic agents
                                output_str = output_val.head().to_markdown(index=False)
                            except Exception:
                                output_str = str(output_val)
                        else:
                            output_str = str(output_val)

                    logs_str = execution_result.get("logs", "")

                    observation_parts = ["Code executed successfully."]
                    if logs_str:
                        observation_parts.append(f"Stdout:\n{logs_str}")
                    if output_val is not None:
                        observation_parts.append(f"Return Value:\n{output_str}")
                    elif not logs_str:
                        observation_parts.append("No output or return value.")

                    observation = "\n".join(observation_parts)
                    observations.append(observation)
                    final_result = output_val

                    # Yield: Iteration complete
                    yield self._create_status(
                        AgentStatusType.ITERATION_COMPLETE,
                        f"Iteration {current_iter}: Code executed successfully",
                        iteration=current_iter,
                        total_iterations=max_iterations,
                        data={
                            "success": True,
                            "final_answer": final_answer,
                            "output": output_str,  # Use string/markdown for visibility in trace
                        },
                    )

                    # Check if agent signals completion
                    if final_answer:
                        logger.info(
                            "Agent signaled completion with final_answer=true",
                            iteration=current_iter,
                        )
                        is_complete = True
                        break

                    # Otherwise, continue for progressive refinement
                    logger.debug(
                        "Code succeeded but final_answer=false, continuing for refinement",
                        iteration=current_iter,
                    )

                    # Add observation and ask if more work needed
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Thoughts: {thoughts}\nCode:\n```python\n{code}\n```\nFinal Answer: {final_answer}",
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Observation: {observation}\n\nThe code executed successfully. If the task is complete, set final_answer to true. Otherwise, continue refining the solution.",
                        }
                    )
                else:
                    # Execution failed
                    logs_str = execution_result.get("logs", "")
                    observation_parts = ["Code execution failed."]
                    if logs_str:
                        observation_parts.append(f"Stdout:\n{logs_str}")
                    observation_parts.append(f"Error:\n{execution_result['error']}")

                    observation = "\n".join(observation_parts)
                    observations.append(observation)

                    # Yield: Iteration complete with error
                    yield self._create_status(
                        AgentStatusType.ITERATION_COMPLETE,
                        f"Iteration {current_iter}: Execution failed, will retry",
                        iteration=current_iter,
                        total_iterations=max_iterations,
                        data={
                            "success": False,
                            "error": execution_result["error"][:200],
                        },
                    )

                    # Add observation to messages for next iteration
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Thoughts: {thoughts}\nCode:\n```python\n{code}\n```",
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Observation: {observation}\n\nPlease fix the error and try again. Return JSON with thoughts, code, and final_answer.",
                        }
                    )

                    logger.debug(
                        "Code execution failed, retrying",
                        iteration=current_iter,
                        error=execution_result["error"][:200],
                    )

            except Exception as e:
                logger.error(
                    "ReAct iteration failed",
                    iteration=current_iter,
                    error=str(e),
                    exc_info=True,
                )
                observations.append(f"Iteration {current_iter} failed: {str(e)}")

                # Yield: Error
                yield self._create_status(
                    AgentStatusType.ERROR,
                    f"Iteration {current_iter}: Error - {str(e)[:100]}",
                    iteration=current_iter,
                    total_iterations=max_iterations,
                    data={"error": str(e)},
                )
                break

        # Store in session if provided
        if session_id:
            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=user_prompt,
            )
            await self.memory.add_message(
                session_id=session_id,
                role="assistant",
                content=str(final_result) if final_result else "No result",
                metadata={
                    "agent": self.agent_name,
                    "iterations": len(code_history),
                    "code_history": code_history,
                    "is_complete": is_complete,
                },
            )

        logger.info(
            "CodingAgent execution completed",
            agent=self.agent_name,
            iterations=len(code_history),
            success=is_complete or final_result is not None,
            is_complete=is_complete,
        )

        # Serialize final result for JSON safety
        serialized_final_result = self._serialize_result(final_result)

        # Success = agent signaled completion OR produced a result
        execution_success = is_complete or final_result is not None

        # If no success after max iterations, yield an error status
        if not execution_success:
            yield self._create_status(
                AgentStatusType.ERROR,
                f"{self.agent_name}: Max iterations reached without success",
                iteration=len(code_history),
                total_iterations=max_iterations,
                data={"error": "No valid result produced after max iterations"},
            )

        # Yield: Completed with final result
        yield self._create_status(
            AgentStatusType.COMPLETED,
            f"{self.agent_name} completed",
            iteration=len(code_history),
            total_iterations=max_iterations,
            data={
                "success": execution_success,
                "result": serialized_final_result,
                "context": context,
                "code_history": code_history,
                "observations": observations,
                "iterations": len(code_history),
                "is_complete": is_complete,
            },
        )

    async def execute(
        self,
        user_prompt: str,
        context: dict[str, Any] | None = None,
        max_iterations: int = 5,
        session_id: str | None = None,
        include_context: bool = False,
    ) -> dict[str, Any]:
        """
        Execute the coding agent and return final result.

        Non-streaming version that consumes all yields and returns the final result.
        Use execute_stream() for real-time progress updates.

        Args:
            user_prompt: User's request/question
            context: Additional context (file IDs, data, etc.)
            max_iterations: Maximum ReAct iterations
            session_id: Optional session ID for memory
            include_context: Include conversation history from session

        Returns:
            Dict with final result, code history, and metadata
        """
        final_status = None
        async for status in self.execute_stream(
            user_prompt=user_prompt,
            context=context,
            max_iterations=max_iterations,
            session_id=session_id,
            include_context=include_context,
        ):
            final_status = status

        if final_status and final_status.data:
            return final_status.data

        return {
            "success": False,
            "result": None,
            "code_history": [],
            "observations": [],
            "iterations": 0,
            "is_complete": False,
        }

    def _parse_function_info(self, function: Any) -> dict[str, Any]:
        """
        Parse function information for prompt inclusion.

        Args:
            function: Function object to parse
        Returns:
            Dict with function name, parameters, and docstring
        """
        import inspect

        func_name = function.__name__
        sig = inspect.signature(function)
        params = [
            {
                "name": name,
                "type": (
                    str(param.annotation)
                    if param.annotation != inspect.Parameter.empty
                    else "Any"
                ),
                "default": (
                    param.default if param.default != inspect.Parameter.empty else None
                ),
            }
            for name, param in sig.parameters.items()
        ]
        docstring = inspect.getdoc(function) or ""

        return {
            "name": func_name,
            "parameters": params,
            "docstring": docstring,
        }

    def _serialize_result(self, result: Any) -> Any:
        """
        Serialize a result for JSON safety.

        Handles special types like matplotlib Figures, DataFrames, etc.

        Args:
            result: The result to serialize

        Returns:
            JSON-serializable representation of the result
        """
        if result is None:
            return None

        # Check for matplotlib Figure (duck typing to avoid import)
        if hasattr(result, "savefig") and hasattr(result, "get_axes"):
            try:
                import base64
                import io

                # Save figure to bytes buffer
                buf = io.BytesIO()
                result.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode("utf-8")
                buf.close()

                # Close the figure to free memory
                try:
                    import matplotlib.pyplot as plt

                    plt.close(result)
                except Exception:
                    pass

                return {
                    "type": "matplotlib_figure",
                    "format": "base64_png",
                    "data": img_base64,
                }
            except Exception as e:
                logger.warning(
                    "Failed to serialize matplotlib figure",
                    error=str(e),
                )
                return f"<matplotlib.figure.Figure: serialization failed - {e}>"

        # Check for pandas DataFrame/Series
        if hasattr(result, "to_dict"):
            try:
                return result.to_dict(orient="records")
            except TypeError:
                try:
                    return result.to_dict()
                except Exception:
                    return str(result)

        # Check for plotly Figure
        if (
            hasattr(result, "to_json")
            and hasattr(result, "data")
            and hasattr(result, "layout")
        ):
            try:
                import json

                return {
                    "type": "plotly_figure",
                    "format": "json",
                    "data": json.loads(result.to_json()),
                }
            except Exception as e:
                logger.warning(
                    "Failed to serialize plotly figure",
                    error=str(e),
                )
                return f"<plotly.graph_objects.Figure: serialization failed - {e}>"

        # Check for numpy arrays
        if hasattr(result, "tolist"):
            try:
                return result.tolist()
            except Exception:
                return str(result)

        # Check if it's already a JSON-safe type
        if isinstance(result, (dict, list, str, int, float, bool)):
            return result

        # Default: convert to string
        return str(result)

    def _parse_dataframe_info(self, df: pd.DataFrame) -> str:
        """
        Parse DataFrame information for prompt inclusion.

        Args:
            df: DataFrame object to parse
        Returns:
            String summary of DataFrame structure
        """
        info_lines = [f"DataFrame with {df.shape[0]} rows and {df.shape[1]} columns."]
        info_lines.append("Columns:")
        for col in df.columns:
            info_lines.append(
                f"- {col}: {df[col].dtype}, Sample Data: {df[col].head(3).tolist()}"
            )
        return "\n".join(info_lines)

    def _build_initial_prompt(
        self,
        user_prompt: str,
        context: dict[str, Any] | None,
        has_conversation_history: bool = False,
    ) -> str:
        """
        Build the initial user prompt with context.

        Args:
            user_prompt: User's request
            context: Additional context
            has_conversation_history: Whether prior conversation exists

        Returns:
            Formatted prompt string
        """
        prompt_parts = [user_prompt]

        if context:
            prompt_parts.append("\nContext:")
            for key, value in context.items():
                # Don't include large objects in prompt text
                if isinstance(value, (str, int, float, bool)):
                    prompt_parts.append(f"- {key}: {value}")
                elif hasattr(value, "__name__") and callable(value):
                    logger.debug(
                        "Parsing function for prompt", function_name=value.__name__
                    )
                    func_info = self._parse_function_info(value)
                    param_str = ", ".join(
                        [
                            f"{p['name']}: {p['type']}"
                            + (f" = {p['default']}" if p["default"] is not None else "")
                            for p in func_info["parameters"]
                        ]
                    )
                    prompt_parts.append(
                        f"- {key}: function {func_info['name']}({param_str})\n  Docstring: {func_info['docstring']}"
                    )
                elif isinstance(value, pd.DataFrame):
                    logger.debug("Parsing DataFrame for prompt", key=key)
                    df_info = self._parse_dataframe_info(value)
                    prompt_parts.append(f"- {key}: {df_info}")
                else:
                    prompt_parts.append(f"- {key}: <{type(value).__name__} object>")

        # Context-aware instructions
        if has_conversation_history:
            prompt_parts.append(
                "\n\nReview the conversation history above. If relevant prior results exist, "
                "use them directly instead of recomputing. Then address this request."
            )
        else:
            prompt_parts.append(
                "\n\nPlease think through the problem and generate code to solve it."
            )

        prompt_parts.append("Return your response as JSON with these fields:")
        prompt_parts.append("- 'thoughts': Your reasoning about the problem")
        prompt_parts.append("- 'code': Python code to execute")
        prompt_parts.append(
            "- 'final_answer': Set to true when the task is complete, false if you need more iterations"
        )

        return "\n".join(prompt_parts)

    async def _execute_code(
        self,
        code: str,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Execute generated code in sandbox.

        Args:
            code: Python code to execute
            context: Execution context

        Returns:
            Execution result with success status, output, or error
        """
        import asyncio

        try:
            # Execute synchronously in thread pool
            result = await asyncio.to_thread(self.executor.execute, code, context or {})

            if result.success:
                return {
                    "success": True,
                    "output": result.output,
                    "logs": "\n".join(result.logs) if result.logs else "",
                }
            else:
                return {
                    "success": False,
                    "error": result.error or "Unknown error",
                    "logs": "\n".join(result.logs) if result.logs else "",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
