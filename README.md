# PlayHt Discord Bot
PlayHT TTS Discord Bot

## Set Up
1. Create .env at project's base dir
2. Add env variables
3. Installed required pip packages (after creating python env)
   `pip install -r requirements.txt`
4. Run bot locally
   `python bot.py`
   or in a Heroku App (Proc file provided)

## Env
| Environment Variable  | Description  |
| ----------------------| -------------|
| DISCORD_TOKEN         | Discord token for bot  |
| COMMAND_PREFIX        | Prefixes for commands (for slash commands need '/' in here or leave default) in string array '["\", "!"]'  |
