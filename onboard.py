#!/usr/bin/env python3
import argparse
import json
import os
import secrets
import string
from datetime import datetime, timezone

import gspread
import requests
from google.oauth2 import service_account

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path=None):
    with open(path or CONFIG_PATH) as f:
        return json.load(f)


def generate_password(length=14):
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(chars) for _ in range(length))


def get_sheet(cfg):
    creds = service_account.Credentials.from_service_account_file(
        cfg["google_sa_path"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    return client.open_by_key(cfg["sheet_id"]).worksheet(cfg["sheet_name"])


def create_cpanel_email(cfg, username, password):
    resp = requests.post(
        f"{cfg['cpanel_url']}/execute/Email/add_pop",
        headers={"Authorization": f"cpanel {cfg['cpanel_token']}"},
        data={
            "email": username,
            "domain": cfg["cpanel_domain"],
            "password": password,
            "quota": cfg["cpanel_quota"],
        },
    )
    data = resp.json()
    if not data.get("status"):
        raise RuntimeError(f"cPanel error: {data.get('errors', resp.text)}")
    return data


def create_nextcloud_user(cfg, username, password, firstname, lastname):
    resp = requests.post(
        f"{cfg['nextcloud_url'].rstrip('/')}/ocs/v2.php/cloud/users",
        auth=(cfg["nextcloud_admin"], cfg["nextcloud_password"]),
        headers={"OCS-APIRequest": "true"},
        json={
            "userid": username,
            "password": password,
            "displayName": f"{firstname} {lastname}".strip(),
            "groups": [cfg["nextcloud_group"]],
        },
    )
    if not resp.ok:
        body = resp.json()
        msg = body.get("ocs", {}).get("meta", {}).get("message", resp.text)
        raise RuntimeError(f"Nextcloud error: {msg}")
    return resp.json()


def send_telegram(cfg, text):
    if not cfg.get("telegram_bot_token"):
        return
    params = {"chat_id": cfg["telegram_chat_id"], "text": text}
    if cfg.get("telegram_thread_id"):
        params["message_thread_id"] = cfg["telegram_thread_id"]
    requests.post(
        f"https://api.telegram.org/bot{cfg['telegram_bot_token']}/sendMessage",
        json=params,
    )


def main(dry_run=False):
    cfg = load_config()
    sheet = get_sheet(cfg)
    records = sheet.get_all_records()

    status_col = None
    for i, h in enumerate(sheet.row_values(1), start=1):
        if h == "Status":
            status_col = i
            break

    updated = 0
    for idx, row in enumerate(records, start=2):
        if row.get("Status", "").strip().upper() != "PENDING":
            continue

        first = row.get("Firstname", "").strip().lower()
        last = row.get("Lastname", "").strip().lower()
        if not first or not last:
            continue

        username = f"{first}.{last}"
        email = f"{username}@{cfg['email_domain']}"
        password = generate_password()

        if dry_run:
            print(f"[DRY-RUN] Would create: {first}.{last} / {email} / {password}")
            continue

        errors = []
        try:
            create_cpanel_email(cfg, username, password)
        except Exception as e:
            errors.append(f"cPanel: {e}")

        try:
            create_nextcloud_user(cfg, username, password, first, last)
        except Exception as e:
            errors.append(f"Nextcloud: {e}")

        now = datetime.now(timezone.utc).isoformat()
        if errors:
            sheet.update_cell(idx, status_col, "FAILED")
            sheet.update_cell(idx, status_col + 1, errors[0])
            send_telegram(cfg, f"FAIL: {first}.{last}\n" + "\n".join(errors))
        else:
            sheet.update_cell(idx, status_col, "CREATED")
            sheet.update_cell(idx, status_col + 1, now)
            send_telegram(
                cfg,
                f"email: {email}\n"
                f"password: {password}\n"
                f"\n"
                f"Email: {cfg['email_access_url']}\n"
                f"Nextcloud: {cfg['nextcloud_url']}",
            )

        updated += 1

    if updated == 0:
        print("No PENDING rows found.")
    else:
        print(f"Processed {updated} row(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
