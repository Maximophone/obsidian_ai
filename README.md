# Obsidian AI

A file watcher that adds AI capabilities directly into your Obsidian notes. Write questions or instructions using simple tags, save the file, and get AI responses inline.

## How It Works

1. Start the watcher: `python obsidian_ai.py`
2. In any Obsidian note, add an AI block with a `<reply!>` tag
3. Save the file
4. The AI responds directly in your note

```markdown
<ai!>
What are the main themes in this note?
<reply!>
</ai!>
```

After saving, the AI's response appears where `<reply!>` was:

```markdown
<ai!>
What are the main themes in this note?
|AI|
The main themes are...
|ME|
</ai!>
```

## Installation

### Requirements
- Python 3.10+
- [ai_engine](https://github.com/Maximophone/ai_engine) — the `ai_core` package that provides the AI model interface

### Setup

**1. Clone both repositories side by side:**

```bash
# Create a parent directory for both repos
mkdir ~/code && cd ~/code

# Clone ai_engine first (required dependency)
git clone https://github.com/Maximophone/ai_engine.git

# Clone obsidian_ai next to it
git clone https://github.com/Maximophone/obsidian_ai.git

# Your folder structure should look like:
# ~/code/
#   ├── ai_engine/
#   └── obsidian_ai/
```

**2. Run the setup script:**

**macOS/Linux:**
```bash
cd obsidian_ai
./setup_env.sh
```

**Windows (PowerShell):**
```powershell
cd obsidian_ai
.\setup_env.ps1
```

**Windows (CMD):**
```cmd
cd obsidian_ai
setup_env.bat
```

The setup script will automatically install `ai_core` from the sibling `ai_engine` directory.

### Configuration

**1. Copy the example configuration file:**

```bash
cp env.example .env
```

**2. Edit `.env` with your settings:**

```env
# REQUIRED: Path to your Obsidian vault
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# REQUIRED: At least one AI API key
CLAUDE_API_KEY=your-claude-key
# or
OPENAI_API_KEY=your-openai-key
# or
GEMINI_API_KEY=your-gemini-key

# OPTIONAL: For integrations
DISCORD_BOT_TOKEN=your-discord-token
GDRIVE_API_KEY=your-gdrive-key
```

**Vault path examples:**
- macOS: `/Users/yourname/Documents/MyVault`
- Windows: `C:/Users/yourname/Documents/MyVault`
- Linux: `/home/yourname/Documents/MyVault`

> **Note:** If you don't set `OBSIDIAN_VAULT_PATH`, it will try to auto-detect a vault in Google Drive (`My Drive/Obsidian`).

### Getting API Keys for Integrations

#### Discord Bot Token

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name
3. In the left sidebar, click **"Bot"**
4. Click **"Add Bot"** and confirm
5. Under the **Token** section, click **"Reset Token"** then **"Copy"** — this is your `DISCORD_BOT_TOKEN`
6. Scroll down and enable these **Privileged Gateway Intents**:
   - Message Content Intent
   - Server Members Intent (if needed)
7. To invite your bot to a server:
   - Go to **"OAuth2" → "URL Generator"**
   - Select scopes: `bot`
   - Select permissions: `Send Messages`, `Read Message History`, `View Channels`
   - Copy the generated URL and open it in your browser to invite the bot

#### Google Drive API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Drive API**:
   - Go to **"APIs & Services" → "Library"**
   - Search for "Google Drive API" and click **Enable**
4. Create credentials:
   - Go to **"APIs & Services" → "Credentials"**
   - Click **"Create Credentials" → "API Key"**
   - Copy the key — this is your `GDRIVE_API_KEY`
5. (Recommended) Restrict the API key:
   - Click on the newly created key
   - Under **"API restrictions"**, select **"Restrict key"**
   - Choose **"Google Drive API"** from the list
   - Save

> **Note:** For accessing private files, you'll need OAuth 2.0 credentials instead of an API key. See [Google's OAuth setup guide](https://developers.google.com/drive/api/quickstart/python) for details.

## Usage

### Basic AI Queries

```markdown
<ai!>
Explain quantum computing in simple terms.
<reply!>
</ai!>
```

### Choosing a Model

```markdown
<ai!>
<model!opus>
Write a detailed analysis of this research paper.
<reply!>
</ai!>
```

Available models depend on your `ai_core` configuration (e.g., `haiku`, `sonnet`, `opus`, `gpt4`, `gemini`).

### Including Context

**Current document:**
```markdown
<ai!>
<this!>
Summarize the key points above.
<reply!>
</ai!>
```

**Another note:**
```markdown
<ai!>
<doc![[Meeting Notes 2024-01-15]]>
What action items came from this meeting?
<reply!>
</ai!>
```

**A URL:**
```markdown
<ai!>
<url!https://example.com/article>
Summarize this article.
<reply!>
</ai!>
```

**A PDF:**
```markdown
<ai!>
<pdf!Documents/paper.pdf>
What methodology does this paper use?
<reply!>
</ai!>
```

**An image:**
```markdown
<ai!>
<model!sonnet>
<image!Screenshots/chart.png>
Describe what this chart shows.
<reply!>
</ai!>
```

### Using System Prompts

Create prompt files in your vault's `Prompts/` folder, then reference them:

```markdown
<ai!>
<system!code_reviewer>
Review this function for bugs and improvements.
<reply!>
</ai!>
```

### Using Tools

Enable AI tools to interact with external services:

```markdown
<ai!>
<tools!gmail>
Find my most recent email from John and summarize it.
<reply!>
</ai!>
```

**Available toolsets:**
- `system` - File operations, shell commands, Python execution
- `obsidian` - Navigate and read your vault (see below)
- `gmail` - Read and send emails
- `discord` - Send Discord messages
- `subagents` - Create specialized sub-agents

**Obsidian toolset** - Designed for navigating large vaults efficiently:
- `list_vault(directory)` - Browse vault structure with file sizes
- `get_note_outline(filepath)` - See headings, links, and metadata without reading full content
- `read_note(filepath, offset, limit)` - Read notes with line numbers and pagination
- `read_note_section(filepath, heading)` - Read a specific section by heading name
- `search_vault(query, directory)` - Find notes by content or filename
- `get_note_links(filepath)` - See all wikilinks in a note

### Parameters

| Tag | Description | Example |
|-----|-------------|---------|
| `<model!name>` | Choose AI model | `<model!opus>` |
| `<temperature!n>` | Response randomness (0-1) | `<temperature!0.7>` |
| `<max_tokens!n>` | Max response length | `<max_tokens!4000>` |
| `<system!name>` | Use system prompt from Prompts/ | `<system!analyst>` |
| `<think!>` | Enable extended thinking | `<think!>` |
| `<debug!>` | Show debug information | `<debug!>` |

### Getting Help

Type `<help!>` in any note and save to see the full tag reference.

## Running

Simply use the run script (it handles the virtual environment for you):

**macOS/Linux:**
```bash
./run.sh
```

**Windows (PowerShell):**
```powershell
.\run.ps1
```

**Windows (CMD):**
```cmd
run.bat
```

The watcher monitors your vault for file changes. When you save a file containing `<ai!>` blocks with `<reply!>` tags, it processes them automatically.

### Command Line Options

```bash
./run.sh --log-level DEBUG  # Verbose logging
./run.sh --log-level ERROR  # Quiet mode
```

## Project Structure

```
obsidian_ai/
├── obsidian_ai.py          # Entry point
├── obsidian/               # Core functionality
│   ├── obsidian_ai.py      # File processing
│   ├── process_ai_block.py # AI tag handling
│   ├── parser/             # Tag parser
│   └── ...
├── integrations/           # External services
│   ├── discord/            # Discord bot
│   ├── gmail_client.py     # Gmail API
│   ├── gdoc_utils.py       # Google Docs
│   └── notion_integration.py
├── toolsets/               # AI-callable tools
│   ├── system.py           # File/command tools
│   ├── obsidian.py         # Vault tools
│   ├── gmail.py            # Email tools
│   └── discord.py          # Discord tools
├── services/               # Background services
│   └── file_watcher.py     # File monitoring
├── config/                 # Configuration
└── ui/                     # UI components
    └── tool_confirmation.py
```

## License

MIT License - see [LICENSE](LICENSE) for details.
