"""Wizard engine — pure logic, zero Telegram imports.

Keeping navigation, validation and pruning here means the whole conversation can be
walked and tested headlessly (see tests/test_engine.py). Handlers stay thin.

State is a plain dict so it survives pickling by PTB's persistence layer across
restarts — a half-finished intake is never lost because the bot was redeployed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .flow import FLOW, STEPS_BY_ID, Step, visible_steps
from .validators import VALIDATORS

MODE_WIZARD = "wizard"
MODE_REVIEW = "review"
MODE_EDIT = "edit"
MODE_DONE = "done"


@dataclass
class StepResult:
    ok: bool
    error: str = ""
    finished: bool = False  # the user reached the end of the questions


def new_state() -> dict[str, Any]:
    return {
        "answers": {},
        "buffer": {},          # step_id -> list of selected keys (multi-select in progress)
        "step": FLOW[0].id,
        "mode": MODE_WIZARD,
        "version": 1,
    }


class Wizard:
    """Thin behaviour wrapper around the state dict."""

    def __init__(self, state: dict[str, Any]):
        self.state = state

    # -- accessors ---------------------------------------------------------
    @property
    def answers(self) -> dict[str, Any]:
        return self.state["answers"]

    @property
    def mode(self) -> str:
        return self.state.get("mode", MODE_WIZARD)

    @mode.setter
    def mode(self, value: str) -> None:
        self.state["mode"] = value

    @property
    def path(self) -> list[Step]:
        return visible_steps(self.answers)

    @property
    def step(self) -> Step | None:
        step_id = self.state.get("step")
        step = STEPS_BY_ID.get(step_id) if step_id else None
        if step is None:
            return None
        # A branch change can make the current step irrelevant; snap back onto the path.
        if not step.visible(self.answers):
            return self._first_unanswered() or None
        return step

    def position(self) -> tuple[int, int]:
        """(current index starting at 1, total steps on this path)."""
        path = self.path
        step = self.step
        total = len(path)
        if step is None:
            return total, total
        for index, candidate in enumerate(path, start=1):
            if candidate.id == step.id:
                return index, total
        return total, total

    # -- navigation --------------------------------------------------------
    def _first_unanswered(self) -> Step | None:
        for step in self.path:
            if step.id not in self.answers:
                return step
        return None

    def _advance(self) -> StepResult:
        """Move to the next unanswered step, or finish."""
        if self.mode == MODE_EDIT:
            self.mode = MODE_REVIEW
            self.state["step"] = None
            return StepResult(ok=True, finished=True)

        path = self.path
        current_id = self.state.get("step")
        index = next((i for i, s in enumerate(path) if s.id == current_id), -1)
        for step in path[index + 1:]:
            if step.id not in self.answers:
                self.state["step"] = step.id
                return StepResult(ok=True)
        # Nothing left after the cursor — catch any gap created by a branch switch.
        pending = self._first_unanswered()
        if pending is not None:
            self.state["step"] = pending.id
            return StepResult(ok=True)
        self.mode = MODE_REVIEW
        self.state["step"] = None
        return StepResult(ok=True, finished=True)

    def back(self) -> bool:
        """Step backwards. Returns False when already at the first question."""
        path = self.path
        if self.mode == MODE_REVIEW:
            if not path:
                return False
            self.mode = MODE_WIZARD
            self.state["step"] = path[-1].id
            self.state["buffer"].pop(path[-1].id, None)
            return True
        if self.mode == MODE_EDIT:
            self.mode = MODE_REVIEW
            self.state["step"] = None
            return True
        current_id = self.state.get("step")
        index = next((i for i, s in enumerate(path) if s.id == current_id), 0)
        if index <= 0:
            return False
        previous = path[index - 1]
        self.state["step"] = previous.id
        self.state["buffer"].pop(previous.id, None)
        return True

    def goto(self, step_id: str, *, mode: str = MODE_EDIT) -> bool:
        step = STEPS_BY_ID.get(step_id)
        if step is None or not step.visible(self.answers):
            return False
        self.state["step"] = step_id
        self.mode = mode
        self.state["buffer"].pop(step_id, None)
        return True

    # -- answering ---------------------------------------------------------
    def answer_choice(self, step_id: str, key: str) -> StepResult:
        step = STEPS_BY_ID.get(step_id)
        if step is None or step.kind != "choice":
            return StepResult(False, "این گزینه دیگر معتبر نیست.")
        if not any(option.key == key for option in step.options):
            return StepResult(False, "این گزینه دیگر معتبر نیست.")
        previous = self.answers.get(step_id)
        self.answers[step_id] = key
        if previous != key:
            self._prune()
        return self._advance()

    def toggle_multi(self, step_id: str, key: str) -> StepResult:
        step = STEPS_BY_ID.get(step_id)
        if step is None or step.kind != "multi":
            return StepResult(False, "این گزینه دیگر معتبر نیست.")
        if not any(option.key == key for option in step.options):
            return StepResult(False, "این گزینه دیگر معتبر نیست.")
        selected: list[str] = list(self.selection(step_id))
        if key in selected:
            selected.remove(key)
        else:
            # An explicit "none of these" answer is mutually exclusive with the rest.
            if key == "none":
                selected = []
            else:
                selected = [item for item in selected if item != "none"]
            selected.append(key)
        self.state["buffer"][step_id] = selected
        return StepResult(ok=True)

    def confirm_multi(self, step_id: str) -> StepResult:
        step = STEPS_BY_ID.get(step_id)
        if step is None or step.kind != "multi":
            return StepResult(False, "این گزینه دیگر معتبر نیست.")
        selected = self.selection(step_id)
        if len(selected) < step.min_select:
            return StepResult(False, "لطفاً دست‌کم یک گزینه را انتخاب کنید.")
        ordered = [option.key for option in step.options if option.key in set(selected)]
        self.answers[step_id] = ordered
        self.state["buffer"].pop(step_id, None)
        return self._advance()

    def answer_text(self, step_id: str, raw: str) -> StepResult:
        step = STEPS_BY_ID.get(step_id)
        if step is None or step.kind != "text":
            return StepResult(False, "این پرسش دیگر فعال نیست.")
        validator = VALIDATORS.get(step.validator, VALIDATORS["free_text"])
        ok, value = validator(raw)
        if not ok:
            return StepResult(False, value)
        self.answers[step_id] = value
        return self._advance()

    def skip(self, step_id: str) -> StepResult:
        step = STEPS_BY_ID.get(step_id)
        if step is None or not step.optional:
            return StepResult(False, "این پرسش اختیاری نیست.")
        self.answers[step_id] = ""
        return self._advance()

    def selection(self, step_id: str) -> list[str]:
        """Current multi-select state: the in-progress buffer, else a saved answer."""
        if step_id in self.state["buffer"]:
            return list(self.state["buffer"][step_id])
        saved = self.answers.get(step_id)
        return list(saved) if isinstance(saved, list) else []

    # -- housekeeping ------------------------------------------------------
    def _prune(self) -> None:
        """Drop answers that belong to a branch the user just navigated away from."""
        allowed = {step.id for step in self.path}
        for key in [k for k in self.answers if k not in allowed]:
            self.answers.pop(key, None)
        for key in [k for k in self.state["buffer"] if k not in allowed]:
            self.state["buffer"].pop(key, None)

    def is_complete(self) -> bool:
        return all(step.id in self.answers for step in self.path)

    def missing(self) -> list[Step]:
        return [step for step in self.path if step.id not in self.answers]

    def answered_steps(self) -> list[tuple[Step, Any]]:
        return [(step, self.answers[step.id]) for step in self.path if step.id in self.answers]

    def display_value(self, step: Step) -> str:
        """Human-readable answer for the summary card."""
        value = self.answers.get(step.id)
        if value is None or value == "":
            return "—"
        if step.kind == "multi" and isinstance(value, list):
            return "، ".join(step.option_label(key) for key in value) or "—"
        if step.kind == "choice":
            return step.option_label(str(value))
        return str(value)
