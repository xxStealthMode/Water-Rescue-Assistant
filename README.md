# Los Santos Fire Department Assistant (LSFD Assistant) 🚒

## Overview
The Los Santos Fire Department Assistant is an AI-powered Discord bot designed to provide comprehensive guidance and support for fire service, emergency medical services (EMS), and rescue operations. Built with Discord.py and powered by Perplexity AI, this assistant offers real-time access to standard operating procedures (SOPs), protocols, and emergency response information.

## Features
### 🔥 Fire Services
- Fire suppression tactics and strategies
- Firefighting SOPs and best practices
- Fire prevention and safety inspections
- Structure fire protocols
- Wildland firefighting procedures

### 🚑 Emergency Medical Services (EMS)
- EMS protocols and procedures
- Medical emergency response guidelines
- Patient assessment and treatment
- CPR and life-saving techniques
- Medical equipment usage

### 🌊 Rescue Operations
- Water rescue operations and swift water safety
- Technical rescue (confined space, high angle, collapse)
- Vehicle extrication procedures
- Search and rescue operations
- Rope rescue techniques

### ⚠️ Hazmat & Special Operations
- Hazardous materials (HAZMAT) response
- Chemical and biological incident management
- Decontamination procedures
- Safety protocols for special incidents

## Commands

### `/activate`
Activates the LSFD Assistant in the current channel. Requires "Manage Channels" permission.

Example:
```
/activate
```

### `/deactivate`
Deactivates the LSFD Assistant in the current channel. Requires "Manage Channels" permission.

Example:
```
/deactivate
```

### `/sources`
Displays links to the knowledge base sources (Fire SOP, EMS SOP, and Roster).

Example:
```
/sources
```

### `/welcomechannel`
Designate the current channel as the server's welcome log channel. When set, the bot will send join and leave embeds with welcome/goodbye messages that include the server name whenever members join or leave the server.

- Permissions required: Manage Server (Manage Guild)
- Scope: Per-guild. Each server can set its own welcome channel.
- Persistence: The mapping of guild_id -> channel_id is stored in `welcome_channels.json`.

Examples:
```
/welcomechannel
```

The bot will respond:
```
✅ Set this channel as the welcome log for "<Your Server Name>".
```

Once configured, the bot will automatically post embeds in that channel on member join/leave with:
- Member mention and ID
- Server name
- Member avatar as thumbnail

## Usage
1. **Activate the Bot**: Use `/activate` in any channel where you want the assistant to respond
2. **Ask Questions**: Simply type your question in an activated channel; the bot will reply
3. **Welcome Logs**: Use `/welcomechannel` in the channel where you want join/leave embeds to appear

## Setup
1. Create a Discord bot and invite it with the required intents and permissions
2. Set environment variables:
   - `DISCORD_BOT_TOKEN`
   - `PERPLEXITY_API_KEY`
3. Ensure the bot has the following Gateway Intents enabled in the Developer Portal:
   - Server Members Intent (for join/leave events)
   - Message Content (optional for assistant replies)

## Notes
- SOPs and roster are periodically refreshed every 15 minutes (configurable via `SOP_REFRESH_SECONDS`).
- The assistant replies in activated channels and uses Perplexity for answers based on the provided knowledge base.
