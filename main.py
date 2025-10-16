import discord
from discord.ext import commands
import os
import aiohttp
import asyncio

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# Bot state management
active_channels = set()

# Hollywood Hills EMS S.O.P's document context
SOP_CONTEXT = """
You are providing guidance based strictly on the Hollywood Hills EMS Standard Operating Procedures (S.O.P's). 
This document covers comprehensive protocols for:
- Emergency Medical Services (EMS) response and patient care
- Fire suppression tactics and firefighting procedures
- Water rescue operations and swift water safety protocols
- Technical rescue (confined space, high angle rescue, structural collapse)
- Hazardous materials (HAZMAT) incident response
- Vehicle extrication and traffic incident management
- Mass casualty incidents and disaster response
- Fire prevention, safety inspections, and public education
- Incident command system and organizational protocols

Answer all questions strictly according to these Hollywood Hills EMS S.O.P's. Provide detailed, accurate information 
following the specific procedures outlined in this document. Always prioritize safety and recommend calling 
emergency services (911) for immediate life-threatening emergencies.
"""

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    await bot.tree.sync()
    print('Slash commands synced')

@bot.tree.command(name='activate', description='Activate the LSFD Assistant bot for fire, EMS, and rescue support in this channel')
async def activate(interaction: discord.Interaction):
    """Activate the bot in the current channel with permission checks"""
    
    # Check if user has manage_channels permission
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            '❌ You need "Manage Channels" permission to activate the bot.',
            ephemeral=True
        )
        return
    
    channel_id = interaction.channel_id
    
    if channel_id in active_channels:
        await interaction.response.send_message(
            '⚠️ LSFD Assistant is already active in this channel.',
            ephemeral=True
        )
        return
    
    active_channels.add(channel_id)
    
    await interaction.response.send_message(
        f'✅ **Los Santos Fire Department Assistant Activated!**\n'
        f'🚒 I\'m now monitoring <#{channel_id}> for queries about fire SOPs, EMS procedures, water rescue, and emergency operations.\n'
        f'💡 Ask me anything about LSFD standard operating procedures, emergency response protocols, or safety guidelines!',
        ephemeral=False
    )
    
    print(f'LSFD Assistant activated in channel {channel_id} by {interaction.user}')

@bot.tree.command(name='deactivate', description='Deactivate the LSFD Assistant bot in this channel')
async def deactivate(interaction: discord.Interaction):
    """Deactivate the bot in the current channel with permission checks"""
    
    # Check if user has manage_channels permission
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            '❌ You need "Manage Channels" permission to deactivate the bot.',
            ephemeral=True
        )
        return
    
    channel_id = interaction.channel_id
    
    if channel_id not in active_channels:
        await interaction.response.send_message(
            '⚠️ LSFD Assistant is not active in this channel.',
            ephemeral=True
        )
        return
    
    active_channels.remove(channel_id)
    
    await interaction.response.send_message(
        f'✅ **LSFD Assistant Deactivated**\n'
        f'The bot will no longer respond to messages in <#{channel_id}>.',
        ephemeral=False
    )
    
    print(f'LSFD Assistant deactivated in channel {channel_id} by {interaction.user}')

@bot.tree.command(name='sop', description='Ask any question about EMS, fire, rescue, or operational procedures')
async def sop(interaction: discord.Interaction, question: str):
    """Answer questions about SOPs using Hollywood Hills EMS S.O.P's document as context"""
    
    await interaction.response.defer()
    
    try:
        # Prepend the SOP context to the user's question
        enhanced_query = f"{SOP_CONTEXT}\n\nUser Question: {question}"
        response = await query_perplexity_sop(enhanced_query)
        
        if response:
            await interaction.followup.send(response)
        else:
            await interaction.followup.send('⚠️ Unable to process your query at the moment. Please try again.')
    except Exception as e:
        print(f'Error in /sop command: {str(e)}')
        await interaction.followup.send('⚠️ An error occurred while processing your question. Please try again.')

