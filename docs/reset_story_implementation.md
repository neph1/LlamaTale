# Reset Story Implementation

## Overview
This document describes the implementation of the `!reset_story` wizard command that allows restarting/resetting a story without having to restart the server.

## Feature Description
The `!reset_story` command provides a way to reset the game world back to its initial state while keeping the server running and players connected. This is particularly useful for:
- Testing story changes during development
- Recovering from a broken game state
- Restarting a story for a fresh playthrough without disconnecting players

## Usage
As a wizard (user with wizard privileges), type:
```
!reset_story
```

The command will:
1. Prompt for confirmation (as this affects all players)
2. If confirmed, reset the story world
3. Move all players back to their starting locations
4. Display a completion message

## Implementation Details

### Files Modified
- **tale/cmds/wizard.py**: Added the `do_reset_story` wizard command function
- **tale/driver.py**: Added the `reset_story()` method to the Driver class
- **tests/test_reset_story.py**: Added unit tests for the reset functionality

### What Gets Reset
1. **Deferreds**: All scheduled actions are cleared
2. **MudObject Registry**: 
   - All items are removed
   - All NPCs and non-player livings are removed
   - All locations are cleared (except players remain in registry)
   - All exits are cleared
3. **Story Module**: The story module is reloaded from disk
4. **Zones**: All zone modules are unloaded and reloaded
5. **Game Clock**: Reset to the story's epoch or current time
6. **Player Positions**: All players are moved to their designated starting locations

### What Is Preserved
1. **Player Objects**: Player objects remain in the registry with the same vnum
2. **Player Inventory**: Players keep their items
3. **Player Stats**: Player statistics and attributes are preserved
4. **Player Connections**: Active player connections remain intact
5. **Server Uptime**: The server uptime counter continues

### Technical Approach
The implementation handles several challenging aspects:

1. **Module Reloading**: Python modules are removed from `sys.modules` and reimported to get fresh instances
2. **Registry Management**: The MudObjRegistry is selectively cleared to preserve players while removing other objects
3. **Safe Exception Handling**: Specific exceptions are caught when removing players from old locations
4. **Sequence Number Management**: The registry sequence number is adjusted to account for existing player vnums

### Error Handling
- If the story module cannot be reloaded, an error message is displayed
- If starting locations cannot be found, players are notified
- If a player's old location is in an invalid state, the error is caught and ignored
- All exceptions during reset are caught and reported to the wizard who initiated the command

## Testing
The implementation includes comprehensive unit tests:
- Test that the command exists and is registered
- Test that the command is a generator (for confirmation dialog)
- Test that confirmation is required
- Test that the Driver.reset_story method exists
- Test that the command calls the driver's reset method when confirmed

## Future Enhancements
Possible improvements for future versions:
- Option to reset only specific zones
- Option to preserve or clear player inventories
- Backup/restore of game state before reset
- Configuration to exclude certain objects from reset
- Reset statistics tracking (number of resets, last reset time)

## Known Limitations
1. Custom story data not managed by the standard story/zone system may not be properly reset
2. External systems (databases, file caches) are not automatically reset
3. LLM cache and character memories are not cleared (may need manual cleanup)
4. Player wiretaps are not automatically re-established after reset

## Command Documentation
The command includes built-in help accessible via:
```
help !reset_story
```

The help text explains:
- What the command does
- That it requires wizard privileges
- That it affects all players
- What is preserved and what is reset
