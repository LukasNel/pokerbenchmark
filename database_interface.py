from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from database_models import (
    PlayerModel, SessionModel, HandModel, PlayerHandModel, ActionModel,
    PlayerStatsModel, HandSummaryModel, SessionSummaryModel, HandDetailModel
)

class DatabaseInterface(ABC):
    """Abstract interface for database operations"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection"""
        pass
    
    @abstractmethod
    async def init_schema(self) -> None:
        """Initialize database schema/tables"""
        pass
    
    # Player operations
    @abstractmethod
    async def create_player(self, player: PlayerModel) -> PlayerModel:
        """Create a new player and return with ID"""
        pass
    
    @abstractmethod
    async def get_player(self, player_id: int) -> Optional[PlayerModel]:
        """Get player by ID"""
        pass
    
    @abstractmethod
    async def get_player_by_name(self, name: str) -> Optional[PlayerModel]:
        """Get player by name"""
        pass
    
    @abstractmethod
    async def list_players(self) -> List[PlayerModel]:
        """List all players"""
        pass
    
    # Session operations
    @abstractmethod
    async def create_session(self, session: SessionModel) -> SessionModel:
        """Create a new session and return with ID"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: int) -> Optional[SessionModel]:
        """Get session by ID"""
        pass
    
    @abstractmethod
    async def update_session(self, session: SessionModel) -> SessionModel:
        """Update session details"""
        pass
    
    @abstractmethod
    async def list_sessions(self) -> List[SessionModel]:
        """List all sessions"""
        pass
    
    # Hand operations
    @abstractmethod
    async def create_hand(self, hand: HandModel) -> HandModel:
        """Create a new hand and return with ID"""
        pass
    
    @abstractmethod
    async def get_hand(self, hand_id: int) -> Optional[HandModel]:
        """Get hand by ID"""
        pass
    
    @abstractmethod
    async def get_hands_by_session(self, session_id: int) -> List[HandModel]:
        """Get all hands for a session"""
        pass
    
    # Player hand operations
    @abstractmethod
    async def create_player_hand(self, player_hand: PlayerHandModel) -> PlayerHandModel:
        """Create player hand record"""
        pass
    
    @abstractmethod
    async def get_player_hands_by_hand(self, hand_id: int) -> List[PlayerHandModel]:
        """Get all player hands for a specific hand"""
        pass
    
    @abstractmethod
    async def get_player_hands_by_player(self, player_id: int) -> List[PlayerHandModel]:
        """Get all hands for a specific player"""
        pass
    
    # Action operations
    @abstractmethod
    async def create_action(self, action: ActionModel) -> ActionModel:
        """Create a new action record"""
        pass
    
    @abstractmethod
    async def get_actions_by_hand(self, hand_id: int) -> List[ActionModel]:
        """Get all actions for a specific hand"""
        pass
    
    @abstractmethod
    async def get_actions_by_player(self, player_id: int) -> List[ActionModel]:
        """Get all actions for a specific player"""
        pass
    
    # Statistics and aggregations
    @abstractmethod
    async def get_player_stats(self, player_id: int) -> Optional[PlayerStatsModel]:
        """Get comprehensive player statistics"""
        pass
    
    @abstractmethod
    async def get_all_player_stats(self) -> List[PlayerStatsModel]:
        """Get statistics for all players"""
        pass
    
    @abstractmethod
    async def get_session_summary(self, session_id: int) -> Optional[SessionSummaryModel]:
        """Get session summary with key metrics"""
        pass
    
    @abstractmethod
    async def get_hand_summaries(self, session_id: int) -> List[HandSummaryModel]:
        """Get hand summaries for a session"""
        pass
    
    @abstractmethod
    async def get_hand_detail(self, hand_id: int) -> Optional[HandDetailModel]:
        """Get complete hand details with all players and actions"""
        pass
    
    # Advanced queries
    @abstractmethod
    async def get_player_win_percentage_over_time(self, player_id: int) -> List[Dict[str, Any]]:
        """Get win percentage progression over time"""
        pass
    
    @abstractmethod
    async def get_model_comparison_stats(self) -> List[Dict[str, Any]]:
        """Compare performance across different AI models"""
        pass
    
    @abstractmethod
    async def get_recent_hands(self, limit: int = 10) -> List[HandSummaryModel]:
        """Get most recent hands across all sessions"""
        pass
    
    @abstractmethod
    async def search_hands(self, 
                          session_id: Optional[int] = None,
                          player_id: Optional[int] = None,
                          min_pot_size: Optional[int] = None,
                          max_pot_size: Optional[int] = None,
                          winner_id: Optional[int] = None,
                          limit: int = 100) -> List[HandSummaryModel]:
        """Search hands with various filters"""
        pass