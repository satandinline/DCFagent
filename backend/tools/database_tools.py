"""
Database Tools for DCF Valuation Agent
Tools for database operations
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import time
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import (
    BaseTool, ToolCategory, ToolResult,
    ToolParameter, ToolCapability
)

logger = logging.getLogger(__name__)


# =============================================================================
# Add Ticker Tool
# =============================================================================

class AddTickerTool(BaseTool):
    """
    Tool for adding a stock ticker to the database
    """
    
    @property
    def name(self) -> str:
        return "add_ticker"
    
    @property
    def description(self) -> str:
        return "将股票代码添加到监控列表"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.SAVE_RESULT]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="ticker",
                type="string",
                description="股票代码（如AAPL）",
                required=True
            ),
            ToolParameter(
                name="locale",
                type="string",
                description="地区代码：US、CN等",
                required=False,
                default="US"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker', '').upper()
        locale = kwargs.get('locale', 'US')
        
        if not ticker:
            return ToolResult(
                success=False,
                error="ticker is required",
                tool_name=self.name
            )
        
        try:
            from backend.services.db_service import db_service
            
            success = db_service.insert_stock(ticker, locale)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=success,
                data={'ticker': ticker, 'locale': locale},
                metadata={'added': success},
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Add ticker error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Get Tickers Tool
# =============================================================================

class GetTickersTool(BaseTool):
    """
    Tool for retrieving all tickers from the database
    """
    
    @property
    def name(self) -> str:
        return "get_tickers"
    
    @property
    def description(self) -> str:
        return "获取数据库中所有监控的股票代码"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.QUERY_DATABASE]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="limit",
                type="integer",
                description="返回数量限制",
                required=False,
                default=100
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        limit = kwargs.get('limit', 100)
        
        try:
            from backend.services.db_service import db_service
            
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM stocks ORDER BY created_at DESC LIMIT {limit}")
                tickers = cursor.fetchall()
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={'tickers': tickers, 'count': len(tickers)},
                metadata={'limit': limit},
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Get tickers error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Save Valuation Result Tool
# =============================================================================

class SaveValuationTool(BaseTool):
    """
    Tool for saving valuation results to database
    """
    
    @property
    def name(self) -> str:
        return "save_valuation"
    
    @property
    def description(self) -> str:
        return "保存估值结果到数据库"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.SAVE_RESULT]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="ticker",
                type="string",
                description="股票代码",
                required=True
            ),
            ToolParameter(
                name="valuation_data",
                type="object",
                description="估值数据对象",
                required=True
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker', '').upper()
        valuation_data = kwargs.get('valuation_data')
        
        if not ticker or not valuation_data:
            return ToolResult(
                success=False,
                error="ticker and valuation_data are required",
                tool_name=self.name
            )
        
        try:
            from backend.services.db_service import db_service
            
            success = db_service.insert_valuation_result(ticker, valuation_data)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=success,
                data={'ticker': ticker, 'saved': success},
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Save valuation error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Get Valuation History Tool
# =============================================================================

class GetValuationHistoryTool(BaseTool):
    """
    Tool for retrieving valuation history from database
    """
    
    @property
    def name(self) -> str:
        return "get_valuation_history"
    
    @property
    def description(self) -> str:
        return "获取股票的估值历史记录"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.QUERY_DATABASE]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="ticker",
                type="string",
                description="股票代码",
                required=False,
                default=None
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回记录数",
                required=False,
                default=50
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker')
        limit = kwargs.get('limit', 50)
        
        try:
            from backend.services.db_service import db_service
            
            if ticker:
                history = db_service.get_valuation_history(ticker.upper(), limit)
            else:
                history = db_service.get_all_valuation_history(limit)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={'history': history, 'count': len(history)},
                metadata={'ticker': ticker, 'limit': limit},
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Get valuation history error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Get Recommendations Tool
# =============================================================================

class GetRecommendationsTool(BaseTool):
    """
    Tool for retrieving portfolio recommendations from database
    """
    
    @property
    def name(self) -> str:
        return "get_recommendations"
    
    @property
    def description(self) -> str:
        return "获取投资组合推荐建议"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.QUERY_DATABASE]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="limit",
                type="integer",
                description="返回推荐数量",
                required=False,
                default=50
            ),
            ToolParameter(
                name="action_filter",
                type="string",
                description="过滤动作：BUY、HOLD、SELL",
                required=False,
                default=None
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        limit = kwargs.get('limit', 50)
        action_filter = kwargs.get('action_filter')
        
        try:
            from backend.services.db_service import db_service
            
            conn = db_service.get_connection()
            
            if action_filter:
                query = """
                    SELECT * FROM portfolio_recommendations 
                    WHERE action = %s
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                with conn.cursor() as cursor:
                    cursor.execute(query, (action_filter, limit))
                    recommendations = cursor.fetchall()
            else:
                query = """
                    SELECT * FROM portfolio_recommendations 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                with conn.cursor() as cursor:
                    cursor.execute(query, (limit,))
                    recommendations = cursor.fetchall()
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={'recommendations': recommendations, 'count': len(recommendations)},
                metadata={'limit': limit, 'action_filter': action_filter},
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Get recommendations error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Register database tools
# =============================================================================

def register_database_tools():
    """Register all database tools to the global registry"""
    from backend.tools.registry import tool_registry
    
    tools = [
        AddTickerTool(),
        GetTickersTool(),
        SaveValuationTool(),
        GetValuationHistoryTool(),
        GetRecommendationsTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)
    
    return tools
