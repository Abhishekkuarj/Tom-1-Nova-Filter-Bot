from pyrogram.errors import UserNotParticipant, FloodWait
from info import FORCE_SUB_CHANNELS, LONG_IMDB_DESCRIPTION, ADMINS, IS_PREMIUM, TIME_ZONE, TMDB_API_KEY, USE_CAPTION_FILTER, UPDATES_SEND_CHANNEL, FILMS_LINK, REQUEST_FORCE_SUB_CHANNEL
import asyncio
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from pyrogram import enums
import re
from datetime import datetime
from database.users_chats_db import db
from shortzy import Shortzy
import requests, pytz
from Script import script


class temp(object):
    START_TIME = 0
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CANCEL = False
    U_NAME = None
    B_NAME = None
    SETTINGS = {}
    VERIFICATIONS = {}
    GET_ALL_FILES = {}
    USERS_CANCEL = False
    SPELL_CHECK = {}
    GROUPS_CANCEL = False
    BOT = None
    PREMIUM = {}


def get_plan_name(days):
    plan_names = {
        7: "1 Week",
        14: "2 Weeks",
        21: "3 Weeks",
        30: "1 Month",
        60: "2 Months",
        90: "3 Months",
        180: "6 Months",
        365: "1 Year"
    }
    if days in plan_names:
        return f"{plan_names[days]} Plan"
    return f"{days} Days Plan"


async def send_update(title, year):
    if not UPDATES_SEND_CHANNEL:
        return
    btn = [[
        InlineKeyboardButton('📥 Request from Here 📥', url=FILMS_LINK)
    ]]
    data = await get_poster(f"{title} {year}")
    if not data:
        _year = f"({year})" if year else ""
        await temp.BOT.send_message(chat_id=UPDATES_SEND_CHANNEL, text=f"✅ New Added ✅\n\n🏷 Title: {title.title()} {_year}", reply_markup=InlineKeyboardMarkup(btn))
        return
    caption = script.NEW_ADDED_TEMPLATE.format(
        title=data['title'],
        kind=data['kind'],
        votes=data['votes'],
        tmdb_id=data["tmdb_id"],
        runtime=data["runtime"],
        release_date=data['release_date'],
        year=data['year'],
        genres=data['genres'],
        plot=data['plot'],
        rating=data['rating'],
        url=data['url'],
        languages=data['languages'],
        countries=data['countries']
    )
    
    if data.get('poster'):
        await temp.BOT.send_photo(chat_id=UPDATES_SEND_CHANNEL, photo=data.get('poster'), caption=caption, reply_markup=InlineKeyboardMarkup(btn))
    else:
        await temp.BOT.send_message(chat_id=UPDATES_SEND_CHANNEL, text=caption, reply_markup=InlineKeyboardMarkup(btn), link_preview_options=LinkPreviewOptions(is_disabled=True))


async def handle_next_back(data, offset=0, max_results=0):
    out_data = data[offset:][:max_results]
    total_results = len(data)
    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = 0
    return out_data, next_offset, total_results

async def is_subscribed(bot, query):
    btn = []
    if await is_premium(query.from_user.id, bot):
        return btn
    fsub = await db.get_fsub()
    fsub_channels = fsub if fsub else FORCE_SUB_CHANNELS
    if fsub_channels:
        for id in fsub_channels.split():
            try:
                ch_id = int(id)
            except ValueError:
                continue
            try:
                chat = await bot.get_chat(ch_id)
                await bot.get_chat_member(ch_id, query.from_user.id)
            except UserNotParticipant:
                btn.append(
                    [InlineKeyboardButton(f'📢 Join : {chat.title}', url=chat.invite_link)]
                )
            except Exception:
                continue
    req_fsub = await db.get_req_fsub()
    req_fsub_channel = req_fsub if req_fsub else REQUEST_FORCE_SUB_CHANNEL
    if req_fsub_channel:
        for id in req_fsub_channel.split():
            try:
                ch_id = int(id)
            except ValueError:
                continue
            try:
                if not await db.find_join_req(query.from_user.id, ch_id):
                    chat = await bot.get_chat(ch_id)
                    try:
                        await bot.get_chat_member(ch_id, query.from_user.id)
                    except UserNotParticipant:
                        url = await bot.create_chat_invite_link(ch_id, creates_join_request=True)
                        btn.append(
                            [InlineKeyboardButton(f'✨ Request : {chat.title}', url=url.invite_link)]
                        )
            except Exception:
                continue
    return btn


def upload_image(file_path):
    with open(file_path, 'rb') as f:
        files = {'files[]': f}
        response = requests.post("https://uguu.se/upload", files=files)

    if response.status_code == 200:
        try:
            data = response.json()
            return data['files'][0]['url'].replace('\\/', '/')
        except Exception as e:
            return None
    else:
        return None



