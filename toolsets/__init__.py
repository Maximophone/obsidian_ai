from . import gmail, obsidian, subagents, system, discord

# Define available tool sets
TOOL_SETS = {
    "system": system.TOOLS,
    "obsidian": obsidian.TOOLS,
    "gmail": gmail.TOOLS,
    "subagents": subagents.TOOLS,
    "discord": discord.TOOLS
}
