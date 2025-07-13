import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

@dataclass
class Card:
    rank: Rank
    suit: Suit
    
    def __str__(self):
        rank_str = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 
                   9: "9", 10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}
        return f"{rank_str[self.rank.value]}{self.suit.value}"

class HandRank(Enum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

@dataclass
class HandEvaluation:
    rank: HandRank
    kickers: List[int]
    
    def __lt__(self, other):
        if self.rank.value != other.rank.value:
            return self.rank.value < other.rank.value
        return self.kickers < other.kickers
    
    def __gt__(self, other):
        if self.rank.value != other.rank.value:
            return self.rank.value > other.rank.value
        return self.kickers > other.kickers
    
    def __eq__(self, other):
        return self.rank.value == other.rank.value and self.kickers == other.kickers
    
    def __ge__(self, other):
        return self > other or self == other
    
    def __le__(self, other):
        return self < other or self == other

class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for rank in Rank for suit in Suit]
        self.shuffle()
    
    def shuffle(self):
        random.shuffle(self.cards)
    
    def deal(self) -> Card:
        return self.cards.pop()

class PokerHand:
    @staticmethod
    def evaluate(cards: List[Card]) -> HandEvaluation:
        ranks = sorted([card.rank.value for card in cards], reverse=True)
        suits = [card.suit for card in cards]
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        is_flush = len(set(suits)) == 1
        is_straight = PokerHand._is_straight(ranks)
        
        if is_straight and is_flush:
            if ranks[0] == 14:  # Ace high straight flush
                return HandEvaluation(HandRank.ROYAL_FLUSH, [14])
            return HandEvaluation(HandRank.STRAIGHT_FLUSH, [max(ranks)])
        
        counts = sorted(rank_counts.values(), reverse=True)
        
        if counts == [4, 1]:
            four_kind = [rank for rank, count in rank_counts.items() if count == 4][0]
            kicker = [rank for rank, count in rank_counts.items() if count == 1][0]
            return HandEvaluation(HandRank.FOUR_OF_A_KIND, [four_kind, kicker])
        
        if counts == [3, 2]:
            three_kind = [rank for rank, count in rank_counts.items() if count == 3][0]
            pair = [rank for rank, count in rank_counts.items() if count == 2][0]
            return HandEvaluation(HandRank.FULL_HOUSE, [three_kind, pair])
        
        if is_flush:
            return HandEvaluation(HandRank.FLUSH, ranks)
        
        if is_straight:
            return HandEvaluation(HandRank.STRAIGHT, [max(ranks)])
        
        if counts == [3, 1, 1]:
            three_kind = [rank for rank, count in rank_counts.items() if count == 3][0]
            kickers = sorted([rank for rank, count in rank_counts.items() if count == 1], reverse=True)
            return HandEvaluation(HandRank.THREE_OF_A_KIND, [three_kind] + kickers)
        
        if counts == [2, 2, 1]:
            pairs = sorted([rank for rank, count in rank_counts.items() if count == 2], reverse=True)
            kicker = [rank for rank, count in rank_counts.items() if count == 1][0]
            return HandEvaluation(HandRank.TWO_PAIR, pairs + [kicker])
        
        if counts == [2, 1, 1, 1]:
            pair = [rank for rank, count in rank_counts.items() if count == 2][0]
            kickers = sorted([rank for rank, count in rank_counts.items() if count == 1], reverse=True)
            return HandEvaluation(HandRank.PAIR, [pair] + kickers)
        
        return HandEvaluation(HandRank.HIGH_CARD, ranks)
    
    @staticmethod
    def _is_straight(ranks: List[int]) -> bool:
        sorted_ranks = sorted(set(ranks))
        if len(sorted_ranks) != 5:
            return False
        
        # Check for ace-low straight (A, 2, 3, 4, 5)
        if sorted_ranks == [2, 3, 4, 5, 14]:
            return True
        
        # Check for regular straight
        for i in range(1, 5):
            if sorted_ranks[i] != sorted_ranks[i-1] + 1:
                return False
        return True

class GameAction(Enum):
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"
    CHECK = "check"

@dataclass
class PlayerAction:
    action: GameAction
    amount: int = 0

@dataclass
class GameState:
    community_cards: List[Card]
    pot_size: int
    current_bet: int
    player_chips: Dict[str, int]
    player_hole_cards: Dict[str, List[Card]]
    active_players: List[str]
    betting_round: str  # "preflop", "flop", "turn", "river"
    to_act: str

