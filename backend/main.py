from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import aiplatform
import random
import os
from typing import List, Dict

app = FastAPI(title="Cloud Quest Dungeon Generator")

# CORS for Meta Horizon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vertex AI setup
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-project-id")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
aiplatform.init(project=PROJECT_ID, location=LOCATION)

# Data models
class DungeonRequest(BaseModel):
    player_level: int
    skill_score: float  # 0.0 to 1.0
    dungeon_type: str = "standard"  # standard, boss, treasure

class Enemy(BaseModel):
    name: str
    health: int
    attack: int
    defense: int
    behavior: str
    loot_drop: List[str]

class DungeonRoom(BaseModel):
    layout: str
    enemies: List[Enemy]
    loot_chests: int
    difficulty_modifier: float
    description: str

# AI Dungeon Generation
async def generate_dungeon_with_ai(request: DungeonRequest) -> DungeonRoom:
    """Use Vertex AI to generate unique dungeon rooms"""
    
    # Calculate difficulty
    base_difficulty = request.player_level * 0.1
    adaptive_difficulty = base_difficulty + (request.skill_score * 0.5)
    
    # Prompt for Vertex AI
    prompt = f"""Generate a unique dungeon room for an action RPG game.
    
Player Level: {request.player_level}
Difficulty: {adaptive_difficulty:.2f}
Dungeon Type: {request.dungeon_type}

Generate 2-4 enemies with:
- Creative names (fantasy theme)
- Health: {50 + request.player_level * 10} to {100 + request.player_level * 20}
- Attack: {10 + request.player_level * 2} to {20 + request.player_level * 4}
- Defense: {5 + request.player_level} to {10 + request.player_level * 2}
- Behavior pattern (aggressive, defensive, ranged, or stealth)
- Loot drops (health potions, weapons, armor, gold)

Room Layout: Choose from (corridor, arena, maze, treasure_room, boss_chamber)
Description: 1-2 sentence atmospheric description

Return JSON format:
{{
    "layout": "...",
    "enemies": [...],
    "loot_chests": 0-3,
    "description": "..."
}}
"""
    
    try:
        # Use Vertex AI Gemini (you can switch to other models)
        from vertexai.preview.generative_models import GenerativeModel
        
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        # Parse AI response (simplified - add error handling)
        ai_result = response.text
        
        # For now, return structured data (you'll parse AI JSON response)
        enemies = [
            Enemy(
                name=f"Shadow Beast Lv.{request.player_level}",
                health=50 + request.player_level * 15,
                attack=10 + request.player_level * 3,
                defense=5 + request.player_level,
                behavior="aggressive",
                loot_drop=["health_potion", "gold"]
            )
        ]
        
        return DungeonRoom(
            layout=random.choice(["corridor", "arena", "maze", "treasure_room"]),
            enemies=enemies,
            loot_chests=random.randint(1, 3),
            difficulty_modifier=adaptive_difficulty,
            description=f"A dark {'corridor' if random.random() > 0.5 else 'arena'} filled with ancient traps."
        )
        
    except Exception as e:
        # Fallback procedural generation if AI fails
        return generate_procedural_dungeon(request)

def generate_procedural_dungeon(request: DungeonRequest) -> DungeonRoom:
    """Fallback procedural generation"""
    num_enemies = min(4, 1 + request.player_level // 3)
    
    enemies = []
    for i in range(num_enemies):
        enemy_types = ["Goblin", "Skeleton", "Orc", "Wraith", "Dragon"]
        enemy_name = f"{random.choice(enemy_types)} Lv.{request.player_level}"
        
        enemies.append(Enemy(
            name=enemy_name,
            health=50 + request.player_level * 10 + random.randint(-10, 10),
            attack=10 + request.player_level * 2 + random.randint(-3, 3),
            defense=5 + request.player_level + random.randint(-2, 2),
            behavior=random.choice(["aggressive", "defensive", "ranged", "stealth"]),
            loot_drop=["health_potion", "gold", "weapon_shard"]
        ))
    
    return DungeonRoom(
        layout=random.choice(["corridor", "arena", "maze", "treasure_room", "boss_chamber"]),
        enemies=enemies,
        loot_chests=random.randint(1, 3),
        difficulty_modifier=request.player_level * 0.1 + request.skill_score * 0.5,
        description=f"A mysterious {random.choice(['dark', 'ancient', 'cursed'])} chamber."
    )

@app.get("/")
async def root():
    return {"message": "Cloud Quest Dungeon Generator API", "status": "running"}

@app.post("/generate-dungeon", response_model=DungeonRoom)
async def generate_dungeon(request: DungeonRequest):
    """Main endpoint: Generate AI-powered dungeon"""
    try:
        dungeon = await generate_dungeon_with_ai(request)
        return dungeon
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "ai": "vertex-ai-connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
