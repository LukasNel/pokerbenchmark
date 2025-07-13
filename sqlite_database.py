import sqlite3
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from database_interface import DatabaseInterface
from database_models import (
    PlayerModel, SessionModel, HandModel, PlayerHandModel, ActionModel,
    PlayerStatsModel, HandSummaryModel, SessionSummaryModel, HandDetailModel,
    ActionType, BettingRound
)

class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_path: str = "poker_benchmark.db"):
        self.db_path = db_path
        self.connection = None
    
    async def connect(self) -> None:
        """Establish database connection"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        await self.init_schema()
    
    async def disconnect(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    async def init_schema(self) -> None:
        """Initialize database schema/tables"""
        schema = """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            model_type TEXT NOT NULL,
            model_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            starting_chips INTEGER NOT NULL,
            small_blind INTEGER NOT NULL,
            big_blind INTEGER NOT NULL,
            max_hands INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            total_hands_played INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS hands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            hand_number INTEGER NOT NULL,
            dealer_position INTEGER NOT NULL,
            pot_size INTEGER NOT NULL,
            community_cards TEXT NOT NULL, -- JSON array
            winner_ids TEXT NOT NULL, -- JSON array
            winnings TEXT NOT NULL, -- JSON dict
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        
        CREATE TABLE IF NOT EXISTS player_hands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            hole_cards TEXT NOT NULL, -- JSON array
            starting_chips INTEGER NOT NULL,
            ending_chips INTEGER NOT NULL,
            final_position INTEGER NOT NULL,
            folded BOOLEAN DEFAULT FALSE,
            all_in BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (hand_id) REFERENCES hands(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );
        
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            betting_round TEXT NOT NULL,
            action_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            pot_size_after INTEGER NOT NULL,
            position_in_round INTEGER NOT NULL,
            reasoning TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hand_id) REFERENCES hands(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_hands_session ON hands(session_id);
        CREATE INDEX IF NOT EXISTS idx_player_hands_hand ON player_hands(hand_id);
        CREATE INDEX IF NOT EXISTS idx_player_hands_player ON player_hands(player_id);
        CREATE INDEX IF NOT EXISTS idx_actions_hand ON actions(hand_id);
        CREATE INDEX IF NOT EXISTS idx_actions_player ON actions(player_id);
        """
        
        cursor = self.connection.cursor()
        cursor.executescript(schema)
        self.connection.commit()
    
    def _row_to_player(self, row: sqlite3.Row) -> PlayerModel:
        return PlayerModel(
            id=row['id'],
            name=row['name'],
            model_type=row['model_type'],
            model_name=row['model_name'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    def _row_to_session(self, row: sqlite3.Row) -> SessionModel:
        return SessionModel(
            id=row['id'],
            session_name=row['session_name'],
            starting_chips=row['starting_chips'],
            small_blind=row['small_blind'],
            big_blind=row['big_blind'],
            max_hands=row['max_hands'],
            created_at=datetime.fromisoformat(row['created_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            total_hands_played=row['total_hands_played']
        )
    
    def _row_to_hand(self, row: sqlite3.Row) -> HandModel:
        return HandModel(
            id=row['id'],
            session_id=row['session_id'],
            hand_number=row['hand_number'],
            dealer_position=row['dealer_position'],
            pot_size=row['pot_size'],
            community_cards=json.loads(row['community_cards']),
            winner_ids=json.loads(row['winner_ids']),
            winnings={int(k): v for k, v in json.loads(row['winnings']).items()},
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    def _row_to_player_hand(self, row: sqlite3.Row) -> PlayerHandModel:
        return PlayerHandModel(
            id=row['id'],
            hand_id=row['hand_id'],
            player_id=row['player_id'],
            hole_cards=json.loads(row['hole_cards']),
            starting_chips=row['starting_chips'],
            ending_chips=row['ending_chips'],
            final_position=row['final_position'],
            folded=bool(row['folded']),
            all_in=bool(row['all_in'])
        )
    
    def _row_to_action(self, row: sqlite3.Row) -> ActionModel:
        return ActionModel(
            id=row['id'],
            hand_id=row['hand_id'],
            player_id=row['player_id'],
            betting_round=BettingRound(row['betting_round']),
            action_type=ActionType(row['action_type']),
            amount=row['amount'],
            pot_size_after=row['pot_size_after'],
            position_in_round=row['position_in_round'],
            reasoning=row['reasoning'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    # Player operations
    async def create_player(self, player: PlayerModel) -> PlayerModel:
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO players (name, model_type, model_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (player.name, player.model_type, player.model_name, player.created_at.isoformat()))
        self.connection.commit()
        
        player.id = cursor.lastrowid
        return player
    
    async def get_player(self, player_id: int) -> Optional[PlayerModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        return self._row_to_player(row) if row else None
    
    async def get_player_by_name(self, name: str) -> Optional[PlayerModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM players WHERE name = ?", (name,))
        row = cursor.fetchone()
        return self._row_to_player(row) if row else None
    
    async def list_players(self) -> List[PlayerModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM players ORDER BY created_at")
        return [self._row_to_player(row) for row in cursor.fetchall()]
    
    # Session operations
    async def create_session(self, session: SessionModel) -> SessionModel:
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_name, starting_chips, small_blind, big_blind, 
                                max_hands, created_at, completed_at, total_hands_played)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session.session_name, session.starting_chips, session.small_blind, 
              session.big_blind, session.max_hands, session.created_at.isoformat(),
              session.completed_at.isoformat() if session.completed_at else None,
              session.total_hands_played))
        self.connection.commit()
        
        session.id = cursor.lastrowid
        return session
    
    async def get_session(self, session_id: int) -> Optional[SessionModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return self._row_to_session(row) if row else None
    
    async def update_session(self, session: SessionModel) -> SessionModel:
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE sessions SET session_name = ?, starting_chips = ?, small_blind = ?,
                              big_blind = ?, max_hands = ?, completed_at = ?, total_hands_played = ?
            WHERE id = ?
        """, (session.session_name, session.starting_chips, session.small_blind,
              session.big_blind, session.max_hands,
              session.completed_at.isoformat() if session.completed_at else None,
              session.total_hands_played, session.id))
        self.connection.commit()
        return session
    
    async def list_sessions(self) -> List[SessionModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        return [self._row_to_session(row) for row in cursor.fetchall()]
    
    # Hand operations
    async def create_hand(self, hand: HandModel) -> HandModel:
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO hands (session_id, hand_number, dealer_position, pot_size,
                             community_cards, winner_ids, winnings, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (hand.session_id, hand.hand_number, hand.dealer_position, hand.pot_size,
              json.dumps(hand.community_cards), json.dumps(hand.winner_ids),
              json.dumps(hand.winnings), hand.created_at.isoformat()))
        self.connection.commit()
        
        hand.id = cursor.lastrowid
        return hand
    
    async def get_hand(self, hand_id: int) -> Optional[HandModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM hands WHERE id = ?", (hand_id,))
        row = cursor.fetchone()
        return self._row_to_hand(row) if row else None
    
    async def get_hands_by_session(self, session_id: int) -> List[HandModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM hands WHERE session_id = ? ORDER BY hand_number", (session_id,))
        return [self._row_to_hand(row) for row in cursor.fetchall()]
    
    # Player hand operations
    async def create_player_hand(self, player_hand: PlayerHandModel) -> PlayerHandModel:
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO player_hands (hand_id, player_id, hole_cards, starting_chips,
                                    ending_chips, final_position, folded, all_in)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (player_hand.hand_id, player_hand.player_id, json.dumps(player_hand.hole_cards),
              player_hand.starting_chips, player_hand.ending_chips, player_hand.final_position,
              player_hand.folded, player_hand.all_in))
        self.connection.commit()
        
        player_hand.id = cursor.lastrowid
        return player_hand
    
    async def get_player_hands_by_hand(self, hand_id: int) -> List[PlayerHandModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM player_hands WHERE hand_id = ?", (hand_id,))
        return [self._row_to_player_hand(row) for row in cursor.fetchall()]
    
    async def get_player_hands_by_player(self, player_id: int) -> List[PlayerHandModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM player_hands WHERE player_id = ? ORDER BY id", (player_id,))
        return [self._row_to_player_hand(row) for row in cursor.fetchall()]
    
    # Action operations
    async def create_action(self, action: ActionModel) -> ActionModel:
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO actions (hand_id, player_id, betting_round, action_type, amount,
                               pot_size_after, position_in_round, reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (action.hand_id, action.player_id, action.betting_round.value,
              action.action_type.value, action.amount, action.pot_size_after,
              action.position_in_round, action.reasoning, action.created_at.isoformat()))
        self.connection.commit()
        
        action.id = cursor.lastrowid
        return action
    
    async def get_actions_by_hand(self, hand_id: int) -> List[ActionModel]:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM actions WHERE hand_id = ? 
            ORDER BY betting_round, position_in_round
        """, (hand_id,))
        return [self._row_to_action(row) for row in cursor.fetchall()]
    
    async def get_actions_by_player(self, player_id: int) -> List[ActionModel]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM actions WHERE player_id = ? ORDER BY created_at", (player_id,))
        return [self._row_to_action(row) for row in cursor.fetchall()]
    
    # Statistics and aggregations
    async def get_player_stats(self, player_id: int) -> Optional[PlayerStatsModel]:
        cursor = self.connection.cursor()
        
        # Get basic player info
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player_row = cursor.fetchone()
        if not player_row:
            return None
        
        # Get comprehensive stats
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT ph.hand_id) as total_hands,
                COUNT(DISTINCT CASE WHEN ph.final_position = 1 THEN ph.hand_id END) as hands_won,
                SUM(CASE WHEN ph.final_position = 1 THEN h.pot_size ELSE 0 END) as total_chips_won,
                SUM(ph.starting_chips - ph.ending_chips) as total_chips_lost,
                AVG(CASE WHEN ph.final_position = 1 THEN h.pot_size ELSE 0 END) as avg_pot_won
            FROM player_hands ph
            JOIN hands h ON ph.hand_id = h.id
            WHERE ph.player_id = ?
        """, (player_id,))
        
        stats_row = cursor.fetchone()
        
        # Get action percentages
        cursor.execute("""
            SELECT 
                action_type,
                COUNT(*) as count,
                SUM(CASE WHEN betting_round = 'preflop' AND action_type = 'raise' THEN 1 ELSE 0 END) as preflop_raises,
                SUM(CASE WHEN betting_round != 'preflop' AND action_type = 'raise' THEN 1 ELSE 0 END) as postflop_raises,
                SUM(CASE WHEN betting_round = 'preflop' THEN 1 ELSE 0 END) as preflop_actions,
                SUM(CASE WHEN betting_round != 'preflop' THEN 1 ELSE 0 END) as postflop_actions
            FROM actions
            WHERE player_id = ?
            GROUP BY action_type
        """, (player_id,))
        
        action_stats = {row['action_type']: row['count'] for row in cursor.fetchall()}
        total_actions = sum(action_stats.values())
        
        # Calculate percentages
        fold_pct = (action_stats.get('fold', 0) / total_actions * 100) if total_actions > 0 else 0
        call_pct = (action_stats.get('call', 0) / total_actions * 100) if total_actions > 0 else 0
        raise_pct = (action_stats.get('raise', 0) / total_actions * 100) if total_actions > 0 else 0
        check_pct = (action_stats.get('check', 0) / total_actions * 100) if total_actions > 0 else 0
        
        # Get aggression stats
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN betting_round = 'preflop' AND action_type = 'raise' THEN 1 ELSE 0 END) as preflop_raises,
                SUM(CASE WHEN betting_round != 'preflop' AND action_type = 'raise' THEN 1 ELSE 0 END) as postflop_raises,
                SUM(CASE WHEN betting_round = 'preflop' THEN 1 ELSE 0 END) as preflop_actions,
                SUM(CASE WHEN betting_round != 'preflop' THEN 1 ELSE 0 END) as postflop_actions
            FROM actions
            WHERE player_id = ?
        """, (player_id,))
        
        aggr_row = cursor.fetchone()
        preflop_aggr = (aggr_row['preflop_raises'] / aggr_row['preflop_actions'] * 100) if aggr_row['preflop_actions'] > 0 else 0
        postflop_aggr = (aggr_row['postflop_raises'] / aggr_row['postflop_actions'] * 100) if aggr_row['postflop_actions'] > 0 else 0
        
        total_hands = stats_row['total_hands']
        hands_won = stats_row['hands_won']
        total_chips_won = stats_row['total_chips_won'] or 0
        total_chips_lost = stats_row['total_chips_lost'] or 0
        
        return PlayerStatsModel(
            player_id=player_id,
            player_name=player_row['name'],
            model_name=player_row['model_name'],
            total_hands=total_hands,
            hands_won=hands_won,
            win_percentage=(hands_won / total_hands * 100) if total_hands > 0 else 0,
            total_chips_won=total_chips_won,
            total_chips_lost=total_chips_lost,
            net_profit=total_chips_won - total_chips_lost,
            roi=((total_chips_won - total_chips_lost) / total_chips_lost * 100) if total_chips_lost > 0 else 0,
            avg_pot_won=stats_row['avg_pot_won'] or 0,
            fold_percentage=fold_pct,
            call_percentage=call_pct,
            raise_percentage=raise_pct,
            check_percentage=check_pct,
            preflop_aggression=preflop_aggr,
            postflop_aggression=postflop_aggr
        )
    
    async def get_all_player_stats(self) -> List[PlayerStatsModel]:
        players = await self.list_players()
        stats = []
        for player in players:
            player_stats = await self.get_player_stats(player.id)
            if player_stats:
                stats.append(player_stats)
        return stats
    
    async def get_session_summary(self, session_id: int) -> Optional[SessionSummaryModel]:
        session = await self.get_session(session_id)
        if not session:
            return None
        
        cursor = self.connection.cursor()
        
        # Get final chip counts
        cursor.execute("""
            SELECT p.name, ph.ending_chips
            FROM player_hands ph
            JOIN players p ON ph.player_id = p.id
            JOIN hands h ON ph.hand_id = h.id
            WHERE h.session_id = ?
            ORDER BY h.hand_number DESC, ph.ending_chips DESC
            LIMIT (SELECT COUNT(DISTINCT ph.player_id) FROM player_hands ph JOIN hands h ON ph.hand_id = h.id WHERE h.session_id = ?)
        """, (session_id, session_id))
        
        chip_counts = {row['name']: row['ending_chips'] for row in cursor.fetchall()}
        
        # Get biggest winner/loser
        if chip_counts:
            biggest_winner = max(chip_counts.keys(), key=lambda x: chip_counts[x])
            biggest_loser = min(chip_counts.keys(), key=lambda x: chip_counts[x])
        else:
            biggest_winner = biggest_loser = "Unknown"
        
        # Get pot statistics
        cursor.execute("""
            SELECT MAX(pot_size) as biggest_pot, AVG(pot_size) as avg_pot
            FROM hands WHERE session_id = ?
        """, (session_id,))
        
        pot_stats = cursor.fetchone()
        
        return SessionSummaryModel(
            session_id=session_id,
            session_name=session.session_name,
            total_hands=session.total_hands_played,
            starting_chips=session.starting_chips,
            final_chip_counts=chip_counts,
            biggest_winner=biggest_winner,
            biggest_loser=biggest_loser,
            biggest_pot=pot_stats['biggest_pot'] or 0,
            avg_pot_size=pot_stats['avg_pot'] or 0,
            total_duration_minutes=None,  # Calculate from timestamps if needed
            created_at=session.created_at,
            completed_at=session.completed_at
        )
    
    async def get_hand_summaries(self, session_id: int) -> List[HandSummaryModel]:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                h.id, h.session_id, h.hand_number, h.pot_size, h.community_cards,
                h.winner_ids, h.winnings, h.created_at,
                COUNT(DISTINCT ph.player_id) as num_players,
                COUNT(DISTINCT a.id) as num_actions
            FROM hands h
            LEFT JOIN player_hands ph ON h.id = ph.hand_id
            LEFT JOIN actions a ON h.id = a.hand_id
            WHERE h.session_id = ?
            GROUP BY h.id
            ORDER BY h.hand_number
        """, (session_id,))
        
        summaries = []
        for row in cursor.fetchall():
            winner_ids = json.loads(row['winner_ids'])
            
            # Get winner names
            if winner_ids:
                placeholders = ','.join(['?' for _ in winner_ids])
                cursor.execute(f"SELECT name FROM players WHERE id IN ({placeholders})", winner_ids)
                winner_names = [w['name'] for w in cursor.fetchall()]
            else:
                winner_names = []
            
            # Count betting rounds
            cursor.execute("""
                SELECT COUNT(DISTINCT betting_round) as rounds
                FROM actions WHERE hand_id = ?
            """, (row['id'],))
            rounds_row = cursor.fetchone()
            
            summaries.append(HandSummaryModel(
                hand_id=row['id'],
                session_id=row['session_id'],
                hand_number=row['hand_number'],
                pot_size=row['pot_size'],
                community_cards=json.loads(row['community_cards']),
                winner_names=winner_names,
                total_winnings=sum(json.loads(row['winnings']).values()),
                num_players=row['num_players'],
                num_actions=row['num_actions'],
                betting_rounds_completed=rounds_row['rounds'] or 0,
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        
        return summaries
    
    async def get_hand_detail(self, hand_id: int) -> Optional[HandDetailModel]:
        hand = await self.get_hand(hand_id)
        if not hand:
            return None
        
        session = await self.get_session(hand.session_id)
        players = await self.get_player_hands_by_hand(hand_id)
        actions = await self.get_actions_by_hand(hand_id)
        
        return HandDetailModel(
            hand=hand,
            players=players,
            actions=actions,
            session=session
        )
    
    async def get_player_win_percentage_over_time(self, player_id: int) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                h.hand_number,
                h.created_at,
                ph.final_position,
                ROW_NUMBER() OVER (ORDER BY h.created_at) as hand_index,
                SUM(CASE WHEN ph.final_position = 1 THEN 1 ELSE 0 END) OVER (ORDER BY h.created_at) as cumulative_wins,
                COUNT(*) OVER (ORDER BY h.created_at) as cumulative_hands
            FROM player_hands ph
            JOIN hands h ON ph.hand_id = h.id
            WHERE ph.player_id = ?
            ORDER BY h.created_at
        """, (player_id,))
        
        results = []
        for row in cursor.fetchall():
            win_pct = (row['cumulative_wins'] / row['cumulative_hands'] * 100) if row['cumulative_hands'] > 0 else 0
            results.append({
                'hand_number': row['hand_index'],
                'cumulative_wins': row['cumulative_wins'],
                'cumulative_hands': row['cumulative_hands'],
                'win_percentage': win_pct,
                'created_at': row['created_at']
            })
        
        return results
    
    async def get_model_comparison_stats(self) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                p.model_name,
                p.model_type,
                COUNT(DISTINCT ph.hand_id) as total_hands,
                COUNT(DISTINCT CASE WHEN ph.final_position = 1 THEN ph.hand_id END) as hands_won,
                SUM(CASE WHEN ph.final_position = 1 THEN h.pot_size ELSE 0 END) as total_winnings,
                AVG(CASE WHEN ph.final_position = 1 THEN h.pot_size ELSE 0 END) as avg_pot_won
            FROM players p
            LEFT JOIN player_hands ph ON p.id = ph.player_id
            LEFT JOIN hands h ON ph.hand_id = h.id
            GROUP BY p.model_name, p.model_type
            ORDER BY hands_won DESC, total_winnings DESC
        """, ())
        
        results = []
        for row in cursor.fetchall():
            win_pct = (row['hands_won'] / row['total_hands'] * 100) if row['total_hands'] > 0 else 0
            results.append({
                'model_name': row['model_name'],
                'model_type': row['model_type'],
                'total_hands': row['total_hands'],
                'hands_won': row['hands_won'],
                'win_percentage': win_pct,
                'total_winnings': row['total_winnings'] or 0,
                'avg_pot_won': row['avg_pot_won'] or 0
            })
        
        return results
    
    async def get_recent_hands(self, limit: int = 10) -> List[HandSummaryModel]:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                h.id, h.session_id, h.hand_number, h.pot_size, h.community_cards,
                h.winner_ids, h.winnings, h.created_at,
                COUNT(DISTINCT ph.player_id) as num_players,
                COUNT(DISTINCT a.id) as num_actions
            FROM hands h
            LEFT JOIN player_hands ph ON h.id = ph.hand_id
            LEFT JOIN actions a ON h.id = a.hand_id
            GROUP BY h.id
            ORDER BY h.created_at DESC
            LIMIT ?
        """, (limit,))
        
        summaries = []
        for row in cursor.fetchall():
            winner_ids = json.loads(row['winner_ids'])
            
            # Get winner names
            if winner_ids:
                placeholders = ','.join(['?' for _ in winner_ids])
                cursor.execute(f"SELECT name FROM players WHERE id IN ({placeholders})", winner_ids)
                winner_names = [w['name'] for w in cursor.fetchall()]
            else:
                winner_names = []
            
            # Count betting rounds
            cursor.execute("""
                SELECT COUNT(DISTINCT betting_round) as rounds
                FROM actions WHERE hand_id = ?
            """, (row['id'],))
            rounds_row = cursor.fetchone()
            
            summaries.append(HandSummaryModel(
                hand_id=row['id'],
                session_id=row['session_id'],
                hand_number=row['hand_number'],
                pot_size=row['pot_size'],
                community_cards=json.loads(row['community_cards']),
                winner_names=winner_names,
                total_winnings=sum(json.loads(row['winnings']).values()),
                num_players=row['num_players'],
                num_actions=row['num_actions'],
                betting_rounds_completed=rounds_row['rounds'] or 0,
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        
        return summaries
    
    async def search_hands(self, 
                          session_id: Optional[int] = None,
                          player_id: Optional[int] = None,
                          min_pot_size: Optional[int] = None,
                          max_pot_size: Optional[int] = None,
                          winner_id: Optional[int] = None,
                          limit: int = 100) -> List[HandSummaryModel]:
        
        conditions = []
        params = []
        
        if session_id:
            conditions.append("h.session_id = ?")
            params.append(session_id)
        
        if player_id:
            conditions.append("EXISTS (SELECT 1 FROM player_hands ph WHERE ph.hand_id = h.id AND ph.player_id = ?)")
            params.append(player_id)
        
        if min_pot_size:
            conditions.append("h.pot_size >= ?")
            params.append(min_pot_size)
        
        if max_pot_size:
            conditions.append("h.pot_size <= ?")
            params.append(max_pot_size)
        
        if winner_id:
            conditions.append("EXISTS (SELECT 1 FROM player_hands ph WHERE ph.hand_id = h.id AND ph.player_id = ? AND ph.final_position = 1)")
            params.append(winner_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor = self.connection.cursor()
        cursor.execute(f"""
            SELECT 
                h.id, h.session_id, h.hand_number, h.pot_size, h.community_cards,
                h.winner_ids, h.winnings, h.created_at,
                COUNT(DISTINCT ph.player_id) as num_players,
                COUNT(DISTINCT a.id) as num_actions
            FROM hands h
            LEFT JOIN player_hands ph ON h.id = ph.hand_id
            LEFT JOIN actions a ON h.id = a.hand_id
            WHERE {where_clause}
            GROUP BY h.id
            ORDER BY h.created_at DESC
            LIMIT ?
        """, params + [limit])
        
        summaries = []
        for row in cursor.fetchall():
            winner_ids = json.loads(row['winner_ids'])
            
            # Get winner names
            if winner_ids:
                placeholders = ','.join(['?' for _ in winner_ids])
                cursor.execute(f"SELECT name FROM players WHERE id IN ({placeholders})", winner_ids)
                winner_names = [w['name'] for w in cursor.fetchall()]
            else:
                winner_names = []
            
            # Count betting rounds
            cursor.execute("""
                SELECT COUNT(DISTINCT betting_round) as rounds
                FROM actions WHERE hand_id = ?
            """, (row['id'],))
            rounds_row = cursor.fetchone()
            
            summaries.append(HandSummaryModel(
                hand_id=row['id'],
                session_id=row['session_id'],
                hand_number=row['hand_number'],
                pot_size=row['pot_size'],
                community_cards=json.loads(row['community_cards']),
                winner_names=winner_names,
                total_winnings=sum(json.loads(row['winnings']).values()),
                num_players=row['num_players'],
                num_actions=row['num_actions'],
                betting_rounds_completed=rounds_row['rounds'] or 0,
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        
        return summaries