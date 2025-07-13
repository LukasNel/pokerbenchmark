#!/usr/bin/env python3

import asyncio
import argparse
import json
import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from ai_players import OpenAIPlayer, AnthropicPlayer, RandomPlayer
from game_simulator import GameSimulator
from sqlite_database import SQLiteDatabase

def print_results(results):
    print("\n" + "="*60)
    print("POKER AI BENCHMARK RESULTS")
    print("="*60)
    
    print(f"\nBenchmark Summary:")
    print(f"Total Sessions: {results.total_sessions}")
    print(f"Total Hands: {results.total_hands}")
    print(f"Overall Winner: {results.overall_winner}")
    
    print(f"\nPlayer Performance:")
    print(f"{'Player':<20} {'Total $':<12} {'Avg/Session':<12} {'ROI':<8} {'Sessions Won':<12}")
    print("-" * 70)
    
    for player, stats in results.player_stats.items():
        roi_pct = stats['roi'] * 100
        print(f"{player:<20} ${stats['total_final_chips']:<11,} "
              f"${stats['average_chips_per_session']:<11,.0f} "
              f"{roi_pct:<7.1f}% {stats['sessions_won']:<12}")
    
    print(f"\nSession-by-Session Results:")
    for i, session in enumerate(results.session_results, 1):
        print(f"\nSession {i} ({session.hands_played} hands):")
        for player, chips in session.player_final_chips.items():
            profit = chips - 1000  # Starting chips
            print(f"  {player}: ${chips:,} (${profit:+,})")

def save_results(results, filename: str):
    data = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_summary": {
            "total_sessions": results.total_sessions,
            "total_hands": results.total_hands,
            "overall_winner": results.overall_winner
        },
        "player_stats": results.player_stats,
        "session_results": [
            {
                "hands_played": session.hands_played,
                "session_duration": session.session_duration,
                "final_chips": session.player_final_chips,
                "hand_count": len(session.hand_results)
            }
            for session in results.session_results
        ]
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nResults saved to {filename}")

async def main():
    parser = argparse.ArgumentParser(description="Poker AI Benchmark")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--anthropic-key", help="Anthropic API key")
    parser.add_argument("--sessions", type=int, default=5, help="Number of sessions to run")
    parser.add_argument("--hands-per-session", type=int, default=50, help="Hands per session")
    parser.add_argument("--starting-chips", type=int, default=1000, help="Starting chips per player")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--include-random", action="store_true", help="Include random player for baseline")
    
    args = parser.parse_args()
    
    # Get API keys from environment if not provided
    openai_key = args.openai_key or os.getenv("OPENAI_API_KEY")
    anthropic_key = args.anthropic_key or os.getenv("ANTHROPIC_API_KEY")
    
    if not openai_key and not anthropic_key:
        print("Error: At least one API key is required (OpenAI or Anthropic)")
        print("Provide via --openai-key, --anthropic-key, or environment variables OPENAI_API_KEY, ANTHROPIC_API_KEY")
        return
    
    # Create players
    players = []
    
    if openai_key:
        players.extend([
            OpenAIPlayer("GPT-4.5-preview", openai_key, "gpt-4.5-preview"),
            OpenAIPlayer("GPT-4o", openai_key, "gpt-4o"),
            OpenAIPlayer("GPT-4o-mini", openai_key, "gpt-4o-mini"),
        ])
    
    if anthropic_key:
        players.extend([
            AnthropicPlayer("Claude-4-Sonnet", anthropic_key, "claude-sonnet-4-20250514"),
            AnthropicPlayer("Claude-3.5-Sonnet", anthropic_key, "claude-3-5-sonnet-20241022"),
            AnthropicPlayer("Claude-3.5-Haiku", anthropic_key, "claude-3-5-haiku-20241022")
        ])
    
    if args.include_random:
        players.append(RandomPlayer("Random-Baseline"))
    
    if len(players) < 2:
        print("Error: Need at least 2 players for poker game")
        return
    
    print(f"Starting benchmark with {len(players)} players:")
    for player in players:
        print(f"  - {player.name}")
    
    print(f"\nConfiguration:")
    print(f"  Sessions: {args.sessions}")
    print(f"  Hands per session: {args.hands_per_session}")
    print(f"  Starting chips: ${args.starting_chips:,}")
    
    # Setup database
    db = SQLiteDatabase()
    await db.connect()
    
    # Run benchmark
    simulator = GameSimulator(players, args.starting_chips, db=db)
    
    try:
        results = await simulator.run_benchmark(args.sessions, args.hands_per_session)
        
        print_results(results)
        
        if args.output:
            save_results(results, args.output)
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\nError during benchmark: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if db:
            await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())