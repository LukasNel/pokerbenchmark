from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ActionType(str, Enum):
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"
    CHECK = "check"

class BettingRound(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"

class PlayerModel(BaseModel):
    id: Optional[int] = None
    name: str
    model_type: str  # "openai", "anthropic", "random"
    model_name: str  # "gpt-4o", "claude-4-sonnet", etc.
    created_at: datetime = Field(default_factory=datetime.now)

class SessionModel(BaseModel):
    id: Optional[int] = None
    session_name: str
    starting_chips: int
    small_blind: int
    big_blind: int
    max_hands: int
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_hands_played: int = 0

class HandModel(BaseModel):
    id: Optional[int] = None
    session_id: int
    hand_number: int
    dealer_position: int
    pot_size: int
    community_cards: List[str]  # JSON array of card strings
    created_at: datetime = Field(default_factory=datetime.now)
    winner_ids: List[int]  # JSON array of player IDs
    winnings: Dict[int, int]  # JSON dict of player_id -> amount_won

class PlayerHandModel(BaseModel):
    id: Optional[int] = None
    hand_id: int
    player_id: int
    hole_cards: List[str]  # JSON array of 2 card strings
    starting_chips: int
    ending_chips: int
    final_position: int  # 1 = winner, 2 = second place, etc.
    folded: bool = False
    all_in: bool = False

class ActionModel(BaseModel):
    id: Optional[int] = None
    hand_id: int
    player_id: int
    betting_round: BettingRound
    action_type: ActionType
    amount: int
    pot_size_after: int
    position_in_round: int  # Order within this betting round
    reasoning: Optional[str] = None  # AI reasoning if available
    created_at: datetime = Field(default_factory=datetime.now)

class PlayerStatsModel(BaseModel):
    player_id: int
    player_name: str
    model_name: str
    total_hands: int
    hands_won: int
    win_percentage: float
    total_chips_won: int
    total_chips_lost: int
    net_profit: int
    roi: float  # Return on investment
    avg_pot_won: float
    fold_percentage: float
    call_percentage: float
    raise_percentage: float
    check_percentage: float
    preflop_aggression: float  # % of preflop raises
    postflop_aggression: float  # % of postflop raises

class HandSummaryModel(BaseModel):
    hand_id: int
    session_id: int
    hand_number: int
    pot_size: int
    community_cards: List[str]
    winner_names: List[str]
    total_winnings: int
    num_players: int
    num_actions: int
    betting_rounds_completed: int
    created_at: datetime

class SessionSummaryModel(BaseModel):
    session_id: int
    session_name: str
    total_hands: int
    starting_chips: int
    final_chip_counts: Dict[str, int]  # player_name -> final_chips
    biggest_winner: str
    biggest_loser: str
    biggest_pot: int
    avg_pot_size: float
    total_duration_minutes: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]

class HandDetailModel(BaseModel):
    hand: HandModel
    players: List[PlayerHandModel]
    actions: List[ActionModel]
    session: SessionModel
    
    class Config:
        from_attributes = True