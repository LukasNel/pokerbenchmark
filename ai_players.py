import json
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from poker_game import GameState, PlayerAction, GameAction, Card

class AIPlayer(ABC):
    def __init__(self, name: str):
        self.name = name
        self.total_hands = 0
        self.hands_won = 0
        self.total_winnings = 0
    
    @abstractmethod
    async def make_decision(self, game_state: GameState, hole_cards: List[Card]) -> PlayerAction:
        pass
    
    def get_game_context(self, game_state: GameState, hole_cards: List[Card]) -> str:
        context = f"""You are playing Texas Hold'em poker. Here's the current situation:

Your hole cards: {', '.join(str(card) for card in hole_cards)}
Community cards: {', '.join(str(card) for card in game_state.community_cards) if game_state.community_cards else 'None yet'}
Betting round: {game_state.betting_round}
Pot size: ${game_state.pot_size}
Current bet: ${game_state.current_bet}
Your chips: ${game_state.player_chips.get(self.name, 0)}

Active players: {', '.join(game_state.active_players)}

You need to make a decision. Available actions:
- fold: Give up your hand
- call: Match the current bet (${game_state.current_bet})
- raise: Increase the bet (specify amount)
- check: Pass if no bet to call

Respond with JSON format: {{"action": "fold/call/raise/check", "amount": 0, "reasoning":""}}
If raising, specify the raise amount in the "amount" field.

Consider your hand strength, pot odds, and position. Play strategically to maximize your winnings."""
        return context


def find_the_json(text: str) -> str:
    left_brace = text.find("{")
    right_brace = text.rfind("}")
    if left_brace == -1 or right_brace == -1:
        return None
    return text[left_brace:right_brace+1]

class   OpenAIPlayer(AIPlayer):
    def __init__(self, name: str, api_key: str, model: str = "gpt-4"):
        super().__init__(name)
        self.api_key = api_key
        self.model = model
        
    async def make_decision(self, game_state: GameState, hole_cards: List[Card]) -> PlayerAction:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            
            context = self.get_game_context(game_state, hole_cards)
            
            # o1 models have different parameters
            if "o1" in self.model:
                messages = [{"role": "user", "content": f"You are an expert poker player. Always respond with valid JSON containing your decision.\n\n{context}"}]
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_completion_tokens=150
                )
            else:
                messages = [
                    {"role": "system", "content": "You are an aggresive expert poker player. Always respond with valid JSON containing your decision."},
                    {"role": "user", "content": context}
                ]
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150
                )
            
            decision_text = response.choices[0].message.content.strip()

            decision_text = find_the_json(decision_text)
            
            print(decision_text)
            # Parse JSON response
            try:
                decision = json.loads(decision_text)
                action_str = decision.get("action", "fold").lower()
                amount = decision.get("amount", 0)
                
                if action_str == "fold":
                    return PlayerAction(GameAction.FOLD)
                elif action_str == "call":
                    return PlayerAction(GameAction.CALL)
                elif action_str == "raise":
                    return PlayerAction(GameAction.RAISE, max(amount, game_state.current_bet))
                elif action_str == "check":
                    return PlayerAction(GameAction.CHECK)
                else:
                    return PlayerAction(GameAction.FOLD)
                    
            except json.JSONDecodeError:
                # Fallback: try to parse simple text response
                if "fold" in decision_text.lower():
                    return PlayerAction(GameAction.FOLD)
                elif "call" in decision_text.lower():
                    return PlayerAction(GameAction.CALL)
                elif "raise" in decision_text.lower():
                    return PlayerAction(GameAction.RAISE, game_state.current_bet * 2)
                else:
                    return PlayerAction(GameAction.CHECK)
                    
        except Exception as e:
            print(f"Error with OpenAI player {self.name}: {e}")
            # Default conservative play
            if game_state.current_bet == 0:
                return PlayerAction(GameAction.CHECK)
            else:
                return PlayerAction(GameAction.FOLD)

class AnthropicPlayer(AIPlayer):
    def __init__(self, name: str, api_key: str, model: str = "claude-3-sonnet-20240229"):
        super().__init__(name)
        self.api_key = api_key
        self.model = model
        
    async def make_decision(self, game_state: GameState, hole_cards: List[Card]) -> PlayerAction:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            context = self.get_game_context(game_state, hole_cards)
            
            message = await asyncio.to_thread(
                client.messages.create,
                model=self.model,
                max_tokens=150,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": f"You are an expert poker player. {context}"}
                ]
            )
            
            decision_text = message.content[0].text.strip()
            decision_text = find_the_json(decision_text)
            print(decision_text)
            # Parse JSON response
            try:
                decision = json.loads(decision_text)
                action_str = decision.get("action", "fold").lower()
                amount = decision.get("amount", 0)
                
                if action_str == "fold":
                    return PlayerAction(GameAction.FOLD)
                elif action_str == "call":
                    return PlayerAction(GameAction.CALL)
                elif action_str == "raise":
                    return PlayerAction(GameAction.RAISE, max(amount, game_state.current_bet))
                elif action_str == "check":
                    return PlayerAction(GameAction.CHECK)
                else:
                    return PlayerAction(GameAction.FOLD)
                    
            except json.JSONDecodeError:
                # Fallback: try to parse simple text response
                if "fold" in decision_text.lower():
                    return PlayerAction(GameAction.FOLD)
                elif "call" in decision_text.lower():
                    return PlayerAction(GameAction.CALL)
                elif "raise" in decision_text.lower():
                    return PlayerAction(GameAction.RAISE, game_state.current_bet * 2)
                else:
                    return PlayerAction(GameAction.CHECK)
                    
        except Exception as e:
            print(f"Error with Anthropic player {self.name}: {e}")
            # Default conservative play
            if game_state.current_bet == 0:
                return PlayerAction(GameAction.CHECK)
            else:
                return PlayerAction(GameAction.FOLD)

class RandomPlayer(AIPlayer):
    def __init__(self, name: str):
        super().__init__(name)
        
    async def make_decision(self, game_state: GameState, hole_cards: List[Card]) -> PlayerAction:
        import random
        
        # Simple random strategy with some basic logic
        my_chips = game_state.player_chips.get(self.name, 0)
        
        if game_state.current_bet == 0:
            # No bet to call, randomly check or bet
            if random.random() < 0.7:
                return PlayerAction(GameAction.CHECK)
            else:
                bet_amount = min(random.randint(10, 50), my_chips // 4)
                return PlayerAction(GameAction.RAISE, bet_amount)
        else:
            # There's a bet to call
            call_amount = game_state.current_bet
            
            if call_amount > my_chips // 2:
                # Bet is too large relative to stack
                return PlayerAction(GameAction.FOLD)
            
            action_choice = random.choices(
                ["fold", "call", "raise"], 
                weights=[0.3, 0.5, 0.2]
            )[0]
            
            if action_choice == "fold":
                return PlayerAction(GameAction.FOLD)
            elif action_choice == "call":
                return PlayerAction(GameAction.CALL)
            else:
                raise_amount = min(random.randint(call_amount, call_amount * 2), my_chips)
                return PlayerAction(GameAction.RAISE, raise_amount)