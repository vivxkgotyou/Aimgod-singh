import asyncio
import os
import threading
import logging
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.users import GetFullUserRequest

app = Flask(__name__)
app.secret_key = "vivek_super_secret_key"

temp_logins = {}
active_tasks = {}

SUPEROWNER_ID = 6133172474
P = r"/"
current_delay = 0.5
SESSION_FILE = "sessions.txt"

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
        .card { background: #111827; padding: 35px; border-radius: 16px; width: 100%; max-width: 440px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 1px solid #1f2937; }
        .brand { text-align: center; margin-bottom: 25px; }
        .brand h1 { color: #38bdf8; font-size: 24px; margin: 0; font-weight: 700; }
        .brand p { color: #94a3b8; font-size: 13px; margin-top: 5px; }
        label { display: block; margin-top: 14px; font-size: 13px; color: #cbd5e1; font-weight: 500; }
        input { width: 100%; padding: 12px; margin-top: 6px; border-radius: 8px; border: 1px solid #374151; background: #030712; color: white; box-sizing: border-box; font-size: 14px; }
        input:focus { outline: none; border-color: #38bdf8; }
        button { width: 100%; background: #0284c7; color: white; padding: 12px; border: none; border-radius: 8px; font-weight: 600; margin-top: 24px; cursor: pointer; font-size: 15px; }
        button:hover { background: #0ea5e9; }
        .flash { background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #fca5a5; padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; text-align: center; }
        .success { background: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; color: #86efac; padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; text-align: center; }
        .string-box { background: #030712; padding: 12px; border-radius: 8px; font-size: 11px; word-break: break-all; color: #38bdf8; margin-top: 12px; border: 1px dashed #374151; max-height: 100px; overflow-y: auto; }
        .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #64748b; }
    </style>
</head>
<body>
    <div class="card">
        <div class="brand">
            <h1>⚡ Vivek's Command Center ⚡</h1>
            <p>Multi-Account Userbot Control Suite</p>
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
            <label>API ID:</label>
            <input type="text" name="api_id" required placeholder="Enter API ID">
            <label>API Hash:</label>
            <input type="text" name="api_hash" required placeholder="Enter API Hash">
            <label>Phone Number (with +91):</label>
            <input type="text" name="phone" required placeholder="+91xxxxxxxxxx">
            <button type="submit">Send OTP Code</button>
        </form>
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
        {% elif step == 'success' %}
        <div style="text-align: center;">
            <p style="color: #4ade80; font-weight: 600; font-size: 16px; margin-bottom: 5px;">✅ Connected Successfully!</p>
            <p style="font-size: 12px; color: #94a3b8;">Session saved & bot activated automatically:</p>
            <div class="string-box">{{ session_string }}</div>
            <a href="/"><button style="margin-top: 20px;">Connect Another Account</button></a>
        </div>
        {% endif %}
        <div class="footer">Automated by Vivek 🇧🇼</div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, step="phone")

@app.route("/send_code", methods=["POST"])
def send_code():
    try:
        api_id = int(request.form.get("api_id"))
        api_hash = request.form.get("api_hash").strip()
        phone = request.form.get("phone").strip()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        client = TelegramClient(StringSession(), api_id, api_hash, loop=loop)
        loop.run_until_complete(client.connect())
        sent = loop.run_until_complete(client.send_code_request(phone))
        
        temp_logins["client"] = client
        temp_logins["phone"] = phone
        temp_logins["phone_code_hash"] = sent.phone_code_hash
        temp_logins["api_id"] = api_id
        temp_logins["api_hash"] = api_hash
        temp_logins["loop"] = loop
        
        return render_template_string(HTML_TEMPLATE, step="otp")
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
            f.write(f"{temp_logins['api_id']}|{temp_logins['api_hash']}|{session_str}\n")
            
        asyncio.run_coroutine_threadsafe(start_single_client(temp_logins['api_id'], temp_logins['api_hash'], session_str), bot_loop)
        return render_template_string(HTML_TEMPLATE, step="success", session_string=session_str)
    except SessionPasswordNeededError:
        return render_template_string(HTML_TEMPLATE, step="password")
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
            f.write(f"{temp_logins['api_id']}|{temp_logins['api_hash']}|{session_str}\n")
            
        asyncio.run_coroutine_threadsafe(start_single_client(temp_logins['api_id'], temp_logins['api_hash'], session_str), bot_loop)
        return render_template_string(HTML_TEMPLATE, step="success", session_string=session_str)
    except Exception as e:
        flash(f"2FA Error: {str(e)}", "error")
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

    @client.on(events.NewMessage(pattern=rf"{P}spam\s+(\d+)\s+(.+)"))
    async def spam_cmd(event):
        if event.sender_id != SUPEROWNER_ID and not event.out: return
        count = int(event.pattern_match.group(1))
        text = event.pattern_match.group(2)
        chat_id = event.chat_id
        await event.delete()
        for _ in range(count):
            await client.send_message(chat_id, text)
            await asyncio.sleep(current_delay)

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
            
            from telethon.tl.functions.account import UpdateProfileRequest
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
            from telethon.tl.functions.account import UpdateProfileRequest
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
        client = TelegramClient(StringSession(session_str), int(api_id), api_hash)
        await client.start()
        me = await client.get_me()
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
