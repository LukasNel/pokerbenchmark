import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from poker_game import TexasHoldem, GameAction, PlayerAction
from ai_players import AIPlayer
from database_interface import DatabaseInterface
from database_integration import DatabaseIntegration

@dataclass
class GameResults:
    player_final_chips: Dict[str, int]
    hands_played: int
    session_duration: float
    hand_results: List[Dict[str, Any]]

@dataclass
class BenchmarkResults:
    total_hands: int
    total_sessions: int
    player_stats: Dict[str, Dict[str, Any]]
    overall_winner: str
    session_results: List[GameResults]

class GameSimulator:
    def __init__(self, players: List[AIPlayer], starting_chips: int = 1000, 
                 small_blind: int = 5, big_blind: int = 10, db: Optional[DatabaseInterface] = None):
        self.players = players
        self.player_names = [p.name for p in players]
        self.starting_chips = starting_chips
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.db = db
        self.db_integration = DatabaseIntegration(db) if db else None
        
    async def simulate_session(self, max_hands: int = 100, time_limit: int = 300, 
                              session_name: Optional[str] = None) -> GameResults:
        start_time = time.time()
        game = TexasHoldem(self.player_names, self.starting_chips, self.small_blind, self.big_blind)
        
        hands_played = 0
        hand_results = []
        session_id = None
        
        # Initialize database session if available
        if self.db_integration and session_name:
            session_id = await self.db_integration.init_session(
                session_name, self.players, self.starting_chips, 
                self.small_blind, self.big_blind, max_hands
            )
        
        print(f"  Starting chips: {', '.join(f'{p}: ${game.chips[p]}' for p in self.player_names)}")
        
        while (hands_played < max_hands and 
               time.time() - start_time < time_limit and 
               len([p for p in self.player_names if game.chips[p] > 0]) > 1):
            
            try:
                print(f"\n  Hand {hands_played + 1}:")
                hand_result = await self._play_single_hand(game, session_id, hands_played + 1)
                hand_results.append(hand_result)
                hands_played += 1
                
                # Show hand results
                winners = hand_result.get('winners', [])
                pot = hand_result.get('pot_size', 0)
                print(f"    Winner(s): {', '.join(winners)} (pot: ${pot})")
                print(f"    Current chips: {', '.join(f'{p}: ${game.chips[p]}' for p in self.player_names)}")
                
                # Update player statistics
                for player in self.players:
                    player.total_hands += 1
                    if player.name in hand_result.get('winners', []):
                        player.hands_won += 1
                        player.total_winnings += hand_result.get('winnings', {}).get(player.name, 0)
                
            except Exception as e:
                print(f"    Error in hand {hands_played + 1}: {e}")
                break
                
        session_duration = time.time() - start_time
        
        # Complete database session if available
        if self.db_integration and session_id:
            await self.db_integration.complete_session(session_id, hands_played)
        
        return GameResults(
            player_final_chips=game.chips.copy(),
            hands_played=hands_played,
            session_duration=session_duration,
            hand_results=hand_results
        )
    
    async def _play_single_hand(self, game: TexasHoldem, session_id: Optional[int] = None, 
                               hand_number: int = 0) -> Dict[str, Any]:
        game_state = game.start_hand()
        hand_actions = []
        hand_id = None
        
        # Initialize database hand if available
        if self.db_integration and session_id:
            hole_cards_str = {name: [str(card) for card in cards] 
                             for name, cards in game.hole_cards.items()}
            hand_id = await self.db_integration.start_hand(
                session_id, hand_number, game.dealer_position, 
                hole_cards_str, game.chips.copy()
            )
        
        # Play through all betting rounds
        for betting_round in ["preflop", "flop", "turn", "river"]:
            # Check if hand is complete (only 1 player left)
            if game.is_hand_complete():
                break
            
            # Advance to next community card round (except preflop)
            if betting_round != "preflop":
                game_state = game.advance_betting_round()
                if game_state is None:  # Showdown time
                    break
            
            # Show community cards for this round
            if betting_round == "preflop":
                print(f"    {betting_round.capitalize()}: (hole cards dealt, pot: ${game.pot})")
            else:
                community_str = ', '.join(str(card) for card in game_state.community_cards)
                print(f"    {betting_round.capitalize()}: {community_str} (pot: ${game.pot})")
                
            betting_complete = False
            players_who_acted = set()  # Track who has acted this round
            last_to_act = None  # Track last player to bet/raise
            
            while not betting_complete:
                active_players = [p for p in game.active_players if p not in game.folded_players]
                
                if len(active_players) <= 1:
                    betting_complete = True
                    break
                
                # Find players who need to act
                players_to_act = []
                for player in active_players:
                    if game.chips[player] > 0:  # Only players with chips can act
                        if game.current_bet == 0:
                            # No one has bet yet - everyone needs chance to act
                            if player not in players_who_acted:
                                players_to_act.append(player)
                        else:
                            # Someone has bet - need to match or exceed
                            if game.player_bets[player] < game.current_bet:
                                players_to_act.append(player)
                
                # Check if betting is complete
                if not players_to_act:
                    # If current_bet is 0 and everyone has acted, or everyone has matched bets
                    if game.current_bet == 0:
                        # Everyone checked
                        if len(players_who_acted) >= len(active_players):
                            betting_complete = True
                            break
                    else:
                        # Everyone has called/folded
                        betting_complete = True
                        break
                
                # Get actions from each player who needs to act
                for player_name in players_to_act:
                    if player_name in game.folded_players:
                        continue
                        
                    player = next(p for p in self.players if p.name == player_name)
                    hole_cards = game.hole_cards[player_name]
                    
                    try:
                        action = await asyncio.wait_for(
                            player.make_decision(game_state, hole_cards), 
                            timeout=30.0
                        )
                        
                        # Validate and process action
                        if action.action == GameAction.RAISE:
                            if action.amount <= 0:
                                action.amount = game.current_bet
                            action.amount = min(action.amount, game.chips[player_name])
                        
                        result_state = game.process_action(player_name, action)
                        if result_state:
                            game_state = result_state
                        
                        # Track that this player has acted
                        players_who_acted.add(player_name)
                        if action.action.value == "raise":
                            last_to_act = player_name
                        
                        # Show the action
                        action_str = action.action.value
                        if action.action.value == "raise":
                            total_bet = game.player_bets.get(player_name, 0) + action.amount
                            action_str += f" to ${total_bet}"
                        elif action.action.value == "call":
                            call_amount = game.current_bet - game.player_bets.get(player_name, 0)
                            if call_amount > 0:
                                action_str += f" ${call_amount}"
                            else:
                                action_str = "check"  # If call amount is 0, it's really a check
                        print(f"      {player_name}: {action_str}")
                        
                        # Record action in database
                        if self.db_integration and hand_id:
                            await self.db_integration.record_action(
                                hand_id, player_name, betting_round, action.action.value,
                                action.amount, game.pot, None  # reasoning not available yet
                            )
                            
                        hand_actions.append({
                            "player": player_name,
                            "action": action.action.value,
                            "amount": action.amount,
                            "betting_round": betting_round
                        })
                        
                    except asyncio.TimeoutError:
                        # Player took too long, force fold
                        fold_action = PlayerAction(GameAction.FOLD)
                        game.process_action(player_name, fold_action)
                        players_who_acted.add(player_name)
                        print(f"      {player_name}: fold (timeout)")
                        hand_actions.append({
                            "player": player_name,
                            "action": "fold",
                            "amount": 0,
                            "betting_round": betting_round,
                            "reason": "timeout"
                        })
                    except Exception as e:
                        print(f"      Error getting action from {player_name}: {e}")
                        # Force fold on error
                        fold_action = PlayerAction(GameAction.FOLD)
                        game.process_action(player_name, fold_action)
                        players_who_acted.add(player_name)
                        print(f"      {player_name}: fold (error)")
            
            # Betting round complete - continue to next round
        
        # Determine winner and distribute pot
        winners = game._determine_winner()
        
        # Complete hand in database
        if self.db_integration and hand_id:
            community_cards_str = [str(card) for card in game_state.community_cards]
            await self.db_integration.complete_hand(
                hand_id, game.pot, community_cards_str, winners, 
                game.chips.copy(), game.folded_players
            )
        
        game.next_hand()
        
        return {
            "winners": list(winners.keys()),
            "winnings": winners,
            "pot_size": game_state.pot_size,
            "actions": hand_actions,
            "community_cards": [str(card) for card in game_state.community_cards]
        }
    
    async def run_benchmark(self, num_sessions: int = 10, hands_per_session: int = 100) -> BenchmarkResults:
        print(f"Starting benchmark: {num_sessions} sessions, {hands_per_session} hands each")
        
        session_results = []
        total_hands = 0
        
        for session_num in range(num_sessions):
            print(f"Running session {session_num + 1}/{num_sessions}...")
            
            # Reset player chips for each session
            for player in self.players:
                player.total_hands = 0
                player.hands_won = 0
                player.total_winnings = 0
            
            session_name = f"Session_{session_num + 1}" if num_sessions > 1 else "Single_Session"
            session_result = await self.simulate_session(hands_per_session, session_name=session_name)
            session_results.append(session_result)
            total_hands += session_result.hands_played
            
            print(f"Session {session_num + 1} complete: {session_result.hands_played} hands in {session_result.session_duration:.1f}s")
            for player_name, chips in session_result.player_final_chips.items():
                print(f"  {player_name}: ${chips}")
        
        # Calculate overall statistics
        player_stats = {}
        for player in self.players:
            total_chips = sum(session.player_final_chips.get(player.name, 0) for session in session_results)
            sessions_won = sum(1 for session in session_results 
                             if session.player_final_chips.get(player.name, 0) == 
                             max(session.player_final_chips.values()))
            
            player_stats[player.name] = {
                "total_final_chips": total_chips,
                "average_chips_per_session": total_chips / num_sessions,
                "sessions_won": sessions_won,
                "win_rate": sessions_won / num_sessions,
                "total_profit": total_chips - (self.starting_chips * num_sessions),
                "roi": (total_chips - (self.starting_chips * num_sessions)) / (self.starting_chips * num_sessions)
            }
        
        # Determine overall winner
        overall_winner = max(player_stats.keys(), 
                           key=lambda p: player_stats[p]["total_final_chips"])
        
        return BenchmarkResults(
            total_hands=total_hands,
            total_sessions=num_sessions,
            player_stats=player_stats,
            overall_winner=overall_winner,
            session_results=session_results
        )