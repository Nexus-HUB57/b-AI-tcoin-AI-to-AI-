"""
BAIT Investment Pipeline — Phase State Machine
===============================================
Manages the lifecycle of the investment pipeline through phases:
  IDLE → PHASE_1_DEPLOY → PHASE_2_LIQUIDITY → PHASE_3_INCREMENTAL → DEPLOYED

Each phase has entry/exit actions and transition guards.
State is persisted to disk for crash recovery.
"""

import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from config import Phase, PipelineConfig


class TransitionResult(Enum):
    SUCCESS = "success"
    GUARD_FAILED = "guard_failed"
    ALREADY_IN_PHASE = "already_in_phase"
    ERROR = "error"


class PhaseStateMachine:
    """
    State machine for the investment pipeline.
    
    Legal transitions:
      IDLE → PHASE_1_DEPLOY
      PHASE_1_DEPLOY → PHASE_2_LIQUIDITY
      PHASE_1_DEPLOY → ERROR
      PHASE_2_LIQUIDITY → PHASE_3_INCREMENTAL
      PHASE_2_LIQUIDITY → DEPLOYED  (skip phase 3 if desired)
      PHASE_2_LIQUIDITY → ERROR
      PHASE_3_INCREMENTAL → DEPLOYED
      PHASE_3_INCREMENTAL → ERROR
      * → PAUSED  (any state can pause)
      PAUSED → <previous_state>  (resume)
      ERROR → <previous_state>  (retry)
    """
    
    LEGAL_TRANSITIONS = {
        Phase.IDLE: [Phase.PHASE_1_DEPLOY],
        Phase.PHASE_1_DEPLOY: [Phase.PHASE_2_LIQUIDITY, Phase.ERROR, Phase.PAUSED],
        Phase.PHASE_2_LIQUIDITY: [Phase.PHASE_3_INCREMENTAL, Phase.DEPLOYED, Phase.ERROR, Phase.PAUSED],
        Phase.PHASE_3_INCREMENTAL: [Phase.DEPLOYED, Phase.ERROR, Phase.PAUSED],
        Phase.DEPLOYED: [Phase.PAUSED],
        Phase.PAUSED: [],  # Dynamic — can resume to previous
        Phase.ERROR: [],    # Dynamic — can retry to previous
    }
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._state = Phase.IDLE
        self._previous_state: Optional[Phase] = None
        self._phase_data: Dict[str, Any] = {}
        self._transition_history: List[Dict] = []
        self._guards: Dict[Phase, List[Callable]] = {}
        self._on_enter: Dict[Phase, List[Callable]] = {}
        self._on_exit: Dict[Phase, List[Callable]] = {}
        self._load_state()
    
    @property
    def current_phase(self) -> Phase:
        return self._state
    
    @property
    def previous_phase(self) -> Optional[Phase]:
        return self._previous_state
    
    @property
    def phase_data(self) -> Dict[str, Any]:
        return self._phase_data
    
    @property
    def is_terminal(self) -> bool:
        return self._state in (Phase.DEPLOYED, Phase.ERROR)
    
    def register_guard(self, phase: Phase, guard: Callable[[], bool]):
        """Register a guard function that must return True for transition to phase"""
        self._guards.setdefault(phase, []).append(guard)
    
    def register_on_enter(self, phase: Phase, action: Callable):
        """Register an action to execute when entering a phase"""
        self._on_enter.setdefault(phase, []).append(action)
    
    def register_on_exit(self, phase: Phase, action: Callable):
        """Register an action to execute when exiting a phase"""
        self._on_exit.setdefault(phase, []).append(action)
    
    def _check_guards(self, target: Phase) -> bool:
        """Check all guards for the target phase"""
        guards = self._guards.get(target, [])
        for guard in guards:
            try:
                if not guard():
                    return False
            except Exception:
                return False
        return True
    
    def transition(self, target: Phase, data: Optional[Dict] = None) -> TransitionResult:
        """
        Attempt a state transition.
        
        Args:
            target: Target phase
            data: Optional data to associate with this transition
            
        Returns:
            TransitionResult indicating success or failure reason
        """
        if self._state == target:
            return TransitionResult.ALREADY_IN_PHASE
        
        # Special handling for PAUSED and ERROR (can resume/retry)
        if target == Phase.PAUSED:
            self._previous_state = self._state
            self._execute_exit(self._state)
            self._state = Phase.PAUSED
            self._record_transition(target, data)
            self._execute_enter(Phase.PAUSED)
            self._save_state()
            return TransitionResult.SUCCESS
        
        if target == Phase.ERROR:
            self._previous_state = self._state
            self._execute_exit(self._state)
            self._state = Phase.ERROR
            self._record_transition(target, data)
            self._execute_enter(Phase.ERROR)
            self._save_state()
            return TransitionResult.SUCCESS
        
        # Resume from PAUSED
        if self._state == Phase.PAUSED and self._previous_state:
            # Can resume to the previous state
            self._state = self._previous_state
            self._previous_state = Phase.PAUSED
            self._record_transition(self._state, data)
            self._save_state()
            return TransitionResult.SUCCESS
        
        # Resume from ERROR (retry)
        if self._state == Phase.ERROR and self._previous_state:
            self._state = self._previous_state
            self._previous_state = Phase.ERROR
            self._record_transition(self._state, data)
            self._save_state()
            return TransitionResult.SUCCESS
        
        # Normal transition check
        legal_targets = self.LEGAL_TRANSITIONS.get(self._state, [])
        if target not in legal_targets:
            return TransitionResult.GUARD_FAILED
        
        # Check registered guards
        if not self._check_guards(target):
            return TransitionResult.GUARD_FAILED
        
        # Execute transition
        self._execute_exit(self._state)
        self._previous_state = self._state
        self._state = target
        if data:
            self._phase_data.update(data)
        self._record_transition(target, data)
        self._execute_enter(target)
        self._save_state()
        
        return TransitionResult.SUCCESS
    
    def _execute_exit(self, phase: Phase):
        for action in self._on_exit.get(phase, []):
            try:
                action()
            except Exception:
                pass  # Don't block transition on exit action failure
    
    def _execute_enter(self, phase: Phase):
        for action in self._on_enter.get(phase, []):
            try:
                action()
            except Exception:
                pass  # Log but don't block
    
    def _record_transition(self, target: Phase, data: Optional[Dict]):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from": self._previous_state.value if self._previous_state else None,
            "to": target.value,
            "data": data or {}
        }
        self._transition_history.append(record)
    
    def _save_state(self):
        """Persist state to disk for crash recovery"""
        state = {
            "current_phase": self._state.value,
            "previous_phase": self._previous_state.value if self._previous_state else None,
            "phase_data": self._phase_data,
            "transition_history": self._transition_history[-100:],  # Keep last 100
            "saved_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            with open(self.config.monitoring.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass  # Don't crash on save failure
    
    def _load_state(self):
        """Load persisted state from disk"""
        try:
            with open(self.config.monitoring.state_file, 'r') as f:
                state = json.load(f)
            self._state = Phase(state["current_phase"])
            if state.get("previous_phase"):
                self._previous_state = Phase(state["previous_phase"])
            self._phase_data = state.get("phase_data", {})
            self._transition_history = state.get("transition_history", [])
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            # Fresh start
            self._state = Phase.IDLE
    
    def get_status(self) -> Dict[str, Any]:
        """Get full status report"""
        return {
            "current_phase": self._state.value,
            "previous_phase": self._previous_state.value if self._previous_state else None,
            "is_terminal": self.is_terminal,
            "phase_data": self._phase_data,
            "transitions": len(self._transition_history),
            "last_transition": self._transition_history[-1] if self._transition_history else None
        }
    
    def reset(self):
        """Reset to IDLE state (use with caution)"""
        self._state = Phase.IDLE
        self._previous_state = None
        self._phase_data = {}
        self._transition_history = []
        self._save_state()
