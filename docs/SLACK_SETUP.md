# Slack Integration Setup Guide

This guide walks you through setting up Slack integration for the Cash Logistics Optimizer agent. The agent uses Slack to send alerts about missed pickups, insurance limit warnings, and weekly reports.

## Prerequisites

- A Slack workspace where you have permission to install apps
- Admin or app installation permissions in your workspace

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)

2. Click **Create New App**

3. Choose **From scratch**

4. Enter the following:
   - **App Name**: `Cash Logistics Bot` (or your preferred name)
   - **Workspace**: Select your workspace from the dropdown

5. Click **Create App**

You'll be taken to your app's configuration page.

## Step 2: Configure OAuth Scopes

The bot needs specific permissions to send messages. Here's how to set them up:

1. In the left sidebar, click **OAuth & Permissions**

2. Scroll down to the **Scopes** section

3. Under **Bot Token Scopes**, click **Add an OAuth Scope** and add:

   | Scope | Purpose |
   |-------|---------|
   | `chat:write` | Send messages to channels |
   | `channels:read` | View basic channel info |

   > **Note**: `chat:write` is required. `channels:read` is optional but helpful for listing available channels.

4. Your scopes section should look like this:

   ```
   Bot Token Scopes
   ├── chat:write      - Send messages as @Cash Logistics Bot
   └── channels:read   - View basic information about public channels
   ```

## Step 3: Install App to Workspace

1. Scroll up to the **OAuth Tokens for Your Workspace** section

2. Click **Install to Workspace**

3. Review the permissions and click **Allow**

4. You'll be redirected back to the OAuth & Permissions page

5. Copy the **Bot User OAuth Token** - it starts with `xoxb-`

   ```
   Bot User OAuth Token
   xoxb-xxxx-xxxx-xxxx
   ```

   > **Important**: Keep this token secret! Anyone with this token can send messages as your bot.

## Step 4: Save Your Token

1. In your project directory, copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your token:

   ```bash
   SLACK_BOT_TOKEN=xoxb-your-actual-token-here
   SLACK_DEFAULT_CHANNEL=#cash-logistics-alerts
   ```

3. Save the file

## Step 5: Create the Alerts Channel

1. In Slack, create a new channel:
   - Click the **+** next to "Channels" in the sidebar
   - Select **Create a channel**
   - Name it `cash-logistics-alerts` (or your preferred name)
   - Choose Public or Private (Public is easier for testing)
   - Click **Create**

2. If you chose a different channel name, update your `.env`:

   ```bash
   SLACK_DEFAULT_CHANNEL=#your-channel-name
   ```

## Step 6: Invite the Bot to Your Channel

**This step is required!** The bot cannot post to a channel unless it's a member.

### Option A: Using the /invite command

1. Go to your `#cash-logistics-alerts` channel
2. Type: `/invite @Cash Logistics Bot`
3. Press Enter

### Option B: Through channel settings

1. Go to your channel
2. Click the channel name at the top to open settings
3. Go to the **Integrations** tab
4. Click **Add apps**
5. Find and add **Cash Logistics Bot**

## Step 7: Test the Integration

Run the test script to verify everything is working:

```bash
python scripts/test_slack.py
```

Expected output:

```
Slack Integration Test
======================

✓ SLACK_BOT_TOKEN is set
✓ SLACK_DEFAULT_CHANNEL: #cash-logistics-alerts

Testing connection...
✓ Successfully connected to Slack
✓ Bot name: Cash Logistics Bot
✓ Workspace: Your Workspace Name

Sending test message...
✓ Message sent successfully!

Check your #cash-logistics-alerts channel for the test message.
```

## Troubleshooting

### "not_in_channel" error

The bot isn't a member of the channel. See Step 6 to invite it.

### "channel_not_found" error

- Check that the channel name in `.env` includes the `#` prefix
- Verify the channel exists and isn't archived
- For private channels, the bot must be explicitly invited

### "invalid_auth" error

- Your token may be incorrect or expired
- Go back to [api.slack.com/apps](https://api.slack.com/apps), select your app, and get a fresh token from OAuth & Permissions

### "missing_scope" error

You're missing required OAuth scopes. Go back to Step 2 and ensure `chat:write` is added, then reinstall the app.

### Bot posts but I don't see messages

- Check you're looking at the right channel
- Check your Slack notification settings
- Try mentioning the channel in the test: `#cash-logistics-alerts`

## Finding Channel IDs (Advanced)

Some configurations require the channel ID instead of the name. Here's how to find it:

### Option A: From Slack URL

1. Open the channel in Slack (web or desktop)
2. Look at the URL: `https://app.slack.com/client/T12345/C67890`
3. The channel ID is the part starting with `C` (e.g., `C67890`)

### Option B: Right-click method

1. Right-click on the channel name
2. Select **Copy link**
3. Paste it somewhere - the channel ID is in the URL

### Option C: Using the API

```bash
# List channels (requires channels:read scope)
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  https://slack.com/api/conversations.list | jq '.channels[] | {name, id}'
```

## Security Best Practices

1. **Never commit `.env` to git** - It's already in `.gitignore`

2. **Use environment variables in production** - Don't hardcode tokens

3. **Rotate tokens if exposed** - If your token leaks:
   - Go to your app settings
   - Click **OAuth & Permissions**
   - Click **Reinstall to Workspace** to generate a new token

4. **Use private channels for sensitive alerts** - Public channels are visible to everyone in the workspace

## Next Steps

Once Slack is configured, the Cash Logistics Optimizer agent can:

- Send alerts when stores approach insurance limits
- Notify about missed pickups for SLA credit recovery
- Post weekly summary reports
- Escalate urgent issues in real-time

Run the demo to see it in action:

```bash
python src/demo_runner.py --scripted
```

---

## Quick Reference

| Item | Value |
|------|-------|
| Slack App Console | [api.slack.com/apps](https://api.slack.com/apps) |
| Required Scopes | `chat:write`, `channels:read` |
| Token Prefix | `xoxb-` |
| Default Channel | `#cash-logistics-alerts` |
| Test Script | `python scripts/test_slack.py` |
