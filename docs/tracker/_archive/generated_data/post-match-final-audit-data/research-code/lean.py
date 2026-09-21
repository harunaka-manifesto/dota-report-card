LEAN = """id durationSeconds startDateTime gameMode lobbyType gameVersionId didRadiantWin numHumanPlayers
 towerDeaths { time npcId isRadiant }
 players { playerSlot isRadiant leaverStatus position lane heroId isVictory
   stats { networthPerMinute lastHitsPerMinute campStack
           itemPurchases { time itemId } itemUsed { itemId count }
           deathEvents { time timeDead } } }"""
def q(ids, name="L"):
    return f"query {name} {{\n" + "\n".join(f"m{j}: match(id: {m}) {{ {LEAN} }}" for j, m in enumerate(ids)) + "\n}"
