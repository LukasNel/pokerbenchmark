from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import json
import os
from database_interface import DatabaseInterface
from sqlite_database import SQLiteDatabase
from database_models import HandDetailModel, PlayerStatsModel

app = FastAPI(title="Poker AI Benchmark Dashboard")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Database instance
db: DatabaseInterface = None

@app.on_event("startup")
async def startup_event():
    global db
    db = SQLiteDatabase("poker_benchmark_v3.db")
    await db.connect()

@app.on_event("shutdown")
async def shutdown_event():
    if db:
        await db.disconnect()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard showing sessions and overall stats"""
    
    try:
        # Get all sessions
        sessions = await db.list_sessions()
        
        # Get player stats
        player_stats = await db.get_all_player_stats()
        
        # Get model comparison
        model_comparison = await db.get_model_comparison_stats()
        
        # Get recent hands
        recent_hands = await db.get_recent_hands(limit=10)
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "sessions": sessions or [],
            "player_stats": player_stats or [],
            "model_comparison": model_comparison or [],
            "recent_hands": recent_hands or []
        })
    except Exception as e:
        print(f"Error in dashboard: {e}")
        # Return empty dashboard if there's an error
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "sessions": [],
            "player_stats": [],
            "model_comparison": [],
            "recent_hands": []
        })

@app.get("/session/{session_id}", response_class=HTMLResponse)
async def session_detail(request: Request, session_id: int):
    """Session detail page showing all hands"""
    
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session summary
    session_summary = await db.get_session_summary(session_id)
    
    # Get all hands in this session
    hands = await db.get_hand_summaries(session_id)
    
    return templates.TemplateResponse("session_detail.html", {
        "request": request,
        "session": session,
        "session_summary": session_summary,
        "hands": hands
    })

@app.get("/hand/{hand_id}", response_class=HTMLResponse)
async def hand_detail(request: Request, hand_id: int):
    """Hand detail page showing hole cards and all actions"""
    
    hand_detail = await db.get_hand_detail(hand_id)
    if not hand_detail:
        raise HTTPException(status_code=404, detail="Hand not found")
    
    # Get player names for actions
    players = await db.list_players()
    player_names = {p.id: p.name for p in players}
    
    # Group actions by betting round
    actions_by_round = {}
    for action in hand_detail.actions:
        round_name = action.betting_round.value
        if round_name not in actions_by_round:
            actions_by_round[round_name] = []
        actions_by_round[round_name].append(action)
    
    return templates.TemplateResponse("hand_detail.html", {
        "request": request,
        "hand_detail": hand_detail,
        "player_names": player_names,
        "actions_by_round": actions_by_round
    })

@app.get("/player/{player_id}", response_class=HTMLResponse)
async def player_detail(request: Request, player_id: int):
    """Player detail page with stats and hand history"""
    
    player = await db.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Get player stats
    stats = await db.get_player_stats(player_id)
    
    # Get player's hand history
    player_hands = await db.get_player_hands_by_player(player_id)
    
    # Get win percentage over time
    win_percentage_data = await db.get_player_win_percentage_over_time(player_id)
    
    return templates.TemplateResponse("player_detail.html", {
        "request": request,
        "player": player,
        "stats": stats,
        "player_hands": player_hands,
        "win_percentage_data": win_percentage_data
    })

@app.get("/api/sessions")
async def api_sessions():
    """API endpoint to get all sessions"""
    sessions = await db.list_sessions()
    return [session.dict() for session in sessions]

@app.get("/api/session/{session_id}/hands")
async def api_session_hands(session_id: int):
    """API endpoint to get hands for a session"""
    hands = await db.get_hand_summaries(session_id)
    return [hand.dict() for hand in hands]

@app.get("/api/hand/{hand_id}")
async def api_hand_detail(hand_id: int):
    """API endpoint to get detailed hand information"""
    hand_detail = await db.get_hand_detail(hand_id)
    if not hand_detail:
        raise HTTPException(status_code=404, detail="Hand not found")
    return hand_detail.dict()

@app.get("/api/player/{player_id}/stats")
async def api_player_stats(player_id: int):
    """API endpoint to get player statistics"""
    stats = await db.get_player_stats(player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Player not found")
    return stats.dict()

@app.get("/api/player/{player_id}/win-percentage")
async def api_player_win_percentage(player_id: int):
    """API endpoint to get player win percentage over time"""
    data = await db.get_player_win_percentage_over_time(player_id)
    return data

@app.get("/api/model-comparison")
async def api_model_comparison():
    """API endpoint to get model comparison statistics"""
    return await db.get_model_comparison_stats()

@app.get("/api/search/hands")
async def api_search_hands(
    session_id: Optional[int] = None,
    player_id: Optional[int] = None,
    min_pot_size: Optional[int] = None,
    max_pot_size: Optional[int] = None,
    winner_id: Optional[int] = None,
    limit: int = 100
):
    """API endpoint to search hands with filters"""
    hands = await db.search_hands(
        session_id=session_id,
        player_id=player_id,
        min_pot_size=min_pot_size,
        max_pot_size=max_pot_size,
        winner_id=winner_id,
        limit=limit
    )
    return [hand.dict() for hand in hands]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)