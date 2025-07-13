import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from database_interface import DatabaseInterface
from database_models import (
    PlayerModel, SessionModel, HandModel, PlayerHandModel, ActionModel,
    ActionType, BettingRound
)
from ai_players import AIPlayer

class DatabaseIntegration:
    def __init__(self, db: DatabaseInterface):
        self.db = db
        self.player_id_cache: Dict[str, int] = {}
        self.current_session_id: Optional[int] = None
        self.current_hand_id: Optional[int] = None
        self.action_position_counter: Dict[str, int] = {}  # betting_round -> position
    
    async def init_session(self, session_name: str, players: List[AIPlayer], 
                          starting_chips: int, small_blind: int, big_blind: int, 
                          max_hands: int) -> int:
        """Initialize a new session and register players"""
        
        # Create or get existing players
        for player in players:
            existing_player = await self.db.get_player_by_name(player.name)
            if existing_player:
                self.player_id_cache[player.name] = existing_player.id
            else:
                # Determine model type
                if hasattr(player, 'api_key'):
                    if 'anthropic' in player.__class__.__name__.lower():
                        model_type = "anthropic"
                    elif 'openai' in player.__class__.__name__.lower():
                        model_type = "openai"
                    else:
                        model_type = "unknown"
                else:
                    model_type = "random"
                
                new_player = PlayerModel(
                    name=player.name,
                    model_type=model_type,
                    model_name=getattr(player, 'model', 'unknown')
                )
                created_player = await self.db.create_player(new_player)
                self.player_id_cache[player.name] = created_player.id
        
        # Create session
        session = SessionModel(
            session_name=session_name,
            starting_chips=starting_chips,
            small_blind=small_blind,
            big_blind=big_blind,
            max_hands=max_hands
        )
        created_session = await self.db.create_session(session)
        self.current_session_id = created_session.id
        
        return created_session.id
    
    async def start_hand(self, session_id: int, hand_number: int, dealer_position: int,
                        hole_cards: Dict[str, List[str]], starting_chips: Dict[str, int]) -> int:
        """Start a new hand and create player_hand records"""
        
        # Create hand record (will be updated when hand completes)
        hand = HandModel(
            session_id=session_id,
            hand_number=hand_number,
            dealer_position=dealer_position,
            pot_size=0,  # Will be updated when hand completes
            community_cards=[],  # Will be updated when hand completes
            winner_ids=[],  # Will be updated when hand completes
            winnings={}  # Will be updated when hand completes
        )
        
        created_hand = await self.db.create_hand(hand)
        self.current_hand_id = created_hand.id
        
        # Create player hand records
        for player_name, cards in hole_cards.items():
            player_id = self.player_id_cache[player_name]
            player_hand = PlayerHandModel(
                hand_id=created_hand.id,
                player_id=player_id,
                hole_cards=cards,
                starting_chips=starting_chips[player_name],
                ending_chips=starting_chips[player_name],  # Will be updated when hand completes
                final_position=0,  # Will be updated when hand completes
                folded=False,
                all_in=False
            )
            await self.db.create_player_hand(player_hand)
        
        # Reset action position counter
        self.action_position_counter = {}
        
        return created_hand.id
    
    async def record_action(self, hand_id: int, player_name: str, betting_round: str,
                           action_type: str, amount: int, pot_size_after: int,
                           reasoning: Optional[str] = None) -> None:
        """Record a player action"""
        
        player_id = self.player_id_cache[player_name]
        
        # Track position in betting round
        if betting_round not in self.action_position_counter:
            self.action_position_counter[betting_round] = 0
        self.action_position_counter[betting_round] += 1
        
        action = ActionModel(
            hand_id=hand_id,
            player_id=player_id,
            betting_round=BettingRound(betting_round),
            action_type=ActionType(action_type),
            amount=amount,
            pot_size_after=pot_size_after,
            position_in_round=self.action_position_counter[betting_round],
            reasoning=reasoning
        )
        
        await self.db.create_action(action)
    
    async def complete_hand(self, hand_id: int, final_pot_size: int,
                           community_cards: List[str], winners: Dict[str, int],
                           final_chips: Dict[str, int], folded_players: set) -> None:
        """Complete a hand and update all final results"""
        
        # Update hand record
        hand = await self.db.get_hand(hand_id)
        if hand:
            winner_ids = [self.player_id_cache[name] for name in winners.keys()]
            winnings_by_id = {self.player_id_cache[name]: amount for name, amount in winners.items()}
            
            hand.pot_size = final_pot_size
            hand.community_cards = community_cards
            hand.winner_ids = winner_ids
            hand.winnings = winnings_by_id
            
            # Update hand in database
            import json
            cursor = self.db.connection.cursor()
            cursor.execute("""
                UPDATE hands SET pot_size = ?, community_cards = ?, winner_ids = ?, winnings = ?
                WHERE id = ?
            """, (final_pot_size, 
                  json.dumps(community_cards),
                  json.dumps(winner_ids),
                  json.dumps(winnings_by_id),
                  hand_id))
            self.db.connection.commit()
        
        # Update player hand records
        player_hands = await self.db.get_player_hands_by_hand(hand_id)
        winner_names = list(winners.keys())
        
        for player_hand in player_hands:
            player = await self.db.get_player(player_hand.player_id)
            player_name = player.name
            
            # Update ending chips
            player_hand.ending_chips = final_chips.get(player_name, player_hand.starting_chips)
            
            # Update final position (1 = winner, 2+ = loser)
            if player_name in winner_names:
                player_hand.final_position = 1
            else:
                player_hand.final_position = 2
            
            # Update folded status
            player_hand.folded = player_name in folded_players
            
            # Update all_in status (simple check if ending chips equals starting chips)
            player_hand.all_in = player_hand.ending_chips == 0
            
            # Update in database
            cursor = self.db.connection.cursor()
            cursor.execute("""
                UPDATE player_hands SET ending_chips = ?, final_position = ?, folded = ?, all_in = ?
                WHERE id = ?
            """, (player_hand.ending_chips, player_hand.final_position, 
                  player_hand.folded, player_hand.all_in, player_hand.id))
            self.db.connection.commit()
    
    async def complete_session(self, session_id: int, total_hands_played: int) -> None:
        """Complete a session and update final statistics"""
        
        session = await self.db.get_session(session_id)
        if session:
            session.completed_at = datetime.now()
            session.total_hands_played = total_hands_played
            await self.db.update_session(session)
    
    async def get_player_id(self, player_name: str) -> Optional[int]:
        """Get player ID from cache or database"""
        if player_name in self.player_id_cache:
            return self.player_id_cache[player_name]
        
        player = await self.db.get_player_by_name(player_name)
        if player:
            self.player_id_cache[player_name] = player.id
            return player.id
        
        return None