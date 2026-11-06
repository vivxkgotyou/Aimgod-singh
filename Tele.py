import asyncio
import random
import time
import logging
import os
import sys
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import (
    PeerIdInvalidError, ChatWriteForbiddenError, UserNotParticipantError,
    ChatAdminRequiredError, ChannelPrivateError, FloodWaitError,
    UserAlreadyParticipantError, UserPrivacyRestrictedError
)
from telethon.tl.functions.channels import EditAdminRequest, JoinChannelRequest, InviteToChannelRequest
from telethon.tl.types import ChatAdminRights

# ═══════════════ MULTI-ACCOUNT CONFIGURATION ═══════════════
SUPEROWNER_ID = 6133172474

ACCOUNTS = [
    {
        "api_id": 30357864,
        "api_hash": "8d8a1027816b1724b0b420480ea06a6f",
        "session": "vivek_session"
    },
    {
        "api_id": 38437169,
        "api_hash": "0e157a3fcf9ce4e2e7d37b8d4918b3ee",
        "session": "bot2_session"
    },
    {
        "api_id": 30416596,
        "api_hash": "f34ed882241e899cb53cbd906906627f",
        "session": "bot3_session"
    },
    {
        "api_id": 39013245,
        "api_hash": "963f01b44bc7aef297ce8d9f84b13739",
        "session": "bot4_session"
    },
    {
        "api_id": 37767333,
        "api_hash": "5815e35ce0bfe4e53fcbd0d374334803",
        "session": "bot5_session"
    }
]

BOT_VERSION = "𝘼𝙪𝙩𝙤𝙢𝙖𝙩𝙚𝙙 𝘽𝙮 𝙑𝙞v1 🇧🇼 [No-Call Suite]"
START_TIME = datetime.now()
P = r"\."  # prefix pattern

# ═══════════════ LOGGING ═══════════════
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("VIV1-MULTI-BOT")

clients = []

async def safe_delete(msg, delay=0.0):
    try:
        if delay > 0:
            await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass

# ═══════════════ THREAD-SAFE STORAGE & CONTROL ═══════════════
state_lock = asyncio.Lock()
swipe_tasks = {}       # {chat_id: {client_index: asyncio.Task}}
hunt_tasks = {}        # {chat_id: {client_index: asyncio.Task}}
auto_replies = {}      # {chat_id: {user_id: text}}
current_delay = 0.5    

DEFAULT_ADD2_BOTS = [
    "vivuxz_bot", "rapixtvivekbot", "Vivekjack_bot", "vivxk_bot",
    "vivxkbot", "vivekkfyn_bot", "vivxkspybot", "vivekkwrldbot",
    "kuromcbot", "vivxkmyn_bot", "vivxkmyn2_bot", "aieshasxy_bot", "visuchod3_bot"
]

DEFAULT_ADD3_BOTS = [
    "beingvivekbot", "beingvivek1bot", "beingvivek2bot", "beingvivek3bot",
    "beingvivek4bot", "Gopubhaibot", "existingDestroyerbot", "vivekheavnlyybot", "thvivekbot"
]

RAID_POOL = [
    "mene aj tk apni life me kuch galat kara ho to please teri ma randi hai",
    "teri chachi ke takle me lund marke behos krdunga rndi ko",
    "Tere maa ki gand me laat daalke tere choti behen maar dunga",
    "teri budhi dadi ke left boob me mukke ki barish krke seena pichka dunga budhiya ka uske pith pr boobs ajayenge",
    "teri betaal bhutni behn ki chut me bat se marunga rndi sochegi pitch gili thi batting kese hui",
    "okat h kya koi teri khanjri ke bachhe madarchod",
    "teri chhamiya behn ki chut me pipe dalke juice nikalenge glass ke andr",
    "teri budhi bua ke gale me halki si blade marke lund jane ka rasta banaun rndike bche teri behn ko pregnant krke fir uska placenta bhar khinchke lat maru uspe",
    "teri rndi didi ke sar me kulhadi marke 2 tukde krunga",
    "teri Mumma ko budhhu bnaunga bolunga aunty ji apko dadhi ari hai fir unki shaving krne lejaunga kursi me bithake gala kat dunga aunty ji ka fir unki dead body ko parnam karke chudai karunga gopgop haha unki atma santusht hojayegi vivek bhai se",
    "Teri maa ko uchal kr chodunga teri behen ko patak kr chodunga teri dadi ko duba duba kr chodunga teri nani ko bhaga bhaga kr chodunga budiya dm ghunte se hi mr jayegi teri mausi ki chut mein namak dalke chat chat kr chodunga",
    "teri sextoy behn ki chut pe thappad marunga fir use chodke pagal kr dunga fir chudakkado ke bajar me bech dunga kutiya ko fir buyer se wapis chura launga fir firse chodunga roj maje se",
    "teri pagal ma ke tango k baal danto se khinchunga rndi ki atma tadp jayegi drd se",
    "teri pagal rndi ma ko pagalkhane se adopt krlunga fir ghr lake uski bohot chudayi krunga fir wapis pagal khane me return krdunga pasand nhi ayi kehke",
    "teri ma rndi teri behn rndi teri tai rndi teri chachi rndi tu rndi ka bachha ma chude teri",
    "teri ma ke seene me pechkas ghopunga fir straw dalke dudh piyunga kanjar ke"
]

