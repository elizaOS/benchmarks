"""
OSWorld adapter for Milady benchmark server.

This adapter bridges OSWorld's PromptAgent interface to the Milady benchmark server,
allowing Milady to control desktop environments through the OSWorld framework.

Action spaces supported:
- pyautogui: Returns Python code strings for mouse/keyboard actions
- computer_13: Returns structured action dictionaries
"""

import logging
import base64
import json
import re
from typing import Any

# Adjust import path to match where this file is placed relative to mm_agents
try:
    from mm_agents.agent import PromptAgent
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../OSWorld")))
    from mm_agents.agent import PromptAgent

from milady_adapter.client import MiladyClient

logger = logging.getLogger("desktopenv.agent")


# Action mapping from Milady response to OSWorld format
def _map_to_pyautogui(params: dict[str, Any]) -> list[str]:
    """Convert Milady action params to pyautogui code strings."""
    actions: list[str] = []

    # Check for direct code in params
    code = params.get("code") or params.get("command") or params.get("value")
    if code and isinstance(code, str):
        # Clean up the code if wrapped in backticks
        code = re.sub(r"^```(?:python)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        actions.append(code.strip())
        return actions

    # Map structured actions to pyautogui code
    action_type = params.get("action_type") or params.get("action")

    if action_type == "click":
        x = params.get("x") or (params.get("coordinate", [0, 0])[0] if params.get("coordinate") else 0)
        y = params.get("y") or (params.get("coordinate", [0, 0])[1] if params.get("coordinate") else 0)
        button = params.get("button", "left")
        actions.append(f"import pyautogui; pyautogui.click({x}, {y}, button='{button}')")

    elif action_type == "double_click":
        x = params.get("x") or (params.get("coordinate", [0, 0])[0] if params.get("coordinate") else 0)
        y = params.get("y") or (params.get("coordinate", [0, 0])[1] if params.get("coordinate") else 0)
        actions.append(f"import pyautogui; pyautogui.doubleClick({x}, {y})")

    elif action_type == "type" or action_type == "text":
        text = params.get("text", "")
        # Escape quotes in text
        escaped = text.replace("'", "\\'")
        actions.append(f"import pyautogui; pyautogui.typewrite('{escaped}')")

    elif action_type == "key" or action_type == "press":
        key = params.get("key", "")
        actions.append(f"import pyautogui; pyautogui.press('{key}')")

    elif action_type == "hotkey":
        keys = params.get("keys", [])
        if isinstance(keys, str):
            keys = keys.split("+")
        keys_str = ", ".join(f"'{k.strip()}'" for k in keys)
        actions.append(f"import pyautogui; pyautogui.hotkey({keys_str})")

    elif action_type == "scroll":
        amount = params.get("amount", params.get("clicks", 3))
        x = params.get("x")
        y = params.get("y")
        if x is not None and y is not None:
            actions.append(f"import pyautogui; pyautogui.scroll({amount}, {x}, {y})")
        else:
            actions.append(f"import pyautogui; pyautogui.scroll({amount})")

    elif action_type == "move":
        x = params.get("x") or (params.get("coordinate", [0, 0])[0] if params.get("coordinate") else 0)
        y = params.get("y") or (params.get("coordinate", [0, 0])[1] if params.get("coordinate") else 0)
        actions.append(f"import pyautogui; pyautogui.moveTo({x}, {y})")

    elif action_type == "drag":
        start = params.get("start_coordinate", [0, 0])
        end = params.get("end_coordinate", [0, 0])
        actions.append(f"import pyautogui; pyautogui.moveTo({start[0]}, {start[1]}); pyautogui.drag({end[0] - start[0]}, {end[1] - start[1]})")

    elif action_type == "wait" or action_type == "sleep":
        duration = params.get("duration", params.get("seconds", 1))
        actions.append(f"import time; time.sleep({duration})")

    elif action_type == "screenshot":
        # No-op for OSWorld - screenshot is taken by the environment
        pass

    elif action_type == "done" or action_type == "finished":
        # Signal task completion - OSWorld uses DONE action
        actions.append("DONE")

    elif action_type == "fail":
        actions.append("FAIL")

    return actions


def _map_to_computer_13(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Milady action params to computer_13 structured actions."""
    actions: list[dict[str, Any]] = []

    action_type = params.get("action_type") or params.get("action")

    if action_type == "click":
        coord = params.get("coordinate") or [params.get("x", 0), params.get("y", 0)]
        actions.append({
            "action_type": "click",
            "coordinate": coord,
            "button": params.get("button", "left"),
        })

    elif action_type == "double_click":
        coord = params.get("coordinate") or [params.get("x", 0), params.get("y", 0)]
        actions.append({
            "action_type": "double_click",
            "coordinate": coord,
        })

    elif action_type == "type" or action_type == "text":
        actions.append({
            "action_type": "type",
            "text": params.get("text", ""),
        })

    elif action_type == "key" or action_type == "press":
        actions.append({
            "action_type": "key",
            "key": params.get("key", ""),
        })

    elif action_type == "hotkey":
        keys = params.get("keys", [])
        if isinstance(keys, str):
            keys = keys.split("+")
        actions.append({
            "action_type": "hotkey",
            "keys": [k.strip() for k in keys],
        })

    elif action_type == "scroll":
        actions.append({
            "action_type": "scroll",
            "coordinate": params.get("coordinate") or [params.get("x", 0), params.get("y", 0)],
            "direction": params.get("direction", "down"),
            "amount": params.get("amount", 3),
        })

    elif action_type == "drag":
        actions.append({
            "action_type": "drag",
            "start_coordinate": params.get("start_coordinate", [0, 0]),
            "end_coordinate": params.get("end_coordinate", [0, 0]),
        })

    elif action_type == "wait" or action_type == "sleep":
        actions.append({
            "action_type": "wait",
            "duration": params.get("duration", params.get("seconds", 1)),
        })

    elif action_type == "done" or action_type == "finished":
        actions.append({"action_type": "DONE"})

    elif action_type == "fail":
        actions.append({"action_type": "FAIL"})

    return actions


class MiladyOSWorldAgent(PromptAgent):
    """
    Agent that delegates decision making to a running Milady server via HTTP.

    Implements the PromptAgent interface required by OSWorld, translating
    observations to Milady context and mapping Milady responses back to
    OSWorld action format.
    """

    def __init__(
        self,
        milady_url: str = "http://localhost:3939",
        model: str = "milady-agent",
        **kwargs: Any
    ) -> None:
        super().__init__(model=model, **kwargs)
        self.client = MiladyClient(base_url=milady_url)
        self.milady_url = milady_url
        self._task_initialized = False
        self._current_task_id: str | None = None
        logger.info(f"Initialized MiladyOSWorldAgent connecting to {milady_url}")

    def call_llm(self, payload: dict[str, Any]) -> str:
        """
        Not used - we override predict() to communicate directly with Milady.

        The PromptAgent.predict() builds prompts for GPT/Claude format which
        don't match Milady's expected context format, so we bypass this entirely.
        """
        return ""

    def _reset_task(self, task_id: str) -> None:
        """Reset Milady session for a new task."""
        if self._current_task_id == task_id and self._task_initialized:
            return

        try:
            self.client.reset(task_id=task_id, benchmark="osworld")
            self._current_task_id = task_id
            self._task_initialized = True
            logger.info(f"Reset Milady session for task: {task_id}")
        except Exception as e:
            logger.warning(f"Failed to reset Milady session: {e}")

    def predict(self, instruction: str, obs: dict[str, Any]) -> tuple[str, list[Any]]:
        """
        Predict the next action(s) based on the current observation.

        Args:
            instruction: The task instruction/goal
            obs: Dictionary containing 'screenshot' (bytes), 'accessibility_tree', etc.

        Returns:
            Tuple of (thought/response text, list of actions)
        """
        # Extract task ID if available, otherwise generate one
        task_id = obs.get("task_id") or f"osworld-{hash(instruction) % 10000}"
        self._reset_task(task_id)

        # Prepare context for Milady
        context: dict[str, Any] = {
            "benchmark": "osworld",
            "task_id": task_id,
            "goal": instruction,
            "action_space": self.action_space,
            "observation": {},
        }

        # Include screenshot as base64
        if "screenshot" in obs and obs["screenshot"]:
            screenshot = obs["screenshot"]
            if isinstance(screenshot, bytes):
                context["observation"]["screenshot_base64"] = base64.b64encode(screenshot).decode("utf-8")
            elif isinstance(screenshot, str):
                # Assume already base64 encoded
                context["observation"]["screenshot_base64"] = screenshot

        # Include accessibility tree if available
        if "accessibility_tree" in obs and obs["accessibility_tree"]:
            # Truncate if too large to fit in context
            a11y_tree = obs["accessibility_tree"]
            if isinstance(a11y_tree, str) and len(a11y_tree) > 50000:
                a11y_tree = a11y_tree[:50000] + "\n... (truncated)"
            context["observation"]["accessibility_tree"] = a11y_tree

        # Include window info if available
        for key in ["active_window", "window_list", "clipboard"]:
            if key in obs and obs[key]:
                context["observation"][key] = obs[key]

        try:
            # Send to Milady
            resp = self.client.send_message(
                text=f"Task: {instruction}\n\nExecute the next action to complete this task. Analyze the screenshot and accessibility tree to determine what to do.",
                context=context,
            )

            thought = resp.thought or resp.text or "No response"
            params = resp.params

            # If no params returned, try to parse action from response text
            if not params or not params.get("action_type"):
                # Check if response contains structured action in text
                if resp.text:
                    try:
                        # Try to extract JSON from response
                        json_match = re.search(r"\{[^{}]+\}", resp.text)
                        if json_match:
                            params = json.loads(json_match.group())
                    except (json.JSONDecodeError, AttributeError):
                        pass

            # Map response to action format based on action space
            actions: list[Any] = []

            if params:
                if self.action_space == "pyautogui":
                    actions = _map_to_pyautogui(params)
                elif self.action_space in ("computer_13", "computer"):
                    actions = _map_to_computer_13(params)
                else:
                    # Default to pyautogui style
                    actions = _map_to_pyautogui(params)

            # Handle case where Milady signals completion via actions list
            if "DONE" in resp.actions or "done" in resp.actions:
                if self.action_space == "pyautogui":
                    actions = ["DONE"]
                else:
                    actions = [{"action_type": "DONE"}]

            logger.debug(f"Milady response: thought='{thought[:100]}...', actions={actions}")
            return thought, actions

        except Exception as e:
            logger.error(f"Error calling Milady: {e}", exc_info=True)
            return f"Error communicating with Milady server: {e}", []
