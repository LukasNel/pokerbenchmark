# Poker AI Benchmark

A Texas Hold'em poker benchmark that tests different AI language models (OpenAI GPT and Anthropic Claude) to see how well they play poker strategically.

## Features

- Complete Texas Hold'em poker engine
- Support for OpenAI GPT models (GPT-4, GPT-3.5)
- Support for Anthropic Claude models (Claude-3-Sonnet, Claude-3-Haiku)
- Multiple session simulation
- Detailed statistics and performance tracking
- JSON output for further analysis

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Run with both OpenAI and Anthropic models
python benchmark.py --openai-key YOUR_OPENAI_KEY --anthropic-key YOUR_ANTHROPIC_KEY

# Run with just OpenAI models
python benchmark.py --openai-key YOUR_OPENAI_KEY

# Run with environment variables
export OPENAI_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key
python benchmark.py
```

### Advanced Options

```bash
# Custom benchmark settings
python benchmark.py \
    --sessions 10 \
    --hands-per-session 100 \
    --starting-chips 2000 \
    --include-random \
    --output results.json
```

### Parameters

- `--sessions`: Number of poker sessions to run (default: 5)
- `--hands-per-session`: Number of hands per session (default: 50)
- `--starting-chips`: Starting chips for each player (default: 1000)
- `--include-random`: Include a random baseline player
- `--output`: Save results to JSON file

## How It Works

1. **Game Engine**: Implements full Texas Hold'em rules including:
   - Proper hand evaluation (Royal Flush to High Card)
   - Betting rounds (preflop, flop, turn, river)
   - Pot management and side pots
   - Blinds and dealer rotation

2. **AI Players**: Each AI model receives:
   - Their hole cards
   - Community cards (if revealed)
   - Current pot size and betting situation
   - Stack sizes and active players
   - Strategic context about poker decisions

3. **Benchmark Metrics**:
   - Total chips accumulated across all sessions
   - Return on Investment (ROI)
   - Number of sessions won
   - Hands played and performance consistency

## Example Output

```
POKER AI BENCHMARK RESULTS
============================================================

Benchmark Summary:
Total Sessions: 5
Total Hands: 250
Overall Winner: Claude-3-Sonnet

Player Performance:
Player               Total $      Avg/Session  ROI    Sessions Won
----------------------------------------------------------------------
Claude-3-Sonnet      $5,420       $1,084       8.4%   3           
GPT-4                $4,890       $978         -2.2%  2           
GPT-3.5              $4,690       $938         -6.2%  0           
Random-Baseline      $4,000       $800         -20.0% 0           
```

## API Requirements

- **OpenAI**: Requires valid API key with access to GPT models
- **Anthropic**: Requires valid API key with access to Claude models

Both APIs charge per token, so longer benchmarks will incur costs. A typical 5-session benchmark costs approximately $2-5 depending on the models used.

## Poker Strategy

The AIs are prompted to:
- Evaluate hand strength relative to community cards
- Consider pot odds and betting patterns
- Make strategic decisions about folding, calling, or raising
- Adapt their play based on stack sizes and position

## Architecture

- `poker_game.py`: Core Texas Hold'em engine
- `ai_players.py`: AI player implementations for different APIs
- `game_simulator.py`: Multi-session tournament simulation
- `benchmark.py`: Main CLI application


FULL CREDIT TO MR. WILLIAM DIAMOND, who is the genius behind the concept of the poker benchmark. https://www.will-diamond.com/
