
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import aiplatform
import random
import os
from typing import List

app = FastAPI(title="Cloud Quest Dungeon Generator")

# CORS so Meta Horizon / mobile / web can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # hackathon-friendly; you can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------- VERTEX AI / GEMINI CONFIG -------------

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "lustrous-strand-473308-n1")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_NAME = "gemini-2.5-flash"

VERTEX_ENABLED = False
try:
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    VERTEX_ENABLED = True
except Exception:
    VERTEX_ENABLED = False


# ------------- DATA MODELS -------------

class DungeonRequest(BaseModel):
    player_level: int
    skill_score: float  # 0.0 - 1.0
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


# ------------- GENERATION LOGIC -------------

def generate_procedural_dungeon(request: DungeonRequest) -> DungeonRoom:
    """Fallback procedural generation (works even if Vertex AI fails)."""
    num_enemies = min(4, 1 + request.player_level // 3)

    enemies: List[Enemy] = []
    for _ in range(num_enemies):
        enemy_types = ["Goblin", "Skeleton", "Orc", "Wraith", "Dragon"]
        enemy_name = f"{random.choice(enemy_types)} Lv.{request.player_level}"

        enemies.append(
            Enemy(
                name=enemy_name,
                health=50 + request.player_level * 10 + random.randint(-10, 10),
                attack=10 + request.player_level * 2 + random.randint(-3, 3),
                defense=5 + request.player_level + random.randint(-2, 2),
                behavior=random.choice(
                    ["aggressive", "defensive", "ranged", "stealth"]
                ),
                loot_drop=["health_potion", "gold", "weapon_shard"],
            )
        )

    difficulty = request.player_level * 0.1 + request.skill_score * 0.5

    return DungeonRoom(
        layout=random.choice(
            ["corridor", "arena", "maze", "treasure_room", "boss_chamber"]
        ),
        enemies=enemies,
        loot_chests=random.randint(1, 3),
        difficulty_modifier=difficulty,
        description=f"A mysterious {random.choice(['dark', 'ancient', 'cursed'])} chamber.",
    )


async def generate_dungeon_with_ai(request: DungeonRequest) -> DungeonRoom:
    """
    Main generation: tries Gemini 2.5 Flash on Vertex AI.
    If anything fails, falls back to procedural generation.
    """
    base_difficulty = request.player_level * 0.1
    adaptive_difficulty = base_difficulty + (request.skill_score * 0.5)

    prompt = f"""Generate a unique dungeon room for an action RPG mobile game.

Player Level: {request.player_level}
Difficulty: {adaptive_difficulty:.2f}
Dungeon Type: {request.dungeon_type}

Generate 2-4 enemies with:
- Creative fantasy names
- Health: {50 + request.player_level * 10} to {100 + request.player_level * 20}
- Attack: {10 + request.player_level * 2} to {20 + request.player_level * 4}
- Defense: {5 + request.player_level} to {10 + request.player_level * 2}
- Behavior pattern (aggressive, defensive, ranged, or stealth)
- Loot drops (health potions, weapons, armor, gold)

Room Layout: one of (corridor, arena, maze, treasure_room, boss_chamber)
Description: 1-2 sentence atmospheric description

Return strict JSON with this exact shape:

{{
  "layout": "corridor|arena|maze|treasure_room|boss_chamber",
  "enemies": [
    {{
      "name": "string",
      "health": 0,
      "attack": 0,
      "defense": 0,
      "behavior": "aggressive|defensive|ranged|stealth",
      "loot_drop": ["string", "string"]
    }}
  ],
  "loot_chests": 0,
  "difficulty_modifier": {adaptive_difficulty:.2f},
  "description": "string"
}}
"""

    if not VERTEX_ENABLED:
        return generate_procedural_dungeon(request)

    try:
        from vertexai.preview.generative_models import GenerativeModel
        import json

        model = GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)

        text = response.text.strip()

        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]

        data = json.loads(text)

        enemies = [
            Enemy(
                name=e["name"],
                health=int(e["health"]),
                attack=int(e["attack"]),
                defense=int(e["defense"]),
                behavior=e.get("behavior", "aggressive"),
                loot_drop=list(e.get("loot_drop", [])),
            )
            for e in data.get("enemies", [])
        ]

        if not enemies:
            return generate_procedural_dungeon(request)

        return DungeonRoom(
            layout=data.get("layout", "corridor"),
            enemies=enemies,
            loot_chests=int(data.get("loot_chests", 1)),
            difficulty_modifier=float(
                data.get("difficulty_modifier", adaptive_difficulty)
            ),
            description=data.get(
                "description",
                "A dynamically generated dungeon chamber powered by Gemini 2.5 Flash.",
            ),
        )

    except Exception:
        return generate_procedural_dungeon(request)


# ------------- ROUTES -------------

@app.get("/")
async def root():
    return {
        "message": "Cloud Quest Dungeon Generator API",
        "status": "running",
        "vertex_enabled": VERTEX_ENABLED,
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "model": MODEL_NAME,
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ai": "vertex-ai-connected" if VERTEX_ENABLED else "fallback-only",
        "project_id": PROJECT_ID,
    }


@app.post("/generate-dungeon", response_model=DungeonRoom)
async def generate_dungeon(request: DungeonRequest):
    """Main endpoint: Generate AI-powered dungeon."""
    try:
        dungeon = await generate_dungeon_with_ai(request)
        return dungeon
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF
