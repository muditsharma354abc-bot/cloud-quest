// DungeonManager.js
// This script shows how the game talks to the Cloud Quest API.

const cloudQuestAPI = "https://cloud-quest-api-687428638555.us-central1.run.app";

class DungeonManager {
  constructor() {
    this.playerLevel = 1;
    this.skillScore = 0.5;
    this.currentRoom = null;
    this.enemies = [];
  }

  async generateNewDungeon() {
    try {
      const response = await fetch(`${cloudQuestAPI}/generate-dungeon`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_level: this.playerLevel,
          skill_score: this.skillScore,
          dungeon_type: "standard"
        })
      });

      const dungeonData = await response.json();
      this.currentRoom = dungeonData;

      // In Meta Horizon, this is where you'd spawn enemies based on dungeonData.enemies
      console.log("Dungeon generated:", dungeonData);

      return dungeonData;
    } catch (error) {
      console.error("Failed to generate dungeon, using local fallback:", error);
      return this.generateLocalDungeon();
    }
  }

  generateLocalDungeon() {
    return {
      layout: "arena",
      enemies: [],
      loot_chests: 1,
      difficulty_modifier: 0.5,
      description: "Local fallback dungeon."
    };
  }
}

// Example usage (for web testing)
async function testDungeon() {
  const manager = new DungeonManager();
  const dungeon = await manager.generateNewDungeon();
  const pre = document.getElementById("dungeon-output");
  if (pre) {
    pre.textContent = JSON.stringify(dungeon, null, 2);
  }
}

window.addEventListener("load", () => {
  const btn = document.getElementById("generate-btn");
  if (btn) {
    btn.addEventListener("click", testDungeon);
  }
});
