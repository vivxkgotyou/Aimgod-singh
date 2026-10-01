import asyncio
import time
import os
import json
import random
import logging
from threading import Thread
from contextlib import suppress
from typing import Optional, Dict
from flask import Flask, render_template_string
from telethon import TelegramClient, events, types, functions, errors
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from gtts import gTTS

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# ================= FLASK SERVER FOR RENDER (COLORFUL UI) =================
app = Flask(__name__)

# HTML & CSS template colorful animation ke saath
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIMGOD BOT STATUS</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            background-color: #0d0d1a;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow: hidden;
        }
        .container {
            text-align: center;
            padding: 40px;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.03);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .live-title {
            font-size: 4rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 3px;
            background: linear-gradient(45deg, #ff007f, #7f00ff, #00f0ff, #00ff66, #ff007f);
            background-size: 400% 400%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientAnimation 6s ease infinite, pulse 1.5s ease-in-out infinite alternate;
        }
        .subtitle {
            margin-top: 15px;
            color: #a0a0c0;
            font-size: 1.2rem;
            letter-spacing: 2px;
        }
        .status-badge {
            display: inline-block;
            margin-top: 25px;
            padding: 8px 20px;
            background: rgba(0, 255, 102, 0.15);
            color: #00ff66;
            border: 1px solid #00ff66;
            border-radius: 50px;
            font-weight: bold;
            box-shadow: 0 0 15px rgba(0, 255, 102, 0.4);
        }
        @keyframes gradientAnimation {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            100% { transform: scale(1.03); }
        }
        @media (max-width: 600px) {
            .live-title {
                font-size: 2.2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="live-title">⚡ AIMGOD BOT IS LIVE ⚡</h1>
        <p class="subtitle">24/7 ULTRA HIGH-SPEED SYSTEM</p>
        <div class="status-badge">● ONLINE & ACTIVE</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= CONFIGURATION =================
API_ID = 27220803
API_HASH = 'a879e56a7d79c4b4396ae9190d87e365'

SUPER_OWNERS = {5427447587, 8925057904}

SESSION_NAME = 'aimgod_final'
IMAGE_DATA_FILE = 'image_data.json'
IMAGE_FOLDER = 'image_replies'
GAALI_FILE = 'gaali.txt'
HUNT_FILE = 'hunt.txt'
BANNER_FOLDER = 'banners'

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(BANNER_FOLDER, exist_ok=True)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH, auto_reconnect=True, connection_retries=None)

# --- Memory Core ---
snipe_data = {}
spam_active = {}
vortex_active = {}
current_speed = 0.5
global_mute_users = {}
lock_data = {}
image_reply_active = {}
user_images = {}
image_target = {}
image_delay = {}
photo_mode = {}
target_data = {}
target_loop_index = {}
original_profile = {"first_name": "", "last_name": "", "about": ""}
sudo_users = set()
host_account_id = None
blacklist = {}

# ================= HUNT SYSTEM =================
hunt_data = {}
hunt_tasks = {}
hunt_index = {}

# ================= PULSE / REACT MODULE =================
react_target = {}

def set_pulse(chat_id: int, user_id: int, emoji: str):
    react_target[(chat_id, user_id)] = emoji
    return True

def remove_pulse(chat_id: int, user_id: int):
    return react_target.pop((chat_id, user_id), None)

def clear_chat_pulses(chat_id: int):
    keys_to_remove = [k for k in react_target if k[0] == chat_id]
    for k in keys_to_remove:
        react_target.pop(k, None)
    return len(keys_to_remove)

def get_pulse(chat_id: int, user_id: int):
    return react_target.get((chat_id, user_id))

def list_pulses(chat_id: int = None):
    if chat_id is None:
        return dict(react_target)
    return {k: v for k, v in react_target.items() if k[0] == chat_id}

async def apply_reaction(client_ref, chat_id: int, msg_id: int, user_id: int):
    emoji = get_pulse(chat_id, user_id)
    if not emoji:
        return False
    try:
        await client_ref(functions.messages.SendReactionRequest(
            peer=chat_id,
            msg_id=msg_id,
            reaction=[types.ReactionEmoji(emoticon=emoji)]
        ))
        return True
    except Exception as e:
        logger.debug(f"Pulse reaction failed: {e}")
        return False

# ================= BANNER SYSTEM =================
def list_banners():
    if not os.path.exists(BANNER_FOLDER):
        return []
    return sorted([f for f in os.listdir(BANNER_FOLDER) if f.startswith('banner_')])

def get_banner_by_id(banner_id):
    for f in os.listdir(BANNER_FOLDER):
        if f.startswith(f'banner_{banner_id}.'):
            return os.path.join(BANNER_FOLDER, f)
    return None

# ================= PERSISTENCE (Images only) =================
def save_image_data():
    to_save = {}
    for (cid, uid), imgs in user_images.items():
        to_save[f"{cid}_{uid}"] = {}
        for iid, info in imgs.items():
            to_save[f"{cid}_{uid}"][iid] = {'path': info['path'], 'caption': info.get('caption', '')}
    meta = {
        'images': to_save,
        'image_delay': {f"{c}_{u}": d for (c, u), d in image_delay.items()},
        'photo_mode': {f"{c}_{u}": m for (c, u), m in photo_mode.items()}
    }
    try:
        with open(IMAGE_DATA_FILE, 'w') as f:
            json.dump(meta, f, indent=2)
    except Exception as e:
        print(f"?? Save img error: {e}")

def load_image_data():
    global user_images, image_delay, photo_mode
    if not os.path.exists(IMAGE_DATA_FILE):
        return
    try:
        with open(IMAGE_DATA_FILE, 'r') as f:
            data = json.load(f)
        if 'images' in data:
            images_data = data.get('images', {})
            for k, d in data.get('image_delay', {}).items():
                parts = k.split('_', 1)
                if len(parts) == 2:
                    image_delay[(int(parts[0]), int(parts[1]))] = d
            for k, m in data.get('photo_mode', {}).items():
                parts = k.split('_', 1)
                if len(parts) == 2:
                    photo_mode[(int(parts[0]), int(parts[1]))] = m
        else:
            images_data = data
        for k, imgs in images_data.items():
            parts = k.split('_', 1)
            if len(parts) == 2:
                cid, uid = int(parts[0]), int(parts[1])
                user_images[(cid, uid)] = {}
                for iid, info in imgs.items():
                    if os.path.exists(info['path']):
                        user_images[(cid, uid)][iid] = {'path': info['path'], 'caption': info.get('caption', '')}
        print(f"? Loaded images for {len(user_images)} users.")
    except Exception as e:
        print(f"?? Load img error: {e}")

# ================= HELPERS =================
async def safe_respond(event, text):
    try:
        await event.edit(text)
    except Exception as e1:
        try:
            await client.send_message(event.chat_id, text)
        except Exception as e2:
            print(f"? safe_respond failed: edit={e1} send={e2}")

async def parse_user_from_arg(arg, event):
    arg = arg.strip()
    if arg.startswith('@'):
        try:
            user = await client.get_entity(arg)
            return user.id
        except:
            return None
    elif arg.isdigit():
        return int(arg)
    return None

async def get_user_from_reply(event):
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            return reply.sender_id
    return None

async def resolve_target_user(cmd_args, event):
    if cmd_args:
        first = cmd_args.split()[0]
        uid = await parse_user_from_arg(first, event)
        if uid:
            return uid
        return None
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            return reply.sender_id
    return None

def get_mention_html(user):
    name = user.first_name or "User"
    return f'<a href="tg://user?id={user.id}">{name}</a>'

def load_gaali_lines():
    if not os.path.exists(GAALI_FILE):
        return None
    try:
        with open(GAALI_FILE, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
        return lines if lines else None
    except Exception as e:
        print(f"?? gaali read error: {e}")
        return None

def load_hunt_lines():
    if not os.path.exists(HUNT_FILE):
        return None
    try:
        with open(HUNT_FILE, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
        return lines if lines else None
    except Exception as e:
        print(f"?? hunt read error: {e}")
        return None

def get_next_gaali(chat_id):
    lines = load_gaali_lines()
    if not lines:
        return None
    idx = target_loop_index.get(chat_id, 0)
    if idx >= len(lines):
        idx = 0
    line = lines[idx]
    target_loop_index[chat_id] = idx + 1
    return line

def get_next_hunt_line(chat_id):
    lines = load_hunt_lines()
    if not lines:
        return None
    idx = hunt_index.get(chat_id, 0)
    if idx >= len(lines):
        idx = 0
    line = lines[idx]
    hunt_index[chat_id] = idx + 1
    return line

def is_media(event):
    if event.photo: return True
    if event.video: return True
    if event.document:
        mime = event.document.mime_type or ""
        if mime.startswith('image/') or mime.startswith('video/'):
            return True
    return False

async def text_to_voice(text):
    filename = f"vn_{int(time.time())}.mp3"
    def generate():
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        return filename
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate)

async def join_client_via_link(link: str):
    link = link.strip()
    if not link.startswith("http"):
        link = "https://" + link
    if "/joinchat/" in link:
        h = link.split("/joinchat/")[1].split("?")[0]
        return await client(ImportChatInviteRequest(hash=h))
    if "/+" in link:
        h = link.split("/+")[1].split("?")[0]
        return await client(ImportChatInviteRequest(hash=h))
    username = link.rstrip("/").split("/")[-1]
    return await client(JoinChannelRequest(channel=username))

async def kick_user(chat_id, user_id):
    try:
        await client.kick_participant(chat_id, user_id)
        return True
    except Exception as e:
        print(f"Kick error: {e}")
        return False

# ================= HUNT LOOP =================
async def hunt_loop(chat_id, target_user_id, delay):
    print(f"?? Hunt commenced ? user {target_user_id} in chat {chat_id}")
    try:
        user = await client.get_entity(target_user_id)
    except:
        user = None

    while True:
        key = (chat_id, target_user_id)
        if key not in hunt_data or not hunt_data[key].get('active'):
            print(f"?? Hunt concluded")
            break

        line = get_next_hunt_line(chat_id)
        if not line:
            print(f"?? hunt.txt empty")
            await asyncio.sleep(2)
            continue

        try:
            if user:
                mention = get_mention_html(user)
            else:
                mention = f'<a href="tg://user?id={target_user_id}">User</a>'
            msg = f"{mention} {line}"
            await client.send_message(chat_id, msg, parse_mode='html')
            print(f"?? Hunt message dispatched")
        except errors.FloodWaitError as fw:
            print(f"? Rate limited: {fw.seconds}s")
            await asyncio.sleep(fw.seconds)
        except Exception as e:
            print(f"? Hunt error: {type(e).__name__}: {e}")
            break

        await asyncio.sleep(delay)

    print(f"?? Hunt loop terminated")
    hunt_tasks.pop(chat_id, None)

# ================= MENU =================
MENU_TEXT = """
**?----------------------------------------------?**
**     ?? #AIMGOD ?? FINAL INTERFACE ?**
**?----------------------------------------------?**

**??? ???? ??????????**
`-execute` — Invoke control panel
`-latency` — Measure response delay
`-flow <ms>` — Calibrate strike interval
`-status` — Display live protocol status

**?? ?????x & ????? ??????**
`-vortex <text>` (reply) — Ignite rotational flood
`-stopvortex` — Freeze vortex engine
`-burst <text>` — Unleash relentless barrage
`-stopburst` — Halt barrage protocol

**?? ???? ??????**
`-hunt` (reply) — Commence tactical pursuit
`-stophunt` — Terminate pursuit
`-huntdelay <sec>` (reply) — Adjust pursuit interval
`-huntlist` — Display active pursuits

**?? ????? ??????**
`-pulse <emoji>` (reply) — Inject pulse signature
`-stoppulse` (reply) — Detach pulse
`-pulselist` — Display active pulses

**?? ?????? ??????????**
`-target` (reply/mention/id) — Designate target
`-stoptarget` — Release target
`-targetdelay <sec>` — Adjust response delay
`-targetlist` — Display current targets

**?? ???????? ???o??????**
`-clone` (reply) — Replicate target identity
`-restore` — Revert to original self

**?? ??????? ??????????**
`-lockchat` / `-unlockchat`
`-globalmute` / `-globalunmute` / `-mutelist`
`-blacklist` / `-rmblacklist` / `-blackliststatus`

**??? ????? ???????**
`-setimageuser` / `-reloadimage` / `-imagereply`
`-imagestop` / `-imagedelay` / `-photomode`
`-offphotomode` / `-imagelist` / `-imageclear`

**?? ???????-?????**
`-snipe <text>` (reply) — Arm counter-strike
`-stopsnipe` (reply) — Disarm counter-strike

**??? ?????????**
`-vn <text>` — Synthesize voice note
`-kill` — Full local reset
`-superinvite <link>` — Infiltrate group
`-addsudo` / `-removesudo` / `-sudolist`

**----------------------------------------------**
**      ? ??????? ?? ?????? ?**
"""

# ========== UNIFIED HANDLER ==========
@client.on(events.NewMessage)
async def unified_handler(event):
    global spam_active, vortex_active, current_speed, original_profile, sudo_users, host_account_id
    global global_mute_users, lock_data, snipe_data, blacklist
    global image_reply_active, user_images, image_target, image_delay, photo_mode
    global target_data, target_loop_index
    global hunt_data, hunt_tasks, hunt_index
    global react_target

    chat_id = event.chat_id
    sender_id = event.sender_id
    raw_text = event.raw_text or ''
    key = (chat_id, sender_id)

    # ==========================================
    # ============ COMMANDS (- prefix) =========
    # ==========================================
    if raw_text.startswith('-'):
        if not (sender_id in SUPER_OWNERS or sender_id == host_account_id or sender_id in sudo_users):
            print(f"?? Unauthorized attempt by ID: {sender_id}")
            return

        cmd = raw_text[1:].split(' ', 1)
        cmd_name = cmd[0].lower() if cmd else ''
        cmd_args = cmd[1] if len(cmd) > 1 else ""

        if not cmd_name:
            return

        def is_super_owner():
            return sender_id in SUPER_OWNERS

        try:
            # ===== SYSTEM =====
            if cmd_name == 'execute':
                banners = list_banners()
                if banners:
                    chosen = random.choice(banners)
                    banner_path = os.path.join(BANNER_FOLDER, chosen)
                    try:
                        await event.delete()
                    except:
                        pass
                    try:
                        await client.send_file(
                            chat_id,
                            banner_path,
                            caption=MENU_TEXT,
                            parse_mode='md'
                        )
                        return
                    except Exception as e:
                        print(f"?? Banner send failed: {e}")
                await safe_respond(event, MENU_TEXT)

            elif cmd_name == 'latency':
                pings = []
                try:
                    for _ in range(3):
                        st = time.time()
                        await client(functions.help.GetNearestDcRequest())
                        pings.append((time.time() - st) * 1000)
                        await asyncio.sleep(0.1)
                except Exception:
                    pass

                if pings:
                    ping = round(min(pings), 2)
                    avg = round(sum(pings) / len(pings), 2)
                    jitter = round(max(pings) - min(pings), 2)
                else:
                    ping = 0.0
                    avg = 0.0
                    jitter = 0.0

                if ping < 100:
                    status = "`?x???????`"
                elif ping < 200:
                    status = "`????`"
                elif ping < 400:
                    status = "`??????????`"
                else:
                    status = "`????`"

                await safe_respond(event,
                    f"??? **Satellite relay:** `{ping}ms`\n"
                    f"?? **Average:** `{avg}ms` | **Jitter:** `{jitter}ms`\n"
                    f"?? **Connection status:** {status}"
                )

            elif cmd_name == 'flow' and cmd_args:
                try:
                    current_speed = int(cmd_args) / 1000
                    await safe_respond(event, f"?? **Attack flow rate calibrated to** `{cmd_args}ms` — Synchronization complete.")
                except:
                    await safe_respond(event, "? **Invalid parameter.** Please supply a numeric interval.")

            elif cmd_name == 'status':
                lines = []

                if vortex_active.get(chat_id):
                    lines.append("• ?? **Vortex Engine** ? `???????`")
                if spam_active.get(chat_id):
                    lines.append("• ?? **Burst Barrage** ? `???????`")

                chat_pulses = list_pulses(chat_id)
                if chat_pulses:
                    lines.append(f"• ?? **Active Pulses** ? `{len(chat_pulses)} ?????`")

                chat_hunts = [k for k, d in hunt_data.items() if k[0] == chat_id and d.get('active')]
                if chat_hunts:
                    lines.append(f"• ?? **Active Hunts** ? `{len(chat_hunts)} ???????`")

                chat_targets = [k for k, d in target_data.items() if k[0] == chat_id and d.get('active')]
                if chat_targets:
                    lines.append(f"• ?? **Active Targets** ? `{len(chat_targets)} ?????`")

                chat_snipes = [k for k in snipe_data if k[0] == chat_id]
                if chat_snipes:
                    lines.append(f"• ?? **Armed Snipes** ? `{len(chat_snipes)} ???????`")

                chat_img_replies = [k for k in image_reply_active if k[0] == chat_id]
                if chat_img_replies:
                    lines.append(f"• ??? **Image Protocols** ? `{len(chat_img_replies)} ?????`")

                if chat_id in lock_data:
                    lines.append("• ?? **Chat Lock** ? `???????`")

                if chat_id in global_mute_users and global_mute_users[chat_id]:
                    lines.append(f"• ?? **Muted Users** ? `{len(global_mute_users[chat_id])}`")

                if chat_id in blacklist and blacklist[chat_id]:
                    lines.append(f"• ?? **Blacklisted** ? `{len(blacklist[chat_id])}`")

                banner_count = len(list_banners())
                if banner_count:
                    lines.append(f"• ?? **Saved Banners** ? `{banner_count}`")

                if not lines:
                    await safe_respond(event, "**?? No active protocols detected in this chat.**\nAll systems are currently idle.")
                    return

                header = "**?----------------------------------------------?**\n"
                header += "**     ?? ???? ???????? ?????? ??**\n"
                header += "**?----------------------------------------------?**\n\n"
                body = "\n".join(lines)
                footer = "\n\n**----------------------------------------------**\n"
                footer += f"**?? ???? :** `{chat_id}`\n"
                footer += "**? ??????? ?? ?????? ?**"
                await safe_respond(event, header + body + footer)

            # ===== BANNER SYSTEM =====
            elif cmd_name == 'banner':
                if not cmd_args:
                    await safe_respond(event, "? **Usage:** `-banner <id>` — reply to a photo or video.")
                    return
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a photo or video to save it as banner.**")
                    return
                reply = await event.get_reply_message()
                if not reply:
                    await safe_respond(event, "? **No media detected in reply.**")
                    return
                is_photo = bool(reply.photo)
                is_video = bool(reply.video)
                is_doc_media = bool(reply.document and reply.document.mime_type and reply.document.mime_type.startswith(('image/', 'video/')))
                if not (is_photo or is_video or is_doc_media):
                    await safe_respond(event, "? **Only photos or videos can be saved as banner.**")
                    return
                banner_id = cmd_args.strip().split()[0]
                existing = get_banner_by_id(banner_id)
                if existing:
                    try: os.remove(existing)
                    except: pass
                ext = 'jpg'
                if is_video:
                    ext = 'mp4'
                elif reply.document and reply.document.mime_type:
                    mime = reply.document.mime_type
                    if mime.startswith('video/'):
                        ext = 'mp4'
                    elif mime.startswith('image/'):
                        ext = mime.split('/')[-1] or 'jpg'
                path = os.path.join(BANNER_FOLDER, f'banner_{banner_id}.{ext}')
                try:
                    downloaded = await client.download_media(reply, file=path)
                    if not downloaded:
                        await safe_respond(event, "? **Download failed.**")
                        return
                    await safe_respond(event, f"?? **Banner `{banner_id}` saved successfully.**\nTotal banners: `{len(list_banners())}`")
                except Exception as e:
                    await safe_respond(event, f"? **Banner save failed:** `{str(e)[:80]}`")

            elif cmd_name == 'bannerlist':
                banners = list_banners()
                if not banners:
                    await safe_respond(event, "?? **No banners saved yet.**")
                    return
                text = "?? **Saved Banner Registry**\n\n"
                for b in banners:
                    text += f"• `{b}`\n"
                text += f"\n**Total:** `{len(banners)}`"
                await safe_respond(event, text)

            elif cmd_name == 'clearbanner':
                banners = list_banners()
                if not banners:
                    await safe_respond(event, "?? **No banners to clear.**")
                    return
                count = 0
                for f in banners:
                    try:
                        os.remove(os.path.join(BANNER_FOLDER, f))
                        count += 1
                    except:
                        pass
                await safe_respond(event, f"??? **Banner arsenal purged.** `{count}` banner(s) deleted.")

            # ===== PULSE SYSTEM =====
            elif cmd_name == 'pulse':
                if not cmd_args or not event.is_reply:
                    await safe_respond(event, "? **Usage:** `-pulse <emoji>` (reply to a user to engage).")
                    return
                reply_msg = await event.get_reply_message()
                if not reply_msg or not reply_msg.sender_id:
                    await safe_respond(event, "? **No target detected.** Reply to a user to proceed.")
                    return
                emoji = cmd_args.strip().split()[0]
                set_pulse(chat_id, reply_msg.sender_id, emoji)

                if reply_msg.sender_id == host_account_id:
                    await safe_respond(event, f"?? **Self-pulse armed.** All your messages will now be greeted with `{emoji}`.\nSend any message to test.")
                else:
                    await safe_respond(event, f"?? **Pulse injected successfully.**\nEvery incoming message from this user will now be greeted with `{emoji}`.")

            elif cmd_name == 'stoppulse':
                if not event.is_reply:
                    await safe_respond(event, "? **Action requires a reply to a user.**")
                    return
                reply_msg = await event.get_reply_message()
                if not reply_msg or not reply_msg.sender_id:
                    await safe_respond(event, "? **No target detected.**")
                    return
                result = remove_pulse(chat_id, reply_msg.sender_id)
                if result:
                    await safe_respond(event, "?? **Pulse detached.** Target has been released from reaction protocol.")
                else:
                    await safe_respond(event, "?? **No active pulse exists for this user.**")

            elif cmd_name == 'pulselist':
                pulses = list_pulses(chat_id)
                if not pulses:
                    await safe_respond(event, "?? **No active pulses registered in this chat.**")
                    return
                text = "?? **Active Pulse Registry**\n\n"
                for (c, uid), emoji in pulses.items():
                    try:
                        u = await client.get_entity(uid)
                        name = u.first_name or "Unknown"
                    except:
                        name = "Unknown"
                    text += f"• **{name}** `({uid})` ? `{emoji}`\n"
                await safe_respond(event, text)

            # ===== HUNT SYSTEM =====
            elif cmd_name == 'hunt':
                target = await get_user_from_reply(event)
                if not target:
                    await safe_respond(event, "? **No target detected.** Reply to a user with `-hunt` to commence pursuit.")
                    return
                if not load_hunt_lines():
                    await safe_respond(event, f"? **Tactical arsenal empty** — `{HUNT_FILE}` not found or blank.")
                    return
                hkey = (chat_id, target)
                if hkey not in hunt_data:
                    hunt_data[hkey] = {'delay': 1, 'active': True}
                else:
                    hunt_data[hkey]['active'] = True
                try:
                    u = await client.get_entity(target)
                    name = u.first_name or "Unknown"
                except:
                    name = "Unknown"
                old_task = hunt_tasks.get(chat_id)
                if old_task and not old_task.done():
                    old_task.cancel()
                delay = hunt_data[hkey].get('delay', 1)
                task = asyncio.create_task(hunt_loop(chat_id, target, delay))
                hunt_tasks[chat_id] = task
                
                await safe_respond(event, f"?? **Hunt protocol initiated on {name}.**\nResponse interval: `{delay}s` — Use `-stophunt` to terminate.")

            elif cmd_name == 'stophunt':
                if hunt_tasks.get(chat_id):
                    task = hunt_tasks.pop(chat_id, None)
                    if task and not task.done():
                        task.cancel()
                to_del = [k for k in hunt_data if k[0] == chat_id]
                for k in to_del:
                    hunt_data[k]['active'] = False
                await safe_respond(event, "?? **Hunt protocol terminated.** All active pursuits have been halted.")

            elif cmd_name == 'huntdelay':
                target = await get_user_from_reply(event)
                if not target:
                    await safe_respond(event, "? **Reply to a target to calibrate the interval.**")
                    return
                try:
                    d = float(cmd_args.strip())
                    if d < 0.5: d = 0.5
                    hkey = (chat_id, target)
                    if hkey not in hunt_data:
                        hunt_data[hkey] = {'delay': d, 'active': False}
                    else:
                        hunt_data[hkey]['delay'] = d
                    if hunt_tasks.get(chat_id) and not hunt_tasks[chat_id].done():
                        old = hunt_tasks.pop(chat_id)
                        old.cancel()
                        new_task = asyncio.create_task(hunt_loop(chat_id, target, d))
                        hunt_tasks[chat_id] = new_task
                    await safe_respond(event, f"?? **Hunt interval synchronized to** `{d}s`. Protocol adjusted successfully.")
                except:
                    await safe_respond(event, "? **Malformed value.** Example: `-huntdelay 1.5`")

            elif cmd_name == 'huntlist':
                chat_hunts = [(uid, d) for (c, uid), d in hunt_data.items() if c == chat_id and d.get('active')]
                if not chat_hunts:
                    await safe_respond(event, "?? **No active hunt protocols in this chat.**")
                    return
                text = "?? **Active Hunt Protocols**\n\n"
                for uid, d in chat_hunts:
                    try:
                        u = await client.get_entity(uid)
                        name = u.first_name or "Unknown"
                    except:
                        name = "Unknown"
                    text += f"• **{name}** `({uid})` ? `{d.get('delay', 1)}s`\n"
                await safe_respond(event, text)

            # ===== VORTEX =====
            elif cmd_name == 'vortex' and cmd_args and event.is_reply:
                if vortex_active.get(chat_id):
                    await safe_respond(event, "?? **Vortex engine is already operational.** Use `-stopvortex` to halt the current session.")
                    return
                reply_msg = await event.get_reply_message()
                vortex_active[chat_id] = True
                target_text = cmd_args
                reply_id = reply_msg.id
                
                await safe_respond(event, "?? **Vortex engine ignited.** Non-stop rotational assault now in progress...")

                async def vortex_loop():
                    print(f"?? Vortex ignited in {chat_id}")
                    while vortex_active.get(chat_id):
                        try:
                            await client.send_message(chat_id, target_text, reply_to=reply_id)
                        except errors.FloodWaitError as f:
                            await asyncio.sleep(f.seconds)
                        except Exception as e:
                            print(f"? Vortex error: {e}")
                            break
                        await asyncio.sleep(current_speed)
                    print(f"?? Vortex halted")

                asyncio.create_task(vortex_loop())

            elif cmd_name == 'stopvortex':
                vortex_active[chat_id] = False
                await safe_respond(event, "?? **Vortex engine frozen.** Rotational assault suspended.")

            # ===== BURST =====
            elif cmd_name == 'burst' and cmd_args:
                if spam_active.get(chat_id):
                    await safe_respond(event, "?? **Barrage is already underway.** Use `-stopburst` to halt.")
                    return
                spam_active[chat_id] = True
                target_text = cmd_args
                
                await safe_respond(event, "?? **Burst mode activated.** Relentless barrage now streaming...")

                async def burst_loop():
                    print(f"?? Burst ignited in {chat_id}")
                    while spam_active.get(chat_id):
                        try:
                            await client.send_message(chat_id, target_text)
                        except errors.FloodWaitError as f:
                            await asyncio.sleep(f.seconds)
                        except Exception as e:
                            print(f"? Burst error: {e}")
                            break
                        await asyncio.sleep(current_speed)
                    print(f"?? Burst halted")

                asyncio.create_task(burst_loop())

            elif cmd_name == 'stopburst':
                spam_active[chat_id] = False
                await safe_respond(event, "?? **Barrage terminated.** All offensive streams have ceased.")

            # ===== TARGET =====
            elif cmd_name == 'target':
                target = await resolve_target_user(cmd_args, event)
                if not target:
                    await safe_respond(event, "? **Target unresolved.** Reply to a user to designate as target.")
                    return
                k = (chat_id, target)
                if k not in target_data:
                    target_data[k] = {'delay': 0, 'active': True}
                else:
                    target_data[k]['active'] = True
                try:
                    u = await client.get_entity(target)
                    name = u.first_name or "Unknown"
                except:
                    name = "Unknown"
                await safe_respond(event, f"?? **Target acquired:** {name} — Protocol now active.")

            elif cmd_name == 'stoptarget':
                target = await resolve_target_user(cmd_args, event)
                if not target:
                    await safe_respond(event, "? **Reply to a user to release them as target.**")
                    return
                k = (chat_id, target)
                if k in target_data:
                    del target_data[k]
                    await safe_respond(event, "?? **Target released.** Protocol deactivated for this user.")
                else:
                    await safe_respond(event, "?? **No active target registered for this user.**")

            elif cmd_name == 'targetdelay':
                target = None
                delay_val = None
                if cmd_args:
                    parts = cmd_args.split()
                    for p in parts:
                        if p.isdigit() or (p.startswith('-') and p[1:].isdigit()):
                            delay_val = int(p)
                            break
                    remaining = [p for p in parts if not (p.isdigit() or (p.startswith('-') and p[1:].isdigit()))]
                    remaining_args = " ".join(remaining).strip()
                    if remaining_args:
                        target = await parse_user_from_arg(remaining_args.split()[0], event)
                    else:
                        target = await get_user_from_reply(event)
                else:
                    target = await get_user_from_reply(event)
                if not target:
                    await safe_respond(event, "? **Target unresolved.** Reply to a user to proceed.")
                    return
                if delay_val is None:
                    await safe_respond(event, "? **Delay value missing.** Example: `-targetdelay 5`")
                    return
                if delay_val < 0: delay_val = 0
                k = (chat_id, target)
                if k not in target_data:
                    target_data[k] = {'delay': delay_val, 'active': True}
                else:
                    target_data[k]['delay'] = delay_val
                await safe_respond(event, f"?? **Target response delay synchronized to** `{delay_val}s`.")

            elif cmd_name == 'targetlist':
                chat_targets = [(uid, d) for (c, uid), d in target_data.items() if c == chat_id and d.get('active')]
                if not chat_targets:
                    await safe_respond(event, "?? **No active targets registered in this chat.**")
                    return
                text = "?? **Active Target Registry**\n\n"
                for uid, d in chat_targets:
                    try:
                        u = await client.get_entity(uid)
                        name = u.first_name or "Unknown"
                    except:
                        name = "Unknown"
                    text += f"• **{name}** `({uid})` ? `{d.get('delay', 0)}s`\n"
                await safe_respond(event, text)

            # ===== LOCK =====
            elif cmd_name == 'lockchat':
                if chat_id in lock_data:
                    await safe_respond(event, "?? **This chat is already fortified with a lock.**")
                else:
                    lock_data[chat_id] = sender_id
                    await safe_respond(event, "?? **Security lockdown engaged.** Only the host may transmit messages in this chat.")

            elif cmd_name == 'unlockchat':
                if chat_id not in lock_data:
                    await safe_respond(event, "?? **This chat is not currently locked.**")
                else:
                    lock_data.pop(chat_id, None)
                    await safe_respond(event, "?? **Security release acknowledged.** All users may resume transmission.")

            # ===== MUTE =====
            elif cmd_name == 'globalmute':
                user_ids = []
                if cmd_args:
                    for part in cmd_args.split():
                        uid = await parse_user_from_arg(part, event)
                        if uid: user_ids.append(uid)
                else:
                    r = await get_user_from_reply(event)
                    if r: user_ids.append(r)
                if not user_ids:
                    await safe_respond(event, "? **No valid users detected.**")
                    return
                if chat_id not in global_mute_users:
                    global_mute_users[chat_id] = set()
                added = 0
                for uid in user_ids:
                    if uid not in global_mute_users[chat_id]:
                        global_mute_users[chat_id].add(uid)
                        added += 1
                await safe_respond(event, f"?? **Mute deployed.** {added} user(s) silenced within this group.")

            elif cmd_name == 'globalunmute':
                user_ids = []
                if cmd_args:
                    for part in cmd_args.split():
                        uid = await parse_user_from_arg(part, event)
                        if uid: user_ids.append(uid)
                else:
                    r = await get_user_from_reply(event)
                    if r: user_ids.append(r)
                if not user_ids:
                    await safe_respond(event, "? **No valid users detected.**")
                    return
                if chat_id not in global_mute_users:
                    await safe_respond(event, "? **No muted users exist in this chat.**")
                    return
                removed = 0
                for uid in user_ids:
                    if uid in global_mute_users[chat_id]:
                        global_mute_users[chat_id].remove(uid)
                        removed += 1
                if not global_mute_users[chat_id]:
                    del global_mute_users[chat_id]
                await safe_respond(event, f"?? **Mute revoked.** {removed} user(s) permitted to transmit once again.")

            elif cmd_name == 'mutelist':
                if chat_id not in global_mute_users or not global_mute_users[chat_id]:
                    await safe_respond(event, "?? **No muted users registered in this chat.**")
                    return
                text = "?? **Active Mute Registry**\n\n"
                for uid in global_mute_users[chat_id]:
                    try:
                        u = await client.get_entity(uid)
                        text += f"• **{u.first_name or 'Unknown'}** `({uid})`\n"
                    except:
                        text += f"• **Unknown** `({uid})`\n"
                await safe_respond(event, text)

            # ===== BLACKLIST =====
            elif cmd_name == 'blacklist':
                user_ids = []
                if cmd_args:
                    for part in cmd_args.split():
                        uid = await parse_user_from_arg(part, event)
                        if uid: user_ids.append(uid)
                else:
                    r = await get_user_from_reply(event)
                    if r: user_ids.append(r)
                if not user_ids:
                    await safe_respond(event, "? **No valid users detected.**")
                    return
                if chat_id not in blacklist:
                    blacklist[chat_id] = set()
                added = 0
                for uid in user_ids:
                    if uid not in blacklist[chat_id]:
                        blacklist[chat_id].add(uid)
                        added += 1
                        await kick_user(chat_id, uid)
                await safe_respond(event, f"?? **Blacklist enforced.** {added} user(s) designated for exclusion.")

            elif cmd_name == 'rmblacklist':
                user_ids = []
                if cmd_args:
                    for part in cmd_args.split():
                        uid = await parse_user_from_arg(part, event)
                        if uid: user_ids.append(uid)
                else:
                    r = await get_user_from_reply(event)
                    if r: user_ids.append(r)
                if not user_ids:
                    await safe_respond(event, "? **No valid users detected.**")
                    return
                if chat_id not in blacklist:
                    await safe_respond(event, "? **No blacklisted users in this chat.**")
                    return
                removed = 0
                for uid in user_ids:
                    if uid in blacklist[chat_id]:
                        blacklist[chat_id].remove(uid)
                        removed += 1
                if not blacklist[chat_id]:
                    del blacklist[chat_id]
                await safe_respond(event, f"? **Blacklist revoked.** {removed} user(s) restored to permitted status.")

            elif cmd_name == 'blackliststatus':
                if chat_id not in blacklist or not blacklist[chat_id]:
                    await safe_respond(event, "?? **No blacklisted users in this chat.**")
                    return
                text = "?? **Blacklist Registry**\n\n"
                for uid in blacklist[chat_id]:
                    try:
                        u = await client.get_entity(uid)
                        text += f"• **{u.first_name or 'Unknown'}** `({uid})`\n"
                    except:
                        text += f"• **Unknown** `({uid})`\n"
                await safe_respond(event, text)

            # ===== IMAGE REPLY =====
            elif cmd_name == 'setimageuser':
                target = await get_user_from_reply(event)
                if not target:
                    await safe_respond(event, "? **Reply to a user to proceed.**")
                    return
                image_target[chat_id] = target
                await safe_respond(event, "?? **Image target designated.** Arsenal now bound to this user.")

            elif cmd_name == 'reloadimage':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a photo to proceed.**")
                    return
                reply = await event.get_reply_message()
                if not (reply.photo or (reply.document and reply.document.mime_type and reply.document.mime_type.startswith('image/'))):
                    await safe_respond(event, "? **Target media is not a photo.**")
                    return
                target = image_target.get(chat_id)
                if not target:
                    await safe_respond(event, "? **No image target designated.** Use `-setimageuser` first.")
                    return
                parts = cmd_args.split(maxsplit=1)
                if not parts:
                    await safe_respond(event, "? **Usage:** `-reloadimage <id> [caption]`")
                    return
                try:
                    img_id = int(parts[0])
                except ValueError:
                    await safe_respond(event, "? **Image identifier must be numeric.**")
                    return
                caption = parts[1] if len(parts) > 1 else ""
                path = os.path.join(IMAGE_FOLDER, f"img_{chat_id}_{target}_{img_id}.jpg")
                try:
                    file_path = await client.download_media(reply, file=path)
                    if not file_path:
                        await safe_respond(event, "? **Download operation failed.**")
                        return
                except Exception as e:
                    await safe_respond(event, f"? **Execution error:** `{str(e)[:80]}`")
                    return
                k = (chat_id, target)
                if k not in user_images: user_images[k] = {}
                user_images[k][str(img_id)] = {'path': file_path, 'caption': caption}
                save_image_data()
                await safe_respond(event, f"?? **Image archived with identifier** `{img_id}` — Payload ready for deployment.")

            elif cmd_name == 'imagereply':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a user to proceed.**")
                    return
                reply = await event.get_reply_message()
                target = reply.sender_id
                k = (chat_id, target)
                if k not in user_images or not user_images[k]:
                    await safe_respond(event, "? **No images archived for this user.**")
                    return
                image_reply_active[k] = True
                await safe_respond(event, "??? **Image protocol engaged.** Random archival imagery will be dispatched on incoming messages.")

            elif cmd_name == 'imagestop':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a user to proceed.**")
                    return
                reply = await event.get_reply_message()
                target = reply.sender_id
                k = (chat_id, target)
                if k in image_reply_active:
                    del image_reply_active[k]
                    await safe_respond(event, "?? **Image protocol disengaged.** User released from imagery dispatch.")
                else:
                    await safe_respond(event, "?? **No active image protocol for this user.**")

            elif cmd_name == 'imagedelay':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a user to proceed.**")
                    return
                reply = await event.get_reply_message()
                target = reply.sender_id
                try:
                    delay = int(cmd_args)
                    k = (chat_id, target)
                    image_delay[k] = delay
                    save_image_data()
                    await safe_respond(event, f"?? **Image dispatch delay synchronized to** `{delay}ms`.")
                except:
                    await safe_respond(event, "? **Malformed value detected.**")

            elif cmd_name == 'photomode':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a user to proceed.**")
                    return
                reply = await event.get_reply_message()
                target = reply.sender_id
                k = (chat_id, target)
                photo_mode[k] = True
                save_image_data()
                await safe_respond(event, "?? **Photo mode engaged.** Imagery will dispatch only upon incoming photos or videos.")

            elif cmd_name == 'offphotomode':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a user to proceed.**")
                    return
                reply = await event.get_reply_message()
                target = reply.sender_id
                k = (chat_id, target)
                if k in photo_mode:
                    del photo_mode[k]
                    save_image_data()
                    await safe_respond(event, "?? **Photo mode disengaged.** Imagery will now dispatch on all incoming messages.")
                else:
                    await safe_respond(event, "?? **Photo mode is already inactive for this user.**")

            elif cmd_name == 'imagelist':
                if cmd_args:
                    user_id = await parse_user_from_arg(cmd_args, event)
                    if not user_id:
                        await safe_respond(event, "? **Invalid user identifier.**")
                        return
                    target_user = user_id
                else:
                    target_user = image_target.get(chat_id)
                    if not target_user:
                        await safe_respond(event, "? **No target designated.**")
                        return
                k = (chat_id, target_user)
                if k not in user_images or not user_images[k]:
                    await safe_respond(event, "?? **No images archived for this user.**")
                    return
                text = f"??? **Image Archive for** `{target_user}`\n\n"
                for iid, info in user_images[k].items():
                    text += f"• ID `{iid}` ? `{info['caption']}`\n"
                await safe_respond(event, text)

            elif cmd_name == 'imageclear':
                if cmd_args:
                    user_id = await parse_user_from_arg(cmd_args, event)
                    if not user_id:
                        await safe_respond(event, "? **Invalid user identifier.**")
                        return
                    target_user = user_id
                else:
                    target_user = image_target.get(chat_id)
                    if not target_user:
                        await safe_respond(event, "? **No target designated.**")
                        return
                k = (chat_id, target_user)
                if k not in user_images or not user_images[k]:
                    await safe_respond(event, "?? **No images to purge.**")
                    return
                for info in user_images[k].values():
                    try: os.remove(info['path'])
                    except: pass
                del user_images[k]
                image_delay.pop(k, None)
                photo_mode.pop(k, None)
                save_image_data()
                await safe_respond(event, "??? **Image archive purged.** All archival imagery eliminated.")

            # ===== VOICE NOTE =====
            elif cmd_name == 'vn' and cmd_args:
                await safe_respond(event, "??? **Synthesizing voice transmission...**")
                try:
                    audio_path = await text_to_voice(cmd_args)
                    await client.send_file(chat_id, audio_path, voice_note=True, caption=cmd_args,
                                           reply_to=event.reply_to_msg_id if event.is_reply else None)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                except Exception as e:
                    await safe_respond(event, f"? **Synthesis failed:** `{str(e)[:80]}`")

            # ===== SNIPE =====
            elif cmd_name == 'snipe':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a target message to proceed.**")
                    return
                if not cmd_args:
                    await safe_respond(event, "? **Text payload missing.** Usage: `-snipe <text>`")
                    return
                rep = await event.get_reply_message()
                snipe_data[(chat_id, rep.sender_id)] = cmd_args
                await safe_respond(event, "?? **Counter-strike armed.** Target will be intercepted on their next transmission.")

            elif cmd_name == 'stopsnipe':
                if not event.is_reply:
                    await safe_respond(event, "? **Reply to a user to proceed.**")
                    return
                rep = await event.get_reply_message()
                snipe_data.pop((chat_id, rep.sender_id), None)
                await safe_respond(event, "?? **Counter-strike disarmed.** Target released from sniper protocol.")

            # ===== CLONE =====
            elif cmd_name == 'clone' and event.is_reply:
                await event.edit("?? **Identity replicator engaged — establishing connection...**")
                reply_msg = await event.get_reply_message()
                try:
                    target_user = await client.get_entity(reply_msg.sender_id)
                except Exception as e:
                    await event.edit(f"? **Connection violation:** `{str(e)[:80]}`")
                    return
                if not isinstance(target_user, types.User):
                    await event.edit("? **Target must be a user entity.**")
                    return
                me = await client.get_me()
                full_me = await client(functions.users.GetFullUserRequest(id=me.id))
                original_profile["first_name"] = me.first_name or ""
                original_profile["last_name"] = me.last_name or ""
                original_profile["about"] = full_me.full_user.about or ""
                target_full = await client(functions.users.GetFullUserRequest(id=target_user.id))
                target_bio = target_full.full_user.about or ""
                target_first = target_user.first_name or ""
                target_last = target_user.last_name or ""
                pfp_path = await client.download_profile_photo(target_user.id, file="clone_pfp.jpg")
                if pfp_path:
                    try:
                        await client(functions.photos.UploadProfilePhotoRequest(
                            fallback=False, file=await client.upload_file(pfp_path)))
                        if os.path.exists(pfp_path): os.remove(pfp_path)
                    except: pass
                try:
                    await client(functions.account.UpdateProfileRequest(
                        first_name=target_first, last_name=target_last, about=target_bio))
                    await event.edit("?? **Ghost mode active.** Identity successfully replicated — name, bio and portrait mirrored.")
                except Exception as e:
                    await event.edit(f"? **Profile update failed:** `{str(e)[:80]}`")

            elif cmd_name == 'restore':
                await event.edit("?? **Restoring original identity configuration...**")
                try:
                    await client(functions.account.UpdateProfileRequest(
                        first_name=original_profile["first_name"],
                        last_name=original_profile["last_name"],
                        about=original_profile["about"]))
                    await event.edit("? **Identity restored.** Your original profile has been reactivated.")
                except Exception as e:
                    await event.edit(f"? **Restoration failed:** `{str(e)[:80]}`")

            # ===== SUDO =====
            elif cmd_name == 'addsudo' and cmd_args:
                if not is_super_owner():
                    await safe_respond(event, "? **Access denied — super owners only.**")
                    return
                try:
                    username = cmd_args.strip().replace('@', '')
                    u = await client.get_entity(f"@{username}")
                    sudo_users.add(u.id)
                    await safe_respond(event, f"?? **Sudo authority granted to {u.first_name}.** Elevated privileges now in effect.")
                except Exception as e:
                    await safe_respond(event, f"? **Operation failed:** `{str(e)[:50]}`")

            elif cmd_name == 'removesudo' and cmd_args:
                if not is_super_owner():
                    await safe_respond(event, "? **Access denied — super owners only.**")
                    return
                try:
                    username = cmd_args.strip().replace('@', '')
                    u = await client.get_entity(f"@{username}")
                    if u.id in sudo_users:
                        sudo_users.remove(u.id)
                        await safe_respond(event, f"?? **Sudo authority revoked from {u.first_name}.**")
                    else:
                        await safe_respond(event, f"?? **User is not registered within the sudo registry.**")
                except Exception as e:
                    await safe_respond(event, f"? **Operation failed:** `{str(e)[:50]}`")

            elif cmd_name == 'sudolist':
                if not is_super_owner():
                    await safe_respond(event, "? **Access denied — super owners only.**")
                    return
                if not sudo_users:
                    await safe_respond(event, "?? **No sudo users registered.**")
                    return
                text = "?? **Sudo Registry**\n\n"
                for uid in sudo_users:
                    try:
                        u = await client.get_entity(uid)
                        text += f"• **{u.first_name}** `({uid})`\n"
                    except:
                        text += f"• **Unknown** `({uid})`\n"
                await safe_respond(event, text)

            elif cmd_name == 'superinvite':
                if not is_super_owner():
                    await safe_respond(event, "? **Access denied — super owners only.**")
                    return
                link = cmd_args.strip()
                if not link:
                    await safe_respond(event, "? **Invite link missing.** Usage: `-superinvite <link>`")
                    return
                await safe_respond(event, "?? **Initiating group infiltration...**")
                try:
                    await join_client_via_link(link)
                    await safe_respond(event, "? **Infiltration successful.** Target group joined.")
                except errors.FloodWaitError as fw:
                    await safe_respond(event, f"?? **Rate limit encountered** — retry after {fw.seconds}s.")
                except Exception as e:
                    await safe_respond(event, f"? **Infiltration failed:** `{str(e)[:80]}`")

            # ===== KILL =====
            elif cmd_name == 'kill':
                spam_active[chat_id] = False
                vortex_active[chat_id] = False
                t = hunt_tasks.pop(chat_id, None)
                if t and not t.done(): t.cancel()
                for k in [k for k in hunt_data if k[0] == chat_id]:
                    del hunt_data[k]
                hunt_index.pop(chat_id, None)
                snipe_data = {k: v for k, v in snipe_data.items() if k[0] != chat_id}
                clear_chat_pulses(chat_id)
                global_mute_users.pop(chat_id, None)
                lock_data.pop(chat_id, None)
                for k in [k for k in image_reply_active if k[0] == chat_id]:
                    del image_reply_active[k]
                for k in [k for k in image_delay if k[0] == chat_id]:
                    del image_delay[k]
                for k in [k for k in photo_mode if k[0] == chat_id]:
                    del photo_mode[k]
                for k in [k for k in user_images if k[0] == chat_id]:
                    for info in user_images[k].values():
                        try: os.remove(info['path'])
                        except: pass
                    del user_images[k]
                for k in [k for k in target_data if k[0] == chat_id]:
                    del target_data[k]
                target_loop_index.pop(chat_id, None)
                save_image_data()
                image_target.pop(chat_id, None)
                blacklist.pop(chat_id, None)
                await safe_respond(event, "?? **System purge executed.** All active protocols within this chat have been wiped clean.")

        except Exception as e:
            print(f"? Command error [{cmd_name}]: {type(e).__name__}: {e}")
        return

    # ==========================================
    # ============ USER ACTIONS ================
    # ==========================================

    await apply_reaction(client, chat_id, event.id, sender_id)

    if sender_id == host_account_id:
        return

    if chat_id in lock_data and sender_id != lock_data[chat_id]:
        try: await event.delete()
        except: pass
        return

    if chat_id in global_mute_users and sender_id in global_mute_users[chat_id]:
        try: await event.delete()
        except: pass
        return

    if chat_id in blacklist and sender_id in blacklist[chat_id]:
        try: await event.delete()
        except: pass
        await kick_user(chat_id, sender_id)
        return

    # Snipe
    if key in snipe_data:
        try:
            await client.send_message(chat_id, snipe_data[key], reply_to=event.id)
            print(f"?? Snipe dispatched")
        except Exception as e:
            print(f"? Snipe error: {e}")

    # Target (direct)
    if key in target_data and target_data[key].get('active'):
        gaali_lines = load_gaali_lines()
        if gaali_lines:
            delay = target_data[key].get('delay', 0)
            if delay > 0:
                await asyncio.sleep(delay)
            line = get_next_gaali(chat_id)
            if line:
                try:
                    u = await client.get_entity(sender_id)
                    mention = get_mention_html(u)
                except:
                    mention = f"User {sender_id}"
                try:
                    await client.send_message(chat_id, f"{mention} {line}", parse_mode='html', reply_to=event.id)
                except Exception as e:
                    print(f"Target error: {e}")
        return

    # Target (tag)
    if event.message and event.message.entities:
        mentioned_ids = []
        for ent in event.message.entities:
            if isinstance(ent, types.MessageEntityMention):
                uname = event.raw_text[ent.offset:ent.offset + ent.length]
                try:
                    u = await client.get_entity(uname)
                    mentioned_ids.append(u.id)
                except: pass
            elif isinstance(ent, types.MessageEntityMentionName):
                mentioned_ids.append(ent.user_id)
        for uid in mentioned_ids:
            mkey = (chat_id, uid)
            if mkey in target_data and target_data[mkey].get('active'):
                delay = target_data[mkey].get('delay', 0)
                if delay > 0:
                    await asyncio.sleep(delay)
                line = get_next_gaali(chat_id)
                if line:
                    try:
                        u = await client.get_entity(uid)
                        mention = get_mention_html(u)
                    except:
                        mention = f"User {uid}"
                    try:
                        await client.send_message(chat_id, f"{mention} {line}", parse_mode='html', reply_to=event.id)
                    except Exception as e:
                        print(f"Tag target error: {e}")
                break

    # Image reply
    if key in image_reply_active and key in user_images and user_images[key]:
        if photo_mode.get(key):
            if not is_media(event):
                return
        delay = image_delay.get(key, 0)
        if delay > 0:
            await asyncio.sleep(delay / 1000)
        images = user_images[key]
        img_id = random.choice(list(images.keys()))
        info = images[img_id]
        try:
            await client.send_file(chat_id, info['path'], caption=info.get('caption', ''), reply_to=event.id)
        except Exception as e:
            print(f"Image reply error: {e}")
        return

# ========== CHAT ACTION ==========
@client.on(events.ChatAction)
async def chat_action_handler(event):
    global global_mute_users, lock_data, blacklist
    chat_id = event.chat_id
    user_id = None
    if event.user_id:
        user_id = event.user_id
    elif hasattr(event, 'user') and event.user:
        user_id = event.user.id
    if not user_id:
        return
    if chat_id in lock_data and user_id != lock_data[chat_id]:
        try: await event.delete()
        except: pass
        if event.user_joined or event.user_added:
            try: await client.kick_participant(chat_id, user_id)
            except: pass
        return
    if chat_id in global_mute_users and user_id in global_mute_users[chat_id]:
        try: await event.delete()
        except: pass
        if event.user_joined or event.user_added:
            try: await client.kick_participant(chat_id, user_id)
            except: pass
        return
    if chat_id in blacklist and user_id in blacklist[chat_id]:
        try: await event.delete()
        except: pass
        if event.user_joined or event.user_added:
            await kick_user(chat_id, user_id)

# ========== MAIN ==========
async def main():
    global host_account_id

    # Flask web server thread background me start karein
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    load_image_data()

    await client.start()
    me = await client.get_me()
    host_account_id = me.id

    print(f"?? Super Owners: {SUPER_OWNERS}")
    print(f"??? Host: {me.first_name} (ID: {host_account_id})")

    if not os.path.exists(GAALI_FILE):
        print(f"?? gaali.txt NOT FOUND!")
    else:
        lines = load_gaali_lines()
        if lines:
            print(f"? gaali.txt loaded ({len(lines)} lines).")

    if not os.path.exists(HUNT_FILE):
        print(f"?? hunt.txt NOT FOUND!")
    else:
        hlines = load_hunt_lines()
        if hlines:
            print(f"? hunt.txt loaded ({len(hlines)} lines).")

    banner_count = len(list_banners())
    print(f"?? Banners loaded: {banner_count}")

    print("?? AIMGOD FINAL BOT LIVE!")
    print("?? Pulse System Active!")
    print("?? Hunt System Active!")
    print("?? Banner System Active!")
    print("?? Web server active for Render deployment!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
