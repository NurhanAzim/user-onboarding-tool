# User Onboarding

Automate new employee account creation. Reads names from a Google Sheet, creates a cPanel email + Nextcloud account, and updates status back to the sheet.

## How it works

1. You enter the employee's Firstname and Lastname in a Google Sheet with status `PENDING`
2. Run the script (or set up a cron job)
3. Script generates a password, creates both accounts, marks the row `CREATED` and sends a Telegram notification

### Sheet layout

| Firstname | Lastname | Status | Created At | Password |
|-----------|----------|--------|------------|----------|
| John      | Doe      | PENDING |            |          |

Status values: `PENDING` → `CREATED` or `FAILED`.

## Setup

### 1. Google service account

Create a service account and share your sheet with its email:

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new service account
3. Generate a JSON key and download it as `service-account.json`
4. Place it in the project root (do **not** commit it)
5. Share your Google Sheet with the service account email (Editor role)

### 2. Configuration

```bash
cp config.example.json config.json
```

Edit `config.json`:

| Key | Description |
|-----|-------------|
| `google_sa_path` | Path to the service account JSON file |
| `sheet_id` | Your Google Sheet ID (from the sheet URL) |
| `sheet_name` | Worksheet tab name |
| `nextcloud_url` | Nextcloud server URL |
| `nextcloud_admin` | Nextcloud admin username |
| `nextcloud_password` | Nextcloud admin app password |
| `nextcloud_group` | Group to assign new users to |
| `cpanel_url` | cPanel API URL (port 2083) |
| `cpanel_token` | cPanel API token (`user:token`) |
| `email_domain` | Email domain (e.g. `example.com`) |
| `cpanel_domain` | cPanel domain for email creation |
| `cpanel_quota` | Mailbox quota in MB |
| `telegram_bot_token` | *(optional)* Telegram bot token |
| `telegram_chat_id` | *(optional)* Chat/group ID |
| `telegram_thread_id` | *(optional)* Topic thread ID |

Leave telegram fields as `null` to skip notifications.

### 3. Run

```bash
./run.sh --dry-run    # preview what will be created
./run.sh              # execute
```

The first run creates a Python virtualenv (`.venv`) and installs dependencies automatically.

### 4. Automate (cron)

```bash
crontab -e
```

Add to run every 5 minutes:

```
*/5 * * * * /path/to/user-onboarding/run.sh
```

## Requirements

- Python 3.8+
- cPanel API token
- Nextcloud admin credentials (app password recommended)

## Handover

New maintainer needs:
- `config.json` — service account path + credentials
- `service-account.json` — Google service account key
- `run.sh` handles everything else (venv, deps, execution)