HELP = """** 𝘼𝙪𝙩𝙤𝙢𝙖𝙩𝙚𝙙 By 𝙑𝙞v1 🇧🇼 [MASTER SYNC SUITE] **
**🏗 𝙀𝙣𝙜𝙞𝙣𝙚: 𝙏𝙚𝙡𝙚𝙩𝙝𝙤𝙣**

**🔥 𝙎𝙒𝙄𝙋𝙀, 𝙃𝙐𝙉𝙏, 𝘼𝙐𝙏𝙊𝙍𝙀𝙋𝙇𝙔 & 𝘿𝙀𝙇𝘼𝙔**
`.swipe <msg>` — Spams reply thread using ALL accounts simultaneously
`.stopswipe` — Kills active broadcast across all bots
`.hunt` — Unleashes randomized multi-bot raid dispersion
`.stophunt` — Stops the hunt session
`.autoreply <text>` — (Reply) Deploys automated instant response protocol against target
`.stopautoreply` — Ceases automated response protocol
`.delay <seconds>` — Adjusts master delay/speed dynamically for all bots

**👥 𝘼𝘿𝘿 & 𝙅𝙊𝙄𝙉**
`.add2` — Summons your 13 main bots into the chat
`.add3` — Summons your 9 auxiliary bots into the chat
`.join <link>` — All 5 accounts pull up to the chat instantly

**🧰 𝙐𝙏𝙄𝙇𝙄𝙏𝙄𝙀🇸**
`.ping` — Checks the lag / ms
`.alive` — Displays system flex & current delay
`.stopall` — Shuts down all active tasks in this chat
"""

# ═══════════════ EVENT REGISTRATION FOR EACH CLIENT ═══════════════