async def get_poster(query):
    if not TMDB_API_KEY:
        return None
    TMDB_BASE = "https://api.themoviedb.org/3"

    query = query.strip()
    
    import PTN
    
    parsed = PTN.parse(query)
    title = parsed.get("title", query)
    year = parsed.get("year", None)

    url = f"{TMDB_BASE}/search/multi"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title
    }

    res = requests.get(url, params=params).json()

    results = [
        r for r in res.get("results", [])
        if r.get("media_type") in ["movie", "tv"]
    ]

    if not results:
        return None

    if year:
        filtered = []
        for r in results:
            release = r.get("release_date") or r.get("first_air_date")
            if release and release.startswith(str(year)):
                filtered.append(r)

        if filtered:
            results = filtered

    data = results[0]
    tmdb_id = data["id"]
    media_type = data["media_type"]

    data = requests.get(
        f"{TMDB_BASE}/{media_type}/{tmdb_id}",
        params={"api_key": TMDB_API_KEY}
    ).json()

    title = data.get("title") or data.get("name")

    poster = None
    if data.get("poster_path"):
        poster = f"https://image.tmdb.org/t/p/original{data['poster_path']}"

    release_date = data.get("release_date") or data.get("first_air_date") or "N/A"

    genres_list = data.get("genres", [])
    genres = ", ".join([f"#{g['name'].title().replace(' ', '').replace('-', '')}" for g in genres_list]) if genres_list else "N/A"

    if media_type == "movie":
        runtime_val = data.get("runtime")
    else:
        ep_rt = data.get("episode_run_time")
        runtime_val = ep_rt[0] if ep_rt else None
    runtime = f"{runtime_val} min" if runtime_val else "N/A"

    plot = data.get("overview")
    plot = plot if LONG_IMDB_DESCRIPTION else (str(plot)[:200] if plot else "N/A")

    rating = data.get("vote_average") or "N/A"
    votes = data.get("vote_count") or "N/A"

    langs_list = data.get("spoken_languages", [])
    languages = ", ".join([f"#{l['english_name'].title().replace(' ', '').replace('-', '')}" for l in langs_list]) if langs_list else "N/A"

    countries_list = data.get("production_countries", [])
    countries = ", ".join([f"#{c['name'].title().replace(' ', '').replace('-', '')}" for c in countries_list]) if countries_list else "N/A"

    return {
        "title": title,
        "tmdb_id": tmdb_id,
        "kind": media_type,
        "languages": languages,
        "countries": countries,
        "release_date": release_date,
        "year": release_date[:4] if release_date else None,
        "genres": genres,
        "runtime": runtime,
        "rating": rating,
        "votes": votes,
        "poster": poster,
        "plot": plot,
        "url": f"https://www.themoviedb.org/{media_type}/{tmdb_id}"
    }

async def is_check_admin(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except:
        return False

async def get_verify_status(user_id):
    verify = temp.VERIFICATIONS.get(user_id)
    if not verify:
        verify = await db.get_verify_status(user_id)
        temp.VERIFICATIONS[user_id] = verify
    return verify

async def update_verify_status(user_id, verify_token="", is_verified=False, link="", expire_time=0):
    current = await get_verify_status(user_id)
    current['verify_token'] = verify_token
    current['is_verified'] = is_verified
    current['link'] = link
    current['expire_time'] = expire_time
    temp.VERIFICATIONS[user_id] = current
    await db.update_verify_status(user_id, current)

    
async def is_premium(user_id, bot):
    if not IS_PREMIUM:
        return False
    if user_id in ADMINS:
        return True
    mp = await db.get_plan(user_id)
    if mp['premium']:
        if mp['expire'] < datetime.now():
            await bot.send_message(user_id, f"⏳ <b>VIP Premium Expired!</b>\n\n<blockquote>👑 Your <b>{mp['plan']}</b> VIP Premium access will expire on <code>{mp['expire'].strftime('%Y.%m.%d %H:%M:%S')}</code>. Please use /plan to renew your subscription and maintain uninterrupted ad-free service!</blockquote>")
            mp['expire'] = ''
            mp['plan'] = ''
            mp['premium'] = False
            await db.update_plan(user_id, mp)
            return False
        return True
    else:
        return False


async def check_premium(bot):
    while True:
        pr = [i for i in await db.get_premium_users() if i['status']['premium']]
        for p in pr:
            mp = p['status']
            if mp['expire'] < datetime.now():
                try:
                    await bot.send_message(
                        p['id'],
                        f"⏳ <b>VIP Premium Expired!</b>\n\n<blockquote>👑 Your <b>{mp['plan']}</b> VIP Premium access will expire on <code>{mp['expire'].strftime('%Y.%m.%d %H:%M:%S')}</code>. Please use /plan to renew your subscription and maintain uninterrupted ad-free service!</blockquote>"
                    )
                except Exception:
                    pass
                mp['expire'] = ''
                mp['plan'] = ''
                mp['premium'] = False
                await db.update_plan(p['id'], mp)
        await asyncio.sleep(1200)


async def broadcast_messages(user_id, message, pin):
    try:
        m = await message.copy(chat_id=user_id)
        if pin:
            await m.pin(both_sides=True)
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message, pin)
    except Exception as e:
        await db.delete_user(int(user_id))
        return "Error"

