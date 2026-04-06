# Gresco-Management

## Discord Bot Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set the bot token:
   ```bash
   export DISCORD_TOKEN="your-bot-token"
   ```

3. (Optional) Set a log channel ID for moderation logs:
   ```bash
   export LOG_CHANNEL_ID="123456789012345678"
   ```

4. Run the bot:
   ```bash
   python bot.py
   ```

## Commands

- `/warn @user reason`
- `/timeout @user duration reason`
- `/ban @user reason`
- `/actions @user`
- `/shift promo_shift shift_name host co_host time ping_role`
- `/training store_colleague security host co_host trainer time ping_role`

## Storage

- Moderation actions are saved to `data.json` automatically.