def register_events(client_inst, client_idx):
    
    async def is_authorized(event):
        return event.sender_id == SUPEROWNER_ID or event.out

    @client_inst.on(events.NewMessage(pattern=rf"{P}help$"))
    async def help_cmd(event):
        if not await is_authorized(event): return
        await event.edit(HELP)

    @client_inst.on(events.NewMessage(pattern=rf"{P}ping$"))
    async def ping_cmd(event):
        if not await is_authorized(event): return
        start = time.perf_counter()
        await event.edit("⚡")
        delta = (time.perf_counter() - start) * 1000
        await event.edit(f"**🏓 𝙋𝙊𝙉𝙂!**\n`{delta:.2f}𝙢𝙨`")

    @client_inst.on(events.NewMessage(pattern=rf"{P}alive$"))
    async def alive_cmd(event):
        if not await is_authorized(event): return
        uptime = datetime.now() - START_TIME
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        await event.edit(
            f"**⚡ 𝘼𝙪𝙩𝙤𝙢𝙖𝙩𝙚𝙙 𝘽𝙮 𝙑𝙞v1 🇧🇼 ⚡**\n"
            f"**𝙑𝙚𝙧𝙨𝙞𝙤𝙣:** `{BOT_VERSION}`\n"
            f"**⏱️ 𝘾𝙪𝙧𝙧𝙚𝙣𝙩 𝘿𝙚𝙡𝙖𝙮:** `{current_delay}𝙨`\n"
            f"**👑 𝙎𝙪𝙥𝙚𝙧𝙤𝖜𝙣𝙚𝙧 𝙄𝘿:** `{SUPEROWNER_ID}`\n"
            f"**👥 𝘼𝙘𝙘𝙤𝙪𝙣𝙩𝙨:** `{len(clients)} 𝗔𝗰𝘁𝗶𝘃𝗲`\n"
            f"**⏳ 𝙐𝙥𝙩𝙞𝙢𝙚:** `{h}𝙝 {m}𝙢 {s}𝙨`"
        )

    @client_inst.on(events.NewMessage(pattern=rf"{P}delay\s+(.+)"))
    async def delay_cmd(event):
        global current_delay
        if not await is_authorized(event): return
        try:
            new_delay = float(event.pattern_match.group(1).strip())
            if new_delay < 0:
                return await event.edit("**❌ Delay cannot be negative!**")
            current_delay = new_delay
            await event.edit(f"**⚡ Master Speed Updated!** New delay for all bots: `{current_delay}s`")
        except ValueError:
            await event.edit("**❌ Invalid format! Example: `.delay 0.5`**")

    @client_inst.on(events.NewMessage(pattern=rf"{P}autoreply\s+(.+)"))
    async def autoreply_cmd(event):
        if not await is_authorized(event): return
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: 
            return await event.edit("**❌ Reply to a user to set autoreply!**")
        msg = event.pattern_match.group(1)
        async with state_lock:
            auto_replies.setdefault(event.chat_id, {})[reply.sender_id] = msg
        await event.edit(f"**✨ Autoreply set successfully for user ID:** `{reply.sender_id}`")

    @client_inst.on(events.NewMessage(pattern=rf"{P}stopautoreply$"))
    async def stopautoreply_cmd(event):
        if not await is_authorized(event): return
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: 
            return await event.edit("**❌ Reply to a user to stop their autoreply!**")
        async with state_lock:
            auto_replies.get(event.chat_id, {}).pop(reply.sender_id, None)
        await event.edit(f"**✨ Autoreply disabled for user ID:** `{reply.sender_id}`")

    @client_inst.on(events.NewMessage(incoming=True))
    async def incoming_listener(event):
        if not event.sender_id: return
        chat = event.chat_id
        uid = event.sender_id
        try:
            if chat in auto_replies and uid in auto_replies.get(chat, {}):
                await event.reply(auto_replies[chat][uid])
        except Exception:
            pass

    @client_inst.on(events.NewMessage(pattern=rf"{P}swipe\s+(.+)"))
    async def swipe_cmd(event):
        if not await is_authorized(event): return
        reply = await event.get_reply_message()
        if not reply:
            return await event.edit("**❌ Reply to a message to start swipe!**")
        msg = event.pattern_match.group(1)
        chat = event.chat_id
        reply_id = reply.id
        
        await event.edit(f"**🔥 Firing up swipe raid across all `{len(clients)}` accounts...**")

        async with state_lock:
            if chat not in swipe_tasks:
                swipe_tasks[chat] = {}

        for idx, c in enumerate(clients):
            if client_idx in swipe_tasks.get(chat, {}):
                try:
                    swipe_tasks[chat][client_idx].cancel()
                except:
                    pass

            async def client_loop(cli=c):
                try:
                    while True:
                        try:
                            await cli.send_message(chat, msg, reply_to=reply_id)
                        except FloodWaitError as e:
                            await asyncio.sleep(e.seconds)
                        except Exception:
                            pass
                        await asyncio.sleep(current_delay)
                except asyncio.CancelledError:
                    pass

            async with state_lock:
                swipe_tasks[chat][client_idx] = asyncio.create_task(client_loop())

    @client_inst.on(events.NewMessage(pattern=rf"{P}stopswipe$"))
    async def stopswipe_cmd(event):
        if not await is_authorized(event): return
        chat = event.chat_id
        async with state_lock:
            if chat in swipe_tasks:
                for task in swipe_tasks[chat].values():
                    task.cancel()
                swipe_tasks.pop(chat, None)
        await event.edit("**🛑 Swipe broadcast stopped across all bots!**")

    @client_inst.on(events.NewMessage(pattern=rf"{P}hunt$"))
    async def hunt_cmd(event):
        if not await is_authorized(event): return
        reply = await event.get_reply_message()
        if not reply:
            return await event.edit("**❌ Reply to a message to start hunt!**")
        chat = event.chat_id
        reply_id = reply.id
        
        await event.edit(f"**💥 Firing up hunt raid across all `{len(clients)}` accounts...**")

        async with state_lock:
            if chat not in hunt_tasks:
                hunt_tasks[chat] = {}

        for idx, c in enumerate(clients):
            if client_idx in hunt_tasks.get(chat, {}):
                try:
                    hunt_tasks[chat][client_idx].cancel()
                except:
                    pass

            async def client_hunt_loop(cli=c):
                try:
                    while True:
                        try:
                            msg = random.choice(RAID_POOL)
                            await cli.send_message(chat, msg, reply_to=reply_id)
                        except FloodWaitError as e:
                            await asyncio.sleep(e.seconds)
                        except Exception:
                            pass
                        await asyncio.sleep(current_delay)
                except asyncio.CancelledError:
                    pass

            async with state_lock:
                hunt_tasks[chat][client_idx] = asyncio.create_task(client_hunt_loop())

    @client_inst.on(events.NewMessage(pattern=rf"{P}stophunt$"))
    async def stophunt_cmd(event):
        if not await is_authorized(event): return
        chat = event.chat_id
        async with state_lock:
            if chat in hunt_tasks:
                for task in hunt_tasks[chat].values():
                    task.cancel()
                hunt_tasks.pop(chat, None)
        await event.edit("**🛑 Hunt session stopped across all bots!**")

    @client_inst.on(events.NewMessage(pattern=rf"{P}add2(\s+(.+))?$"))
    async def add2_cmd(event):
        if not await is_authorized(event): return
        match_arg = event.pattern_match.group(2)
        usernames = [u.strip() for u in match_arg.split()] if match_arg else DEFAULT_ADD2_BOTS
        await event.edit(f"**🔄 Pulling up `{len(usernames)}` bots (.add2) into the chat...**")
        
        added, failed = 0, 0
        for uname in usernames:
            try:
                clean_uname = uname.replace("@", "")
                user_entity = await client_inst.get_entity(clean_uname)
                await client_inst(InviteToChannelRequest(channel=event.chat_id, users=[user_entity]))
                added += 1
            except Exception as e:
                log.error(f"Failed to add {uname}: {e}")
                failed += 1
            await asyncio.sleep(1)
            
        await event.edit(f"**✨ Add2 Succeeded!**\n• Added: `{added}`\n• Failed: `{failed}`")

    @client_inst.on(events.NewMessage(pattern=rf"{P}add3$"))
    async def add3_cmd(event):
        if not await is_authorized(event): return
        usernames = DEFAULT_ADD3_BOTS
        await event.edit(f"**🔄 Pulling up `{len(usernames)}` bots (.add3) into the chat...**")
        
        added, failed = 0, 0
        for uname in usernames:
            try:
                clean_uname = uname.replace("@", "")
                user_entity = await client_inst.get_entity(clean_uname)
                await client_inst(InviteToChannelRequest(channel=event.chat_id, users=[user_entity]))
                added += 1
            except Exception as e:
                log.error(f"Failed to add {uname}: {e}")
                failed += 1
            await asyncio.sleep(1)
            
        await event.edit(f"**✨ Add3 Succeeded!**\n• Added: `{added}`\n• Failed: `{failed}`")

    @client_inst.on(events.NewMessage(pattern=rf"{P}join\s+(.+)"))
    async def join_cmd(event):
        if not await is_authorized(event): return
        link = event.pattern_match.group(1).strip()
        await event.edit(f"**🔄 Pulling up with all {len(clients)} accounts...**")
        
        success = 0
        for idx, c in enumerate(clients, 1):
            try:
                if "+" in link or "joinchat" in link:
                    from telethon.tl.functions.messages import ImportChatInviteRequest
                    hash_val = link.split("/")[-1].replace("+", "")
                    await c(ImportChatInviteRequest(hash_val))
                else:
                    entity = await c.get_entity(link)
                    await c(JoinChannelRequest(entity))
                success += 1
            except Exception as e:
                log.error(f"Account {idx} join error: {e}")
            await asyncio.sleep(1)
            
        await event.edit(f"**✨ Successfully infiltrated with `{success}/{len(clients)}` accounts!**")

    @client_inst.on(events.NewMessage(pattern=rf"{P}stopall$"))
    async def stopall_cmd(event):
        if not await is_authorized(event): return
        chat = event.chat_id
        async with state_lock:
            if chat in swipe_tasks:
                for task in swipe_tasks[chat].values():
                    task.cancel()
                swipe_tasks.pop(chat, None)
            if chat in hunt_tasks:
                for task in hunt_tasks[chat].values():
                    task.cancel()
                hunt_tasks.pop(chat, None)
            auto_replies.pop(chat, None)
        await event.edit("**⛔ MISSION ABORTED: All active tasks wiped in this chat!**")
        await safe_delete(event, 1)

# ═══════════════ MAIN RUNNER ═══════════════

async def main():
    global clients
    
    for idx, conf in enumerate(ACCOUNTS):
        c = TelegramClient(conf["session"], conf["api_id"], conf["api_hash"])
        await c.start()
        me = await c.get_me()
        clients.append(c)
        
        register_events(c, idx)
        log.info(f"✅ Account online: {me.first_name} (ID: {me.id})")

    log.info(f"🚀 All {len(clients)} userbot accounts locked in under Superowner ID: {SUPEROWNER_ID}!")
    
    await asyncio.gather(*(c.run_until_disconnected() for c in clients))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot gracefully terminated.")
