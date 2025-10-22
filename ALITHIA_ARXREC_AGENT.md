# Alithia Arxrec Agent Configuration

## Setup

1. Fork this project
2. Go to your repository Settings → Secrets and variables → Actions
3. Add a new repository secret named `ALITHIA_CONFIG_JSON`
4. Set the value to your JSON configuration (see Configuration section below)

**Schedule**: Runs daily at 01:00 UTC

## Configuration

### Configuration Structure

The agent uses a global JSON configuration like [alithia_config_example.json]
(alithia/config/alithia_config_example.json).

### Required Services

#### 1. Zotero
- **Purpose**: Source of your research preferences and existing papers
- **Setup**: 
  1. Create account at [zotero.org](https://www.zotero.org)
  2. Get your user ID from Settings → Feeds/API
  3. Generate API key from Settings → Keys

#### 2. OpenAI API
- **Purpose**: Generate TLDR summaries and extract paper information
- **Setup**: 
  1. Any LLM service providers with OpenAI compatible API
  2. Generate API key from API Keys section

#### 3. Email Service (Gmail recommended)
- **Purpose**: Send paper recommendations
- **Setup**:
  1. Enable 2-factor authentication
  2. Generate App Password for the agent
  3. Use SMTP settings: `smtp.gmail.com:587`

### Configuration Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `zotero_id` | ✅ | Your Zotero user ID | `"1234567"` |
| `zotero_key` | ✅ | Your Zotero API key | `"abc123..."` |
| `smtp_server` | ✅ | SMTP server address | `"smtp.gmail.com"` |
| `smtp_port` | ✅ | SMTP server port | `587` |
| `sender` | ✅ | Sender email address | `"you@gmail.com"` |
| `sender_password` | ✅ | Email app password | `"app_password"` |
| `receiver` | ✅ | Recipient email address | `"recipient@example.com"` |
| `openai_api_key` | ✅ | OpenAI API key | `"sk-..."` |
| `openai_api_base` | ❌ | OpenAI base url | `"https://api.openai.com/v1"` |
| `max_paper_num` | ❌ | Max papers per email | `10` |
| `arxiv_query` | ❌ | ArXiv categories | `"cs.AI+cs.CV"` |
| `debug` | ❌ | Enable debug mode | `false` |

## Troubleshooting

### Common Issues

1. **"Zotero API key invalid"**
   - Regenerate your Zotero API key
   - Check user ID is correct

2. **"SMTP authentication failed"**
   - Use App Password, not regular password
   - Enable 2FA on Gmail account

3. **"OpenAI API key invalid"**
   - Verify account has credits

4. **"No papers found"**
   - Check ArXiv query format
   - Verify Zotero library has papers
   - Try broader categories
