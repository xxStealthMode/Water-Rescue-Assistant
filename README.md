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

**Example:**
```
/activate
```

### `/deactivate`
Deactivates the LSFD Assistant in the current channel. Requires "Manage Channels" permission.

**Example:**
```
/deactivate
```

### `/help`
Displays comprehensive help information about available commands and capabilities.

**Example:**
```
/help
```

## Usage

1. **Activate the Bot**: Use `/activate` in any channel where you want the assistant to respond
2. **Ask Questions**: Simply mention the bot or use keywords related to fire, EMS, or rescue operations
3. **Get Instant Answers**: The bot will query Perplexity AI and provide detailed, accurate responses based on standard operating procedures

### Keywords That Trigger Responses
The bot automatically responds when it detects these keywords in messages:
- Fire-related: `fire`, `firefighter`, `hazmat`, `incident`
- EMS-related: `ems`, `medical`, `paramedic`, `emergency`
- Rescue-related: `rescue`, `water`, `drowning`, `safety`
- General: `help`, `sop`, `protocol`

### Example Questions

- "What are the fire safety protocols for structure fires?"
- "How do I perform CPR during a cardiac emergency?"
- "What are the water rescue procedures for swift water?"
- "What's the protocol for hazmat incidents?"
- "What equipment is needed for high angle rescue?"
- "How should we approach a vehicle extrication?"

## Setup & Deployment

### Prerequisites
- Python 3.9+
- Discord Bot Token
- Perplexity API Key

### Environment Variables

```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/xxStealthMode/Water-Rescue-Assistant.git
cd Water-Rescue-Assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables (create `.env` file or set in your deployment platform)

4. Run the bot:
```bash
python main.py
```

### Railway Deployment

This bot is configured for deployment on Railway:

1. Fork this repository
2. Connect your Railway account to GitHub
3. Create a new project from your forked repository
4. Add environment variables:
   - `DISCORD_BOT_TOKEN`
   - `PERPLEXITY_API_KEY`
5. Deploy!

The bot will automatically start and sync slash commands with Discord.

## Technical Details

### Dependencies
- `discord.py` - Discord API wrapper
- `aiohttp` - Async HTTP client for API requests
- `python-dotenv` - Environment variable management (for local development)

### Architecture
- **Bot Framework**: Discord.py with slash commands
- **AI Backend**: Perplexity AI (Sonar model)
- **State Management**: In-memory channel tracking
- **Permissions**: Channel-based activation with admin controls

### AI System Prompt
The bot uses an enhanced system prompt that instructs the AI to respond as an expert LSFD Assistant with knowledge of:
- Fire service standard operating procedures
- EMS protocols and medical emergency procedures
- Water and technical rescue operations
- HAZMAT response and safety protocols
- NFPA standards and best practices

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.

## License

This project is open source and available for use by fire departments, emergency services, and public safety organizations.

## Support

For questions, issues, or support, please open an issue on GitHub or contact the repository maintainer.

---

**Note**: This bot provides informational guidance based on standard fire service and EMS practices. Always follow your department's specific SOPs and protocols. For immediate life-threatening emergencies, always call 911.
