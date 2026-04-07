"""
ReAct (Reasoning + Acting) Nodes for DCF Valuation Agent
Implements反思循环 allows agent to think, act, observe, and adjust strategy
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import ToolResult
from backend.tools.registry import tool_registry

logger = logging.getLogger(__name__)


# =============================================================================
# ReAct State Definitions
# =============================================================================

class ReasoningStep:
    """Represents a single reasoning step"""
    step_number: int
    thought: str
    action: str
    tool_name: str
    tool_params: Dict[str, Any]
    observation: str
    reflection: str
    decision: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'step_number': self.step_number,
            'thought': self.thought,
            'action': self.action,
            'tool_name': self.tool_name,
            'tool_params': self.tool_params,
            'observation': self.observation,
            'reflection': self.reflection,
            'decision': self.decision,
            'timestamp': self.timestamp
        }


@dataclass
class ReActState:
    """
    Extended state for ReAct reasoning loop
    
    Attributes:
        reasoning_history: List of all reasoning steps taken
        current_thought: Current thought being processed
        current_strategy: Current approach/strategy being used
        strategy_adjustments: History of strategy changes
        confidence: Confidence level (high/medium/low)
        retry_count: Number of retries for current action
        max_retries: Maximum allowed retries
        failed_attempts: Failed actions and their reasons
    """
    # Reasoning tracking
    reasoning_history: List[Dict[str, Any]] = field(default_factory=list)
    current_thought: str = ""
    current_action: str = ""
    current_tool: str = ""
    current_params: Dict[str, Any] = field(default_factory=dict)
    
    # Strategy management
    current_strategy: str = "default"
    strategy_adjustments: List[Dict[str, str]] = field(default_factory=list)
    original_strategy: str = "default"
    
    # Confidence and retries
    confidence: str = "medium"  # high, medium, low
    retry_count: int = 0
    max_retries: int = 3
    
    # Failure tracking
    failed_attempts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Results
    accumulated_knowledge: Dict[str, Any] = field(default_factory=dict)
    final_decision: str = ""
    
    def add_reasoning_step(self, step: ReasoningStep):
        """Add a reasoning step to history"""
        self.reasoning_history.append(step.to_dict())
    
    def record_failure(self, tool: str, error: str, reason: str):
        """Record a failed attempt"""
        self.failed_attempts.append({
            'tool': tool,
            'error': error,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        self.retry_count += 1
    
    def adjust_strategy(self, new_strategy: str, reason: str):
        """Record strategy adjustment"""
        self.strategy_adjustments.append({
            'from': self.current_strategy,
            'to': new_strategy,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        self.current_strategy = new_strategy
    
    def reset_retries(self):
        """Reset retry counter"""
        self.retry_count = 0


# =============================================================================
# ReAct Node Functions
# =============================================================================

class ReActNodes:
    """
    ReAct loop nodes that implement the: 
    Thought -> Action -> Observation -> Reflection -> Decision cycle
    """
    
    # Strategy definitions for different scenarios
    STRATEGIES = {
        'default': {
            'description': 'Standard valuation approach',
            'primary_tools': ['yahoo_finance_fetcher', 'industry_classification', 'dcf_valuation'],
            'fallback_tools': ['yahoo_finance_fetcher', 'industry_classification', 'comparable_analysis'],
            'max_retries': 3
        },
        'financial': {
            'description': 'For financial institutions',
            'primary_tools': ['yahoo_finance_fetcher', 'industry_classification', 'ddm_valuation', 'pb_valuation'],
            'fallback_tools': ['yahoo_finance_fetcher', 'industry_classification', 'comparable_analysis'],
            'max_retries': 2
        },
        'high_growth': {
            'description': 'For high growth / unprofitable companies',
            'primary_tools': ['yahoo_finance_fetcher', 'industry_classification', 'ps_valuation'],
            'fallback_tools': ['yahoo_finance_fetcher', 'industry_classification', 'ev_revenue_valuation'],
            'max_retries': 2
        },
        'conservative': {
            'description': 'Conservative approach with multiple validations',
            'primary_tools': ['yahoo_finance_fetcher', 'industry_classification', 'dcf_valuation', 'comparable_analysis'],
            'fallback_tools': ['yahoo_finance_fetcher', 'industry_classification', 'sensitivity_analysis'],
            'max_retries': 4
        }
    }
    
    @classmethod
    def think(cls, state: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Thought step: Analyze current situation and decide what to do next
        
        This is the "Reasoning" part of ReAct - the agent thinks about what action to take.
        """
        react_state = state.get('react_state', ReActState())
        
        # Get current context
        ticker = context.get('ticker', 'UNKNOWN')
        step_number = len(react_state.reasoning_history) + 1
        
        # Build thought prompt
        thought = f"""[Step {step_number}] Analyzing situation for {ticker}:

Current situation:
- Completed steps: {len(react_state.reasoning_history)}
- Current strategy: {react_state.current_strategy}
- Failed attempts: {len(react_state.failed_attempts)}
- Confidence: {react_state.confidence}

Recent history:
{cls._format_history(react_state.reasoning_history[-3:] if react_state.reasoning_history else [])}

What should I do next?
1. Continue with current approach?
2. Try a different strategy?
3. Request more data?
4. Make final decision?"""
        
        react_state.current_thought = thought
        return thought
    
    @classmethod
    def act(cls, state: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """
        Action step: Execute the selected tool with parameters
        
        This is the "Acting" part of ReAct - actually perform an action.
        """
        react_state = state.get('react_state', ReActState())
        
        # Get action from context or determine action
        tool_name = context.get('tool_name')
        tool_params = context.get('tool_params', {})
        
        if not tool_name:
            # Auto-select tool based on strategy
            tool_name = cls._select_tool_for_strategy(
                react_state.current_strategy,
                len(react_state.reasoning_history)
            )
        
        react_state.current_tool = tool_name
        react_state.current_params = tool_params
        
        logger.info(f"ReAct Action: {tool_name} with params {tool_params}")
        
        # Execute tool
        result = tool_registry.execute(tool_name, **tool_params)
        
        return result
    
    @classmethod
    def observe(cls, state: Dict[str, Any], result: ToolResult) -> str:
        """
        Observation step: Interpret the result of the action
        
        This is the "Observation" part of ReAct - understand what happened.
        """
        react_state = state.get('react_state', ReActState())
        
        if result.success:
            observation = f"Success: {json.dumps(result.data, ensure_ascii=False)[:500]}"
            react_state.accumulated_knowledge[react_state.current_tool] = result.data
        else:
            observation = f"Failed: {result.error}"
            react_state.record_failure(
                react_state.current_tool,
                result.error,
                result.error
            )
        
        return observation
    
    @classmethod
    def reflect(cls, state: Dict[str, Any], observation: str) -> str:
        """
        Reflection step: Decide if we need to adjust strategy
        
        This is key to the "reflexion" capability - the agent thinks about 
        whether the action was helpful and if strategy needs adjustment.
        """
        react_state = state.get('react_state', ReActState())
        
        # Check if we should retry or adjust
        should_retry = False
        should_adjust_strategy = False
        adjustment_reason = ""
        
        # If observation indicates failure
        if "Failed" in observation:
            # Check retry count
            if react_state.retry_count < react_state.max_retries:
                should_retry = True
                decision = f"RETRY: Will retry with adjusted parameters (attempt {react_state.retry_count + 1}/{react_state.max_retries})"
            else:
                # Max retries reached, switch strategy
                should_adjust_strategy = True
                adjustment_reason = f"Max retries ({react_state.max_retries}) reached"
                decision = "CHANGE_STRATEGY: Switching to fallback approach"
        else:
            # Success - check if we have enough confidence
            if react_state.confidence == "low":
                # Verify with additional method
                decision = "VERIFY: Results uncertain, need additional validation"
            else:
                decision = "CONTINUE: Results satisfactory, proceeding"
        
        # Generate reflection text
        reflection = f"""Reflection on action result:
- Action: {react_state.current_tool}
- Result: {observation[:200]}
- Decision: {decision}
- Strategy adjustments so far: {len(react_state.strategy_adjustments)}"""
        
        react_state.current_action = decision
        
        return reflection
    
    @classmethod
    def decide_next(cls, state: Dict[str, Any], reflection: str) -> str:
        """
        Decision step: Decide what to do next based on reflection
        """
        react_state = state.get('react_state', ReActState())
        
        # Parse reflection decision
        if "CHANGE_STRATEGY" in reflection:
            # Switch to fallback tools
            new_strategy = cls._get_fallback_strategy(react_state.current_strategy)
            if new_strategy != react_state.current_strategy:
                react_state.adjust_strategy(new_strategy, "Primary approach failed")
            react_state.reset_retries()
            return "fetch_data"  # Loop back
        
        elif "RETRY" in reflection:
            # Will retry with different parameters
            return "retry_current"
        
        elif "VERIFY" in reflection:
            # Need additional verification
            return "verify"
        
        elif "CONTINUE" in reflection:
            # Proceed to next step
            return "continue"
        
        elif "FINISH" in reflection or len(react_state.reasoning_history) >= 10:
            # Enough analysis done
            react_state.final_decision = reflection
            return "finish"
        
        else:
            return "continue"
    
    @classmethod
    def run_reflection_loop(
        cls,
        state: Dict[str, Any],
        context: Dict[str, Any],
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Run the complete ReAct reflection loop
        
        This orchestrates the full Thought -> Action -> Observation -> Reflection -> Decision cycle
        until a final decision is reached.
        
        Returns:
            Final state with reasoning history and decision
        """
        react_state = state.get('react_state', ReActState())
        
        for iteration in range(max_iterations):
            logger.info(f"ReAct iteration {iteration + 1}/{max_iterations}")
            
            # 1. Thought
            thought = cls.think(state, context)
            logger.debug(f"Thought: {thought[:200]}...")
            
            # 2. Action
            result = cls.act(state, context)
            
            # 3. Observation
            observation = cls.observe(state, result)
            logger.debug(f"Observation: {observation[:200]}...")
            
            # 4. Reflection
            reflection = cls.reflect(state, observation)
            logger.debug(f"Reflection: {reflection[:200]}...")
            
            # 5. Decision
            decision = cls.decide_next(state, reflection)
            logger.info(f"Decision: {decision}")
            
            # Record step
            step = ReasoningStep(
                step_number=iteration + 1,
                thought=thought,
                action=react_state.current_action,
                tool_name=react_state.current_tool,
                tool_params=react_state.current_params,
                observation=observation,
                reflection=reflection,
                decision=decision,
                timestamp=datetime.now().isoformat()
            )
            react_state.add_reasoning_step(step)
            
            # Check if done
            if decision == "finish":
                break
            
            # Update state
            state['react_state'] = react_state
            state['last_decision'] = decision
        
        return {
            'final_decision': react_state.final_decision,
            'reasoning_history': react_state.reasoning_history,
            'strategy_adjustments': react_state.strategy_adjustments,
            'accumulated_knowledge': react_state.accumulated_knowledge,
            'iterations': len(react_state.reasoning_history)
        }
    
    @classmethod
    def _format_history(cls, history: List[Dict]) -> str:
        """Format reasoning history for display"""
        if not history:
            return "No previous steps"
        
        lines = []
        for step in history:
            lines.append(f"  Step {step.get('step_number')}: {step.get('tool_name')} -> {step.get('decision', 'N/A')}")
        
        return '\n'.join(lines)
    
    @classmethod
    def _select_tool_for_strategy(cls, strategy: str, step: int) -> str:
        """Select appropriate tool based on strategy and current step"""
        strategy_def = cls.STRATEGIES.get(strategy, cls.STRATEGIES['default'])
        tools = strategy_def['primary_tools']
        
        if step < len(tools):
            return tools[step]
        return tools[-1]  # Default to last tool
    
    @classmethod
    def _get_fallback_strategy(cls, current_strategy: str) -> str:
        """Get fallback strategy when primary fails"""
        fallbacks = {
            'default': 'conservative',
            'financial': 'default',
            'high_growth': 'default',
            'conservative': 'default'
        }
        return fallbacks.get(current_strategy, 'default')


class ReActWorkflowIntegration:
    """
    Integration helpers for connecting ReAct with existing workflow nodes
    """
    
    @staticmethod
    def create_react_enabled_state(initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create workflow state with ReAct support"""
        return {
            'react_state': ReActState(),
            'context': initial_context,
            'use_react': True,
            'last_decision': None
        }
    
    @staticmethod
    def extract_react_insights(result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key insights from ReAct result"""
        return {
            'iterations': result.get('iterations', 0),
            'final_strategy': result.get('reasoning_history', [{}])[-1].get('strategy') if result.get('reasoning_history') else 'unknown',
            'adjustments': len(result.get('strategy_adjustments', [])),
            'key_findings': list(result.get('accumulated_knowledge', {}).keys()),
            'reasoning_summary': cls._summarize_reasoning(result.get('reasoning_history', []))
        }
    
    @staticmethod
    def _summarize_reasoning(history: List[Dict]) -> str:
        """Create a summary of the reasoning process"""
        if not history:
            return "No reasoning recorded"
        
        successful_steps = [s for s in history if 'Success' in s.get('observation', '')]
        failed_steps = [s for s in history if 'Failed' in s.get('observation', '')]
        
        return f"Completed {len(history)} steps ({len(successful_steps)} successful, {len(failed_steps)} failed)"