class TexasHoldem:
    def __init__(self, players: List[str], starting_chips: int = 1000, small_blind: int = 5, big_blind: int = 10):
        self.players = players
        self.starting_chips = starting_chips
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.chips = {player: starting_chips for player in players}
        self.deck = None
        self.community_cards = []
        self.hole_cards = {}
        self.pot = 0
        self.current_bet = 0
        self.player_bets = {}
        self.active_players = []
        self.folded_players = set()
        self.dealer_position = 0
    
    def start_hand(self) -> GameState:
        self.deck = Deck()
        self.community_cards = []
        self.hole_cards = {}
        self.pot = 0
        self.current_bet = 0
        self.player_bets = {player: 0 for player in self.players}
        self.active_players = [p for p in self.players if self.chips[p] > 0]
        self.folded_players = set()
        
        # Deal hole cards
        for player in self.active_players:
            self.hole_cards[player] = [self.deck.deal(), self.deck.deal()]
        
        # Post blinds
        if len(self.active_players) >= 2:
            sb_player = self.active_players[(self.dealer_position + 1) % len(self.active_players)]
            bb_player = self.active_players[(self.dealer_position + 2) % len(self.active_players)]
            
            self._place_bet(sb_player, min(self.small_blind, self.chips[sb_player]))
            self._place_bet(bb_player, min(self.big_blind, self.chips[bb_player]))
            self.current_bet = self.big_blind
        
        return self._get_game_state("preflop")
    
    def _place_bet(self, player: str, amount: int):
        actual_amount = min(amount, self.chips[player])
        self.chips[player] -= actual_amount
        self.player_bets[player] += actual_amount
        self.pot += actual_amount
    
    def process_action(self, player: str, action: PlayerAction) -> Optional[GameState]:
        if player in self.folded_players or player not in self.active_players:
            return None
        
        if action.action == GameAction.FOLD:
            self.folded_players.add(player)
        elif action.action == GameAction.CALL:
            call_amount = self.current_bet - self.player_bets[player]
            self._place_bet(player, call_amount)
        elif action.action == GameAction.RAISE:
            total_bet = self.player_bets[player] + action.amount
            if total_bet > self.current_bet:
                self._place_bet(player, action.amount)
                self.current_bet = total_bet
        elif action.action == GameAction.CHECK:
            if self.player_bets[player] < self.current_bet:
                return None  # Invalid action
        
        return self._get_game_state()
    
    def advance_betting_round(self) -> Optional[GameState]:
        # Reset betting for new round
        self.player_bets = {player: 0 for player in self.players}
        self.current_bet = 0
        
        if not self.community_cards:  # Flop
            self.community_cards = [self.deck.deal(), self.deck.deal(), self.deck.deal()]
            return self._get_game_state("flop")
        elif len(self.community_cards) == 3:  # Turn
            self.community_cards.append(self.deck.deal())
            return self._get_game_state("turn")
        elif len(self.community_cards) == 4:  # River
            self.community_cards.append(self.deck.deal())
            return self._get_game_state("river")
        else:  # Showdown
            return self._determine_winner()
    
    def _get_game_state(self, betting_round: str = None) -> GameState:
        if betting_round is None:
            if not self.community_cards:
                betting_round = "preflop"
            elif len(self.community_cards) == 3:
                betting_round = "flop"
            elif len(self.community_cards) == 4:
                betting_round = "turn"
            else:
                betting_round = "river"
        
        active = [p for p in self.active_players if p not in self.folded_players]
        to_act = active[0] if active else ""
        
        return GameState(
            community_cards=self.community_cards.copy(),
            pot_size=self.pot,
            current_bet=self.current_bet,
            player_chips=self.chips.copy(),
            player_hole_cards=self.hole_cards.copy(),
            active_players=active,
            betting_round=betting_round,
            to_act=to_act
        )
    
    def _determine_winner(self) -> Dict[str, int]:
        active_players = [p for p in self.active_players if p not in self.folded_players]
        
        if len(active_players) == 1:
            winner = active_players[0]
            self.chips[winner] += self.pot
            return {winner: self.pot}
        
        # Evaluate hands
        player_hands = {}
        for player in active_players:
            all_cards = self.hole_cards[player] + self.community_cards
            best_hand = self._get_best_hand(all_cards)
            player_hands[player] = best_hand
        
        # Find winner(s)
        best_evaluation = max(player_hands.values())
        winners = [p for p, hand in player_hands.items() if hand >= best_evaluation]
        
        # Split pot
        winnings_per_player = self.pot // len(winners)
        results = {}
        for winner in winners:
            self.chips[winner] += winnings_per_player
            results[winner] = winnings_per_player
        
        return results
    
    def _get_best_hand(self, cards: List[Card]) -> HandEvaluation:
        from itertools import combinations
        best_hand = None
        
        for five_cards in combinations(cards, 5):
            evaluation = PokerHand.evaluate(list(five_cards))
            if best_hand is None or evaluation > best_hand:
                best_hand = evaluation
        
        return best_hand
    
    def is_hand_complete(self) -> bool:
        active_players = [p for p in self.active_players if p not in self.folded_players]
        return len(active_players) <= 1
    
    def should_advance_to_showdown(self) -> bool:
        active_players = [p for p in self.active_players if p not in self.folded_players]
        return len(active_players) <= 1 or len(self.community_cards) == 5
    
    def next_hand(self):
        self.dealer_position = (self.dealer_position + 1) % len(self.players)
        # Remove players with no chips
        self.players = [p for p in self.players if self.chips[p] > 0]