async def groups_broadcast_messages(chat_id, message, pin):
    try:
        k = await message.copy(chat_id=chat_id)
        if pin:
            try:
                await k.pin()
            except:
                pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await groups_broadcast_messages(chat_id, message, pin)
    except Exception as e:
        await db.delete_chat(chat_id)
        return "Error"

async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS.update({group_id: settings})
    return settings
    
async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current.update({key: value})
    temp.SETTINGS.update({group_id: current})
    await db.update_settings(group_id, current)

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


async def get_shortlink(url, api, link):
    shortzy = Shortzy(api_key=api, base_site=url)
    link = await shortzy.convert(link)
    return link

def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return '-' if result == '' else result

def get_wish():
    time = datetime.now(pytz.timezone(TIME_ZONE))
    now = time.strftime("%H")
    if now < "12":
        status = "🌅 Good morning 🌞"
    elif now < "18":
        status = "🌤️ Good afternoon 🌗"
    else:
        status = "🌙 Good evening 🌘"
    return status
    
async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:]
        if value:
            value = int(value)
        return value, unit
    value, unit = extract_value_and_unit(time_string)
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0


async def render_list_page(client, query_or_msg, user_id, list_type="watchlist", page=0, edit=False):
    if list_type == "favorites":
        items = await db.get_favorites(user_id)
        title = "❤️ <b>Your Favorites List</b>"
        empty_text = "💔 <b>Your Favorites list is currently empty!</b>\n\nClick on <b>❤️ Favorites</b> when viewing any file to save it here for quick access later."
        del_cb_prefix = "del_fav"
        page_cb_prefix = "favorites_page"
        clear_cb = "clear_all_favorites"
        clear_text = "🗑️ Clear All Favorites"
    else:
        items = await db.get_watchlist(user_id)
        title = "🔖 <b>Your Watchlist</b>"
        empty_text = "📂 <b>Your Watchlist is currently empty!</b>\n\nClick on <b>🔖 Watchlist</b> when viewing any file to save it here for quick access later."
        del_cb_prefix = "del_watch"
        page_cb_prefix = "watchlist_page"
        clear_cb = "clear_all_watchlist"
        clear_text = "🗑️ Clear All Watchlist"
        
    if not items:
        buttons = [[InlineKeyboardButton("✖️ Close", callback_data="close_data")]]
        if edit:
            return await query_or_msg.edit_message_text(empty_text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            return await query_or_msg.reply_text(empty_text, reply_markup=InlineKeyboardMarkup(buttons))
    
    total_files = len(items)
    total_pages = (total_files + 9) // 10
    if page >= total_pages:
        page = max(0, total_pages - 1)
        
    start_idx = page * 10
    end_idx = min(start_idx + 10, total_files)
    
    current_ids = items[start_idx:end_idx]
    buttons = []
    from database.ia_filterdb import get_file_details
    
    for f_id in current_ids:
        file_info = await get_file_details(f_id)
        if not file_info:
            buttons.append([
                InlineKeyboardButton("⚠️ [Deleted/Missing File]", callback_data=f"file#{f_id}"),
                InlineKeyboardButton("✖️", callback_data=f"{del_cb_prefix}#{f_id}#list#{page}")
            ])
            continue
        fname = file_info.get('file_name', 'Unknown')
        fsize = get_size(file_info.get('file_size', 0))
        buttons.append([
            InlineKeyboardButton(f"📁 [{fsize}] {fname[:35]}", callback_data=f"file#{f_id}"),
            InlineKeyboardButton("✖️", callback_data=f"{del_cb_prefix}#{f_id}#list#{page}")
        ])
        
    page_buttons = []
    if page > 0:
        page_buttons.append(InlineKeyboardButton("🔙 Back", callback_data=f"{page_cb_prefix}#{page - 1}"))
    page_buttons.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if end_idx < total_files:
        page_buttons.append(InlineKeyboardButton("⏭️ Next", callback_data=f"{page_cb_prefix}#{page + 1}"))
    if len(page_buttons) > 1:
        buttons.append(page_buttons)
        
    buttons.append([InlineKeyboardButton(clear_text, callback_data=clear_cb)])
    buttons.append([InlineKeyboardButton("✖️ Close", callback_data="close_data")])
    
    text = f"{title} (<b>{total_files} Files</b>)\n\n<blockquote>💡 Click any file below to get it instantly, or click ✖️ to remove it from your list.</blockquote>"
    
    if edit:
        await query_or_msg.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query_or_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))



async def get_imdb_suggestions(query):
    try:
        from urllib.parse import quote
        import aiohttp
        url = f'https://v3.sg.media-imdb.com/suggestion/x/{quote(query.lower())}.json'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for d in data.get('d', []):
                        if d.get('q') in ['feature', 'TV series', 'TV mini-series', 'TV movie', 'video', 'short', 'TV special', 'TV short', 'documentary']:
                            title = d.get('l')
                            year = d.get('y')
                            if year:
                                title = f"{title} ({year})"
                            results.append({
                                'title': title,
                                'id': d.get('id')
                            })
                    return results
    except Exception as e:
        print(f"IMDb suggest error: {e}")
    return []