@bot.tree.command(name='help', description='Get information about LSFD Assistant commands and capabilities')
async def help_command(interaction: discord.Interaction):
    """Display help information about the LSFD Assistant"""
    
    help_text = (
        '🚒 **Los Santos Fire Department Assistant (LSFD Assistant)**\n\n'
        '**Available Commands:**\n'
        '• `/activate` - Activate the bot in this channel (requires Manage Channels permission)\n'
        '• `/deactivate` - Deactivate the bot in this channel (requires Manage Channels permission)\n'
        '• `/sop <question>` - Ask any question about EMS, fire, rescue, or operational procedures\n'
        '• `/help` - Show this help message\n\n'
        '**Capabilities:**\n'
        '🔥 Fire SOPs and firefighting procedures\n'
        '🚑 EMS protocols and medical emergency response\n'
        '🌊 Water rescue operations and safety\n'
        '⚠️ Emergency response procedures\n'
        '📋 Standard operating procedures for LSFD\n\n'
        '**How to Use:**\n'
        '1. Use `/sop` command to ask specific questions about procedures\n'
        '2. Or activate the bot in a channel using `/activate`\n'
        '3. When activated, mention the bot or use keywords like "fire", "ems", "rescue", "emergency", "medical", "safety"\n'
        '4. Ask your question about LSFD procedures, protocols, or operations\n\n'
        '**Example Questions:**\n'
        '• `/sop What are the fire safety protocols for structure fires?`\n'
        '• `/sop How do I perform CPR during a cardiac emergency?`\n'
        '• `/sop What are the water rescue procedures for swift water?`\n'
        '• `/sop What\'s the protocol for hazmat incidents?`\n'
    )
    
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return
    
    # Only respond in active channels
    if message.channel.id not in active_channels:
        return
    
    # Check if bot is mentioned or message contains relevant keywords
    keywords = ['rescue', 'emergency', 'drowning', 'water', 'safety', 'help', 'fire', 'ems', 'medical', 'sop', 'protocol', 'hazmat', 'firefighter', 'paramedic', 'incident']
    is_mentioned = bot.user in message.mentions
    has_keyword = any(keyword in message.content.lower() for keyword in keywords)
    
    if is_mentioned or has_keyword:
        async with message.channel.typing():
            # Prepend SOP context for channel messages too
            enhanced_query = f"{SOP_CONTEXT}\n\nUser Question: {message.content}"
            response = await query_perplexity_sop(enhanced_query)
            if response:
                await message.reply(response)
            else:
                await message.reply('⚠️ Unable to process your query at the moment. Please try again.')

async def query_perplexity_sop(query: str) -> str:
    """Query Perplexity API with SOP-focused context and human-like responses"""
    
    if not PERPLEXITY_API_KEY:
        return '⚠️ Perplexity API key not configured.'
    
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Enhanced system prompt with human-like, emotionally supportive tone
    system_content = (
        'You are a helpful, experienced first responder providing guidance on emergency procedures. '
        'Respond in a helpful, human, and emotionally supportive tone. '
        'Do NOT mention you are an AI or language model. '
        'Answer questions based strictly on the Hollywood Hills EMS Standard Operating Procedures (S.O.P\'s) provided in the context. '
        'Show empathy and understanding while providing clear, accurate procedural information. '
        'Use natural language and conversational phrasing as if you are a colleague sharing knowledge. '
        'When appropriate, acknowledge the emotional weight of emergency situations while maintaining professionalism. '
        'Always prioritize safety and recommend calling 911 for actual emergencies.'
    )
    
    payload = {
        'model': 'sonar',
        'messages': [
            {
                'role': 'system',
                'content': system_content
            },
            {
                'role': 'user',
                'content': query
            }
        ],
        'max_tokens': 800,
        'temperature': 0.8
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return f"🚒 **LSFD Assistant**\n{data['choices'][0]['message']['content']}"
                else:
                    error_text = await response.text()
                    print(f'Perplexity API error: {response.status} - {error_text}')
                    return None
    except asyncio.TimeoutError:
        print('Perplexity API timeout')
        return None
    except Exception as e:
        print(f'Perplexity API exception: {str(e)}')
        return None

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print('ERROR: DISCORD_BOT_TOKEN environment variable not set!')
        exit(1)
    
    print('Starting Los Santos Fire Department Assistant (LSFD Assistant)...')
    bot.run(DISCORD_TOKEN)
