import asyncio
import re
from time import time as time_now
import math, os
import random
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
from datetime import datetime, timedelta
from info import AUTO_FILTER, PM_SEARCH, VERIFY_TUTORIAL, IS_PREMIUM, PICS, TUTORIAL, TUTORIAL_NAME, SHORTLINK_API, SHORTLINK_URL, OWNER_USERNAME, SECOND_FILES_DATABASE_URL, ADMINS, URL, MAX_BTN, BIN_CHANNEL, IS_STREAM, DELETE_TIME, FILMS_LINK, LOG_CHANNEL, SUPPORT_GROUP, SUPPORT_LINK, UPDATES_LINK, LANGUAGES, QUALITY
from pyrogram.types import ReplyParameters, WebAppInfo, PreCheckoutQuery, Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, LinkPreviewOptions
from pyrogram import Client, filters, enums
from utils import get_plan_name, handle_next_back, is_premium, get_size, is_subscribed, is_check_admin, get_wish, get_shortlink, get_readable_time, get_poster, get_imdb_suggestions, temp, get_settings, save_group_settings, render_list_page
from database.users_chats_db import db
from database.ia_filterdb import delete_files, db_count_documents, second_db_count_documents, get_search_results, get_file_details
from pyrogram.file_id import FileId
from plugins.commands import get_grp_stg
from urllib.parse import quote

BUTTONS = {}
CAP = {}
SELECT = {}
FILES= {}
ALL_FILES={}
QUERY_CACHE = {}


def clean_filename_for_matching(filename: str) -> str:
    fname = filename.lower()
    fname = re.sub(r'\b(?:x264|x265|x256|h264|h265|hevc|avc|xvid|divx|av1|vp9)\b', ' ', fname)
    fname = re.sub(r'\b(?:2160p|1080p|720p|480p|360p|240p|4k|8k|1080i|720i)\b', ' ', fname)
    fname = re.sub(r'\b(?:10bit|8bit|12bit|6ch|2ch|5\.1ch|7\.1ch|5\.1|7\.1|2\.0|aac|flac|dts|truehd|atmos|mp3|ac3|dd5\.1)\b', ' ', fname)
    fname = re.sub(r'\b\d+(?:\.\d+)?\s*(?:mb|gb|kb|kbps|mbps|fps|hz|mhz)\b', ' ', fname)
    return fname


def get_seasons_from_filename(filename: str) -> set:
    seasons = set()
    fname = clean_filename_for_matching(filename)
    
    range_matches = re.findall(r'(?:s|season)\s*[\._-]?\s*(\d{1,2})\s*(?:-|to)\s*(?:s|season)?\s*[\._-]?\s*(\d{1,2})', fname)
    for start, end in range_matches:
        try:
            s_start, s_end = int(start), int(end)
            if 1 <= s_start <= 50 and 1 <= s_end <= 50 and s_start <= s_end:
                for s_num in range(s_start, s_end + 1):
                    seasons.add(s_num)
        except ValueError:
            pass

    single_matches = re.findall(r'(?<![a-z])(?:s|season)\s*[\._-]?\s*(\d{1,2})(?!\d)', fname)
    for match in single_matches:
        try:
            val = int(match)
            if 1 <= val <= 50:
                seasons.add(val)
        except ValueError:
            pass

    x_matches = re.findall(r'(?<!\d)(\d{1,2})x\d{1,4}(?!\d)', fname)
    for match in x_matches:
        try:
            val = int(match)
            if 1 <= val <= 50:
                seasons.add(val)
        except ValueError:
            pass

    nth_matches = re.findall(r'(\d{1,2})(?:st|nd|rd|th)\s*season', fname)
    for match in nth_matches:
        try:
            val = int(match)
            if 1 <= val <= 50:
                seasons.add(val)
        except ValueError:
            pass

    return seasons


def get_episodes_from_filename(filename: str, season: int = None) -> set:
    episodes = set()
    fname = clean_filename_for_matching(filename)
    
    if season is not None:
        s_padded = f"{season:02d}" if season < 10 else str(season)
        s_patterns = [
            fr"s(?:eason)?\s*[._-]?\s*(?:{season}|{s_padded})\s*[._-]?\s*(?:e|ep|episode)\s*[._-]?\s*(\d{{1,4}})",
            fr"(?<!\d)(?:{season}|{s_padded})x(\d{{1,4}})(?!\d)",
        ]
        for pat in s_patterns:
            matches = re.findall(pat, fname)
            for match in matches:
                try:
                    val = int(match)
                    if 0 <= val <= 3000:
                        episodes.add(val)
                except ValueError:
                    pass

    range_matches = re.findall(r'(?<![a-z])(?:e|ep|episode)\s*[\._-]?\s*(\d{1,4})\s*(?:-|to)\s*(?:e|ep|episode)?\s*[\._-]?\s*(\d{1,4})(?!\d)', fname)
    for start, end in range_matches:
        try:
            e_start, e_end = int(start), int(end)
            if 0 <= e_start <= 3000 and 0 <= e_end <= 3000 and e_start <= e_end and (e_end - e_start) <= 100:
                for e_num in range(e_start, e_end + 1):
                    episodes.add(e_num)
        except ValueError:
            pass

    single_matches = re.findall(r'(?<![a-z])(?:e|ep|episode)\s*[\._-]?\s*(\d{1,4})(?!\d)', fname)
    for match in single_matches:
        try:
            val = int(match)
            if 0 <= val <= 3000:
                episodes.add(val)
        except ValueError:
            pass

    if season is None:
        x_matches = re.findall(r'(?<!\d)\d{1,2}x(\d{1,4})(?!\d)', fname)
        for match in x_matches:
            try:
                val = int(match)
                if 0 <= val <= 3000:
                    episodes.add(val)
            except ValueError:
                pass

    return episodes


def filter_files(all_files, select_dict):
    lang_sel = select_dict.get('lang', 'any')
    qual_sel = select_dict.get('qual', 'any')
    seas_sel = select_dict.get('season', 'any')
    epis_sel = select_dict.get('episode', 'any')

    filtered = []
    for file in all_files:
        fname = file.get('file_name', '').lower()
        lang_ok = (lang_sel == 'any') or (lang_sel.lower() in fname)
        qual_ok = (qual_sel == 'any') or (qual_sel.lower() in fname)
        if seas_sel == 'any':
            seas_ok = True
        else:
            try:
                seas_ok = int(seas_sel) in get_seasons_from_filename(fname)
            except ValueError:
                seas_ok = False
        if epis_sel == 'any':
            epis_ok = True
        else:
            try:
                s_num = int(seas_sel) if seas_sel != 'any' else None
                epis_ok = int(epis_sel) in get_episodes_from_filename(fname, season=s_num)
            except ValueError:
                epis_ok = False
        if lang_ok and qual_ok and seas_ok and epis_ok:
            filtered.append(file)
    return filtered



@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if message.text.startswith("/"):
        return

    if not PM_SEARCH:
        return await message.reply_text('⚠️ PM search was disabled!')
    if not AUTO_FILTER:
        return await message.reply_text('⚠️ Auto filter was disabled!')
    s = await message.reply(f"<b><i>🔎 `{message.text}` searching...</i></b>", reply_parameters=ReplyParameters(message_id=message.id))
    await auto_filter(client, message, s)

            

@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message and message.from_user else 0

    if AUTO_FILTER:
        if not user_id:
            await message.reply("❌ I'm not working for anonymous admin!")
            return
        if SUPPORT_GROUP and message.chat.id == SUPPORT_GROUP:
            files = await get_search_results(message.text)
            if files:
                btn = [[
                    InlineKeyboardButton("📍 Here", url=FILMS_LINK)
                ]]
                await message.reply_text(f'Total {len(files)} results found in this group', reply_markup=InlineKeyboardMarkup(btn))
            return
            
        if message.text.startswith("/") or re.findall(r'https?://\S+|www\.\S+|t\.me/\S+|@\w+', message.text):
            return

        s = await message.reply(f"<b><i>🔎 `{message.text}` searching...</i></b>")
        await auto_filter(client, message, s)
    else:
        k = await message.reply_text('❌ Auto Filter Off!')
        await asyncio.sleep(5)
        await k.delete()
        try:
            await message.delete()
        except:
            pass


@Client.on_callback_query(filters.regex(r"^next_"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)

    search = BUTTONS.get(key)
    cap = CAP.get(key)
    files = FILES.get(key)
    select = SELECT.get(key)
    if not search:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return

    offset = int(offset)
    files, n_offset, total = await handle_next_back(files, max_results=MAX_BTN, offset=offset)

    temp.GET_ALL_FILES[key] = files
    settings = await get_settings(query.message.chat.id)
    auto_del_time = settings.get("auto_delete_time", DELETE_TIME)
    del_msg = f"\n\n<b>⚠️ this message will be auto delete after <code>{get_readable_time(auto_del_time)}</code> to avoid copyright issues</b>" if settings["auto_delete"] else ''
    files_link = ''

    if settings['links'] and query.message.chat.type != enums.ChatType.PRIVATE:
        btn = []
        for file_num, file in enumerate(files, start=offset+1):
            files_link += f"""<b>\n\n{file_num}. <a href="https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file['_id']}">[{get_size(file['file_size'])}] {file['file_name']}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"{get_size(file['file_size'])} - {file['file_name']}", callback_data=f"file#{file['_id']}")
        ]
            for file in files
        ]

    if 0 < offset <= MAX_BTN:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - MAX_BTN
        
    if total <= MAX_BTN:
        btn.append(
            [InlineKeyboardButton("🚫 No More Pages", callback_data="buttons")]
        )
    elif n_offset == 0:
        btn.append(
            [InlineKeyboardButton("🔙 Back", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"{math.ceil(int(offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(int(offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton("⏭️ Next", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("🔙 Back", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"{math.ceil(int(offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons"),
                InlineKeyboardButton("⏭️ Next", callback_data=f"next_{req}_{key}_{n_offset}")
            ]
        )

    lang = "🌐 Language" if select.get('lang', 'any') == 'any' else f"✔️ {select['lang'].title()}"
    qual = "💎 Quality" if select.get('qual', 'any') == 'any' else f"✔️ {select['qual'].title()}"
    seas = "📁 Season" if select.get('season', 'any') == 'any' else f"✔️ Season {select['season']}"
    epis = "🎬 Episode" if select.get('episode', 'any') == 'any' else f"✔️ Episode {select['episode']}"
    btn.insert(0,
                [InlineKeyboardButton(lang, callback_data=f"languages#{key}#{req}#{offset}"),
                InlineKeyboardButton(qual, callback_data=f"quality#{key}#{req}#{offset}")]
            )
    btn.insert(1,
                [InlineKeyboardButton(seas, callback_data=f"season#{key}#{req}#{offset}"),
                InlineKeyboardButton(epis, callback_data=f"episode#{key}#{req}#{offset}")]
            )

    if settings['shortlink'] and not await is_premium(query.from_user.id, bot):
        btn.insert(2,
            [InlineKeyboardButton("⚡ Send All", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}')),
             InlineKeyboardButton(settings['tutorial_name'], url=settings['tutorial'])]
        )
    else:
        btn.insert(2,
            [InlineKeyboardButton("⚡ Send All", callback_data=f"send_all#{key}#{req}"),
             InlineKeyboardButton(settings['tutorial_name'], url=settings['tutorial'])]
        )
    btn.append(
        [InlineKeyboardButton('💎 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")]
    )

    await query.message.edit_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), link_preview_options=LinkPreviewOptions(is_disabled=True), parse_mode=enums.ParseMode.HTML)


@Client.on_callback_query(filters.regex(r"^languages"))
async def languages_(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)
    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return

    available_langs = set()
    for file in all_files:
        fname = file.get('file_name', '').lower()
        for lang in LANGUAGES:
            if lang.lower() in fname:
                available_langs.add(lang.lower())
    available_langs = sorted(available_langs)
    if not available_langs:
        return await query.answer("⚠️ No specific languages available for these files!", show_alert=True)

    current_sel = SELECT.get(key)
    lang_sel = current_sel.get('lang')
    qual_sel = current_sel.get('qual')

    any_lang_tick = "✅" if lang_sel == 'any' else "🌐"
    btn = [[InlineKeyboardButton(f"{any_lang_tick} Any Language", callback_data=f"pick_lang#any#{key}#{req}")]]

    pairs = []
    for i in range(0, len(available_langs) - 1, 2):
        l1 = available_langs[i]
        l2 = available_langs[i+1]
        tick1 = "✅ " if lang_sel == l1 else ""
        tick2 = "✅ " if lang_sel == l2 else ""
        pairs.append([
            InlineKeyboardButton(text=f"{tick1}{l1.title()}", callback_data=f"pick_lang#{l1}#{key}#{req}"),
            InlineKeyboardButton(text=f"{tick2}{l2.title()}", callback_data=f"pick_lang#{l2}#{key}#{req}")
        ])
    btn.extend(pairs)

    if len(available_langs) % 2 != 0:
        last = available_langs[-1]
        tick = "✅ " if lang_sel == last else ""
        btn.append([InlineKeyboardButton(text=f"{tick}{last.title()}", callback_data=f"pick_lang#{last}#{key}#{req}")])

    btn.append([InlineKeyboardButton(text="🔙 Back To Main Page", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(
        f"🌐 <b>Select Language for: {BUTTONS[key]}\n\n👇 <b>Choose below:</b>",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_callback_query(filters.regex(r"^pick_lang"))
async def pick_lang(client: Client, query: CallbackQuery):
    _, lang, key, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)

    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return
    old_lang = SELECT[key].get('lang', 'any')
    SELECT[key]['lang'] = lang

    filtered = filter_files(all_files, SELECT[key])
    if not filtered:
        SELECT[key]['lang'] = old_lang
        await query.answer("⚠️ Sorry, no files found for the selected filters! Please try another selection.", show_alert=True)
        return

    FILES[key] = filtered
    temp.GET_ALL_FILES[key] = filtered
    query.data = f"next_{req}_{key}_0"
    await next_page(client, query)


@Client.on_callback_query(filters.regex(r"^quality"))
async def quality(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)

    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return

    available_quals = set()
    for file in all_files:
        fname = file.get('file_name', '').lower()
        for qual in QUALITY:
            if qual.lower() in fname:
                available_quals.add(qual.lower())
    available_quals = sorted(available_quals)
    if not available_quals:
        return await query.answer("⚠️ No specific qualities available for these files!", show_alert=True)

    current_sel = SELECT.get(key)
    lang_sel = current_sel.get('lang')
    qual_sel = current_sel.get('qual')

    any_qual_tick = "✅" if qual_sel == 'any' else "🎞"
    btn = [[InlineKeyboardButton(f"{any_qual_tick} Any Quality", callback_data=f"pick_qual#any#{key}#{req}")]]

    pairs = []
    for i in range(0, len(available_quals) - 1, 2):
        q1 = available_quals[i]
        q2 = available_quals[i+1]
        tick1 = "✅ " if qual_sel == q1 else ""
        tick2 = "✅ " if qual_sel == q2 else ""
        pairs.append([
            InlineKeyboardButton(text=f"{tick1}{q1.title()}", callback_data=f"pick_qual#{q1}#{key}#{req}"),
            InlineKeyboardButton(text=f"{tick2}{q2.title()}", callback_data=f"pick_qual#{q2}#{key}#{req}")
        ])
    btn.extend(pairs)

    if len(available_quals) % 2 != 0:
        last = available_quals[-1]
        tick = "✅ " if qual_sel == last else ""
        btn.append([InlineKeyboardButton(text=f"{tick}{last.title()}", callback_data=f"pick_qual#{last}#{key}#{req}")])

    btn.append([InlineKeyboardButton(text="🔙 Back To Main Page", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(
        f"💎 <b>Select Quality for: {BUTTONS[key]}\n\n👇 <b>Choose below:</b>",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_callback_query(filters.regex(r"^pick_qual"))
async def pick_qual(client: Client, query: CallbackQuery):
    _, qual, key, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)

    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return
    old_qual = SELECT[key].get('qual', 'any')
    SELECT[key]['qual'] = qual

    filtered = filter_files(all_files, SELECT[key])
    if not filtered:
        SELECT[key]['qual'] = old_qual
        await query.answer("⚠️ Sorry, no files found for the selected filters! Please try another selection.", show_alert=True)
        return

    FILES[key] = filtered
    temp.GET_ALL_FILES[key] = filtered
    query.data = f"next_{req}_{key}_0"
    await next_page(client, query)


@Client.on_callback_query(filters.regex(r"^season"))
async def season_(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)
    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return

    available_seasons = set()
    for file in all_files:
        fname = file.get('file_name', '')
        seasons_in_file = get_seasons_from_filename(fname)
        available_seasons.update(seasons_in_file)
    available_seasons = sorted(available_seasons)

    if not available_seasons:
        return await query.answer("⚠️ No Season numbers found in these files!", show_alert=True)

    current_sel = SELECT.get(key, {})
    seas_sel = current_sel.get('season', 'any')

    any_seas_tick = "✅" if seas_sel == 'any' else "📁"
    btn = [[InlineKeyboardButton(f"{any_seas_tick} Any Season", callback_data=f"pick_seas#any#{key}#{req}")]]

    pairs = []
    for i in range(0, len(available_seasons) - 1, 2):
        s1 = available_seasons[i]
        s2 = available_seasons[i+1]
        tick1 = "✅ " if seas_sel == str(s1) else ""
        tick2 = "✅ " if seas_sel == str(s2) else ""
        pairs.append([
            InlineKeyboardButton(text=f"{tick1}Season {s1}", callback_data=f"pick_seas#{s1}#{key}#{req}"),
            InlineKeyboardButton(text=f"{tick2}Season {s2}", callback_data=f"pick_seas#{s2}#{key}#{req}")
        ])
    btn.extend(pairs)

    if len(available_seasons) % 2 != 0:
        last = available_seasons[-1]
        tick = "✅ " if seas_sel == str(last) else ""
        btn.append([InlineKeyboardButton(text=f"{tick}Season {last}", callback_data=f"pick_seas#{last}#{key}#{req}")])

    btn.append([InlineKeyboardButton(text="🔙 Back To Main Page", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(
        f"📁 <b>Select Season for: {BUTTONS[key]}\n\n👇 <b>Choose below:</b>",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_callback_query(filters.regex(r"^pick_seas"))
async def pick_seas(client: Client, query: CallbackQuery):
    _, seas, key, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)

    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return

    old_seas = SELECT[key].get('season', 'any')
    old_epis = SELECT[key].get('episode', 'any')
    
    SELECT[key]['season'] = seas
    if old_seas != seas:
        SELECT[key]['episode'] = 'any'

    filtered = filter_files(all_files, SELECT[key])
    if not filtered:
        SELECT[key]['season'] = old_seas
        SELECT[key]['episode'] = old_epis
        await query.answer("⚠️ Sorry, no files found for the selected season! Please try another selection.", show_alert=True)
        return

    FILES[key] = filtered
    temp.GET_ALL_FILES[key] = filtered
    query.data = f"next_{req}_{key}_0"
    await next_page(client, query)


@Client.on_callback_query(filters.regex(r"^episode"))
async def episode_(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)
    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return

    current_sel = SELECT.get(key, {})
    seas_sel = current_sel.get('season', 'any')
    
    if seas_sel == 'any':
        return await query.answer("⚠️ Please select a Season first before selecting an Episode!", show_alert=True)

    available_episodes = set()
    for file in all_files:
        fname = file.get('file_name', '')
        try:
            if int(seas_sel) in get_seasons_from_filename(fname):
                episodes_in_file = get_episodes_from_filename(fname, season=int(seas_sel))
                available_episodes.update(episodes_in_file)
        except ValueError:
            pass
            
    available_episodes = sorted(available_episodes)

    if not available_episodes:
        return await query.answer(f"⚠️ No Episode numbers found for Season {seas_sel}!", show_alert=True)

    epis_sel = current_sel.get('episode', 'any')

    any_epis_tick = "✅" if epis_sel == 'any' else "🎬"
    btn = [[InlineKeyboardButton(f"{any_epis_tick} Any Episode", callback_data=f"pick_epis#any#{key}#{req}")]]

    pairs = []
    for i in range(0, len(available_episodes) - 1, 2):
        e1 = available_episodes[i]
        e2 = available_episodes[i+1]
        tick1 = "✅ " if epis_sel == str(e1) else ""
        tick2 = "✅ " if epis_sel == str(e2) else ""
        pairs.append([
            InlineKeyboardButton(text=f"{tick1}Episode {e1}", callback_data=f"pick_epis#{e1}#{key}#{req}"),
            InlineKeyboardButton(text=f"{tick2}Episode {e2}", callback_data=f"pick_epis#{e2}#{key}#{req}")
        ])
    btn.extend(pairs)

    if len(available_episodes) % 2 != 0:
        last = available_episodes[-1]
        tick = "✅ " if epis_sel == str(last) else ""
        btn.append([InlineKeyboardButton(text=f"{tick}Episode {last}", callback_data=f"pick_epis#{last}#{key}#{req}")])

    btn.append([InlineKeyboardButton(text="🔙 Back To Main Page", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(
        f"🎬 <b>Select Episode for Season {seas_sel} of: {BUTTONS[key]}\n\n👇 <b>Choose below:</b>",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_callback_query(filters.regex(r"^pick_epis"))
async def pick_epis(client: Client, query: CallbackQuery):
    _, epis, key, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)

    all_files = ALL_FILES.get(key)
    if not all_files:
        await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis search session has expired. Please send your query again!", show_alert=True)
        return

    old_epis = SELECT[key].get('episode', 'any')
    SELECT[key]['episode'] = epis

    filtered = filter_files(all_files, SELECT[key])
    if not filtered:
        SELECT[key]['episode'] = old_epis
        await query.answer("⚠️ Sorry, no files found for the selected episode! Please try another selection.", show_alert=True)
        return

    FILES[key] = filtered
    temp.GET_ALL_FILES[key] = filtered
    query.data = f"next_{req}_{key}_0"
    await next_page(client, query)


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)
    search = temp.SPELL_CHECK.get(id)
    if not search:
        return await query.answer("⚠️ This button has expired! Please search again.", show_alert=True)
    s = await query.message.edit_text(f"🔍 <b>Searching Cloud Database For:</b> <code>{search}</code>\n\n<blockquote>⏳ <i>Please wait while our smart indexing engine scans all high-speed cloud servers...</i></blockquote>")
    files = await get_search_results(search)
    if files:
        k = (search, files)
        await auto_filter(bot, query, s, k)
    else:
        google_search = quote(search)
        btn = [[
            InlineKeyboardButton("💡 Instructions", callback_data='instructions'),
            InlineKeyboardButton("🌐 Search Google", url=f"https://www.google.com/search?q={google_search}")
        ]]
        k = await query.message.edit(text=script.NOT_FILE_TXT.format(query.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await k.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass


@Client.on_callback_query(filters.regex(r"^req_completed"))
async def request_completed(client, query):
    _, req_id = query.data.split("#")
    req = await db.get_movie_req(req_id)
    if not req:
        return await query.answer("⚠️ Request ID not found or already processed!", show_alert=True)
    
    user_id = req['user_id']
    movie_name = req['movie_name']
    
    try:
        await client.send_message(user_id, f"✅ Your request for **{movie_name}** has been uploaded!")
    except:
        pass
        
    await query.edit_message_text(f"{query.message.text}\n\n**Status:** ✅ Completed")
    await db.del_movie_req(req_id)

@Client.on_callback_query(filters.regex(r"^req_reject"))
async def request_rejected(client, query):
    _, req_id = query.data.split("#")
    req = await db.get_movie_req(req_id)
    if not req:
        return await query.answer("⚠️ Request ID not found or already processed!", show_alert=True)
    
    user_id = req['user_id']
    movie_name = req['movie_name']
    
    try:
        await client.send_message(user_id, f"❌ Your request for **{movie_name}** has been rejected.")
    except:
        pass
        
    await query.edit_message_text(f"{query.message.text}\n\n**Status:** ❌ Rejected")
    await db.del_movie_req(req_id)


async def safe_edit_media_caption(query: CallbackQuery, caption: str, reply_markup: InlineKeyboardMarkup):
    try:
        if len(caption.encode('utf-16-le')) // 2 > 1000:
            raise ValueError("Caption too long for photo media")
        await query.edit_message_media(
            InputMediaPhoto(random.choice(PICS), caption=caption),
            reply_markup=reply_markup
        )
    except Exception:
        try:
            await query.edit_message_text(text=caption, reply_markup=reply_markup)
        except Exception:
            try:
                await query.message.reply_text(text=caption, reply_markup=reply_markup)
            except Exception:
                pass


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        try:
            user = query.message.reply_to_message.from_user.id
        except:
            user = query.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis action is restricted!", show_alert=True)
        await query.answer("✖️ Menu Closed!")
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
  
    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        try:
            user = query.message.reply_to_message.from_user.id
        except:
            user = query.message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)
        
        if query.message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            return await query.answer(url=f"https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file_id}")
        
        await query.answer("⚡ Sending file...")
        files = await get_file_details(file_id)
        if not files:
            return await query.message.reply('⚠️ <b>File Not Found!</b>')
            
        settings = await get_settings(query.message.chat.id)
        if settings.get('shortlink') and not await is_premium(query.from_user.id, client):
            link = await get_shortlink(settings['url'], settings['api'], f"https://t.me/{temp.U_NAME}?start=shortlink_{query.message.chat.id}_{file_id}")
            btn = [[InlineKeyboardButton("🔗 Get File", url=link)]]
            return await query.message.reply(f"📁 <b>{files['file_name']}</b>\n\n✨ Click below to get your file:", reply_markup=InlineKeyboardMarkup(btn))
            
        CAPTION = settings.get('caption', script.FILE_CAPTION)
        f_caption = CAPTION.format(
            file_name=files['file_name'],
            file_size=get_size(files['file_size']),
            file_caption=files.get('caption', '')
        )
        user_watchlist = await db.get_watchlist(query.from_user.id)
        user_favorites = await db.get_favorites(query.from_user.id)
        f_id_str = str(file_id)
        watch_btn = InlineKeyboardButton("🗑️ Remove Watchlist", callback_data=f"del_watch#{f_id_str}") if f_id_str in user_watchlist else InlineKeyboardButton("🔖 Add Watchlist", callback_data=f"add_watch#{f_id_str}")
        fav_btn = InlineKeyboardButton("💔 Remove Favorites", callback_data=f"del_fav#{f_id_str}") if f_id_str in user_favorites else InlineKeyboardButton("❤️ Add Favorites", callback_data=f"add_fav#{f_id_str}")
        if IS_STREAM and URL:
            btn = [[
                InlineKeyboardButton("⚡ Watch & Download", callback_data=f"stream#{f_id_str}")
            ],[
                watch_btn, fav_btn
            ],[
                InlineKeyboardButton("✖️ Close", callback_data="close_data")
            ]]
        else:
            btn = [[
                watch_btn, fav_btn
            ],[
                InlineKeyboardButton("✖️ Close", callback_data="close_data")
            ]]
        try:
            if (FileId.decode(file_id)).file_type == 4:
                await client.send_video(
                    chat_id=query.from_user.id,
                    video=file_id,
                    caption=f_caption,
                    reply_markup=InlineKeyboardMarkup(btn),
                    video_cover=await db.get_video_cover()
                )
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=False,
                    reply_markup=InlineKeyboardMarkup(btn)
                )
        except Exception as e:
            await query.message.reply(f"❌ <b>Error sending file:</b> <code>{e}</code>")

    elif query.data.startswith("get_del_file"):
        ident, group_id, file_id = query.data.split("#")
        if not await is_premium(query.from_user.id, client):
            return await query.answer(f"💎 This feature is reserved for VIP Premium members! Use /plan to upgrade.", show_alert=True)
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start=file_{group_id}_{file_id}")
        await query.message.delete()

    elif query.data.startswith("get_del_send_all_files"):
        ident, group_id, key = query.data.split("#")
        if not await is_premium(query.from_user.id, client):
            return await query.answer(f"💎 This feature is reserved for VIP Premium members! Use /plan to upgrade.", show_alert=True)
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start=all_{group_id}_{key}")
        await query.message.delete()
        
    elif query.data.startswith("stream"):
        file_id = query.data.split('#', 1)[1]
        if not await is_premium(query.from_user.id, client):
            return await query.answer(f"💎 This feature is reserved for VIP Premium members! Use /plan to upgrade.", show_alert=True)
        msg = await client.send_cached_media(chat_id=BIN_CHANNEL, file_id=file_id)
        watch = f"{URL}watch/{msg.id}"
        download = f"{URL}download/{msg.id}"
        user_watchlist = await db.get_watchlist(query.from_user.id)
        user_favorites = await db.get_favorites(query.from_user.id)
        watch_btn = InlineKeyboardButton("🗑️ Remove Watchlist", callback_data=f"del_watch#{file_id}") if str(file_id) in user_watchlist else InlineKeyboardButton("🔖 Add Watchlist", callback_data=f"add_watch#{file_id}")
        fav_btn = InlineKeyboardButton("💔 Remove Favorites", callback_data=f"del_fav#{file_id}") if str(file_id) in user_favorites else InlineKeyboardButton("❤️ Add Favorites", callback_data=f"add_fav#{file_id}")
        btn = [[
            InlineKeyboardButton("🎬 Watch Online", url=watch),
            InlineKeyboardButton("⚡ Fast Download", url=download)
        ],[
            watch_btn, fav_btn
        ],[
            InlineKeyboardButton('✖️ Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)
        await query.edit_message_reply_markup(
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("add_watch"):
        file_id = query.data.split('#', 1)[1]
        await db.add_to_watchlist(query.from_user.id, file_id)
        await query.answer("🔖 File saved to your Watchlist! Use /watchlist to view.", show_alert=True)
        if query.message and query.message.reply_markup and query.message.reply_markup.inline_keyboard:
            new_kb = []
            for row in query.message.reply_markup.inline_keyboard:
                new_row = []
                for btn in row:
                    if btn.callback_data == query.data:
                        new_row.append(InlineKeyboardButton("🗑️ Remove Watchlist", callback_data=f"del_watch#{file_id}"))
                    else:
                        new_row.append(btn)
                new_kb.append(new_row)
            try:
                await query.edit_message_reply_markup(InlineKeyboardMarkup(new_kb))
            except Exception:
                pass

    elif query.data.startswith("del_watch"):
        parts = query.data.split('#')
        file_id = parts[1]
        is_list = len(parts) > 2 and parts[2] == "list"
        await db.remove_from_watchlist(query.from_user.id, file_id)
        await query.answer("🗑️ File removed from your Watchlist!", show_alert=True)
        if is_list:
            page = int(parts[3]) if len(parts) > 3 else 0
            await render_list_page(client, query, query.from_user.id, list_type="watchlist", page=page, edit=True)
        else:
            if query.message and query.message.reply_markup and query.message.reply_markup.inline_keyboard:
                new_kb = []
                for row in query.message.reply_markup.inline_keyboard:
                    new_row = []
                    for btn in row:
                        if btn.callback_data == query.data:
                            new_row.append(InlineKeyboardButton("🔖 Add Watchlist", callback_data=f"add_watch#{file_id}"))
                        else:
                            new_row.append(btn)
                    new_kb.append(new_row)
                try:
                    await query.edit_message_reply_markup(InlineKeyboardMarkup(new_kb))
                except Exception:
                    pass

    elif query.data.startswith("watchlist_page"):
        page = int(query.data.split('#')[1])
        await render_list_page(client, query, query.from_user.id, list_type="watchlist", page=page, edit=True)

    elif query.data == "clear_all_watchlist":
        user_id = query.from_user.id
        await db.col.update_one({'id': int(user_id)}, {'$set': {'watchlist': []}})
        await query.answer("🗑️ All files cleared from your Watchlist!", show_alert=True)
        await render_list_page(client, query, user_id, list_type="watchlist", page=0, edit=True)

    elif query.data.startswith("add_fav"):
        file_id = query.data.split('#', 1)[1]
        await db.add_to_favorites(query.from_user.id, file_id)
        await query.answer("❤️ File added to your Favorites! Use /favorites to view.", show_alert=True)
        if query.message and query.message.reply_markup and query.message.reply_markup.inline_keyboard:
            new_kb = []
            for row in query.message.reply_markup.inline_keyboard:
                new_row = []
                for btn in row:
                    if btn.callback_data == query.data:
                        new_row.append(InlineKeyboardButton("💔 Remove Favorites", callback_data=f"del_fav#{file_id}"))
                    else:
                        new_row.append(btn)
                new_kb.append(new_row)
            try:
                await query.edit_message_reply_markup(InlineKeyboardMarkup(new_kb))
            except Exception:
                pass

    elif query.data.startswith("del_fav"):
        parts = query.data.split('#')
        file_id = parts[1]
        is_list = len(parts) > 2 and parts[2] == "list"
        await db.remove_from_favorites(query.from_user.id, file_id)
        await query.answer("💔 File removed from your Favorites!", show_alert=True)
        if is_list:
            page = int(parts[3]) if len(parts) > 3 else 0
            await render_list_page(client, query, query.from_user.id, list_type="favorites", page=page, edit=True)
        else:
            if query.message and query.message.reply_markup and query.message.reply_markup.inline_keyboard:
                new_kb = []
                for row in query.message.reply_markup.inline_keyboard:
                    new_row = []
                    for btn in row:
                        if btn.callback_data == query.data:
                            new_row.append(InlineKeyboardButton("❤️ Add Favorites", callback_data=f"add_fav#{file_id}"))
                        else:
                            new_row.append(btn)
                    new_kb.append(new_row)
                try:
                    await query.edit_message_reply_markup(InlineKeyboardMarkup(new_kb))
                except Exception:
                    pass

    elif query.data.startswith("favorites_page"):
        page = int(query.data.split('#')[1])
        await render_list_page(client, query, query.from_user.id, list_type="favorites", page=page, edit=True)

    elif query.data == "clear_all_favorites":
        user_id = query.from_user.id
        await db.col.update_one({'id': int(user_id)}, {'$set': {'favorites': []}})
        await query.answer("🗑️ All files cleared from your Favorites!", show_alert=True)
        await render_list_page(client, query, user_id, list_type="favorites", page=0, edit=True)
            
    elif query.data.startswith("checksub"):
        ident, mc = query.data.split("#")
        settings = await get_settings(int(mc.split("_", 2)[1]))
        btn = await is_subscribed(client, query)
        if btn:
            await query.answer(f"📢 Hello {query.from_user.first_name},\nPlease join our updates channel first to use the bot!", show_alert=True)
            btn.append(
                [InlineKeyboardButton("🔁 Try Again", callback_data=f"checksub#{mc}")]
            )
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
            return
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start={mc}")
        await query.message.delete()

    elif query.data == "buttons":
        await query.answer()

    elif query.data == "instructions":
        await query.answer("🎬 Movie Request Format:\n• Example: Black Adam or Black Adam 2022\n\n📺 TV Series Request Format:\n• Example: Loki S01E01 or Loki S01 E01\n\n⚠️ Tip: Do not use special symbols!", show_alert=True)

    elif query.data == 'activate_trial':
        mp = await db.get_plan(query.from_user.id)
        if mp['trial']:
            return await query.message.edit("⚠️ <b>Free Trial Already Claimed!</b>\n\n<blockquote>You have already activated and used your free trial. Please check /plan to upgrade to our VIP premium tiers!</blockquote>")
        ex = datetime.now() + timedelta(hours=1)
        mp['expire'] = ex
        mp['trial'] = True
        mp['plan'] = '1 hour'
        mp['premium'] = True
        await db.update_plan(query.from_user.id, mp)
        await query.message.edit(f"🎉 <b>Trial Activated Successfully!</b>\n\n<blockquote>✨ You now have 1 Hour of full VIP Premium access! Enjoy lightning-fast, ad-free downloads.</blockquote>\n\n⏰ <b>Expires On:</b> <code>{ex.strftime('%Y.%m.%d %H:%M:%S')}</code>")

    elif query.data == 'activate_plan':
        btn = []
        if URL:
            btn.append([InlineKeyboardButton('💳 Pay using WebApp', web_app=WebAppInfo(url=URL + 'activate-plan'))])
        else:
            btn.append([InlineKeyboardButton('💳 Contact Admin to Pay', url=f"https://t.me/{OWNER_USERNAME}")])
        if await is_premium(query.from_user.id, client):
            txt = f"💎 <b>Activate VIP Premium Subscription</b>\n\n<blockquote>Click the button below to complete your activation via our secure WebApp!</blockquote>\n\n👑 <b>Status:</b> You are already an active VIP Premium member!\n💬 <b>24/7 Support:</b> @{OWNER_USERNAME}" 
        else:
            txt = f"💎 <b>Activate VIP Premium Subscription</b>\n\n<blockquote>Click the button below to instantly upgrade and unlock ad-free unlimited cloud streaming!</blockquote>\n\n💬 <b>24/7 Support:</b> @{OWNER_USERNAME}" 
        await query.message.edit(txt, reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("accept_payment"):
        _, id, days = query.data.split("-")
        id = int(id)
        days = int(days)
        user = await client.get_users(id)
        mp = await db.get_plan(id)
        ex = datetime.now() + timedelta(days=days)
        mp['expire'] = ex
        plan = get_plan_name(days)
        mp['plan'] = plan
        mp['premium'] = True
        await db.update_plan(id, mp)
        await query.message.edit(f"✅ <b>VIP Premium Activated!</b>\n\n<blockquote>👑 Successfully granted <b>{plan}</b> access to {user.mention}</blockquote>\n⏰ <b>Expires On:</b> <code>{ex.strftime('%Y.%m.%d %H:%M:%S')}</code>")
        try:
            await client.send_message(user.id, f"🎉 <b>VIP Premium Activated!</b>\n\n<blockquote>👑 Congratulations! You are now an active VIP Premium subscriber with the <b>{plan}</b> plan!</blockquote>\n⏰ <b>Expires On:</b> <code>{ex.strftime('%Y.%m.%d %H:%M:%S')}</code>")
        except:
            pass

    elif query.data.startswith("reject_payment"):
        _, id, days = query.data.split("-")
        id = int(id)
        user = await client.get_users(id)
        await query.message.edit(f"❌ <b>Payment Rejected!</b>\n\n<blockquote>The payment verification for {user.mention} was declined.</blockquote>")
        try:
            await client.send_message(user.id, f"❌ <b>Payment Verification Declined</b>\n\n<blockquote>We were unable to verify your payment transaction. If you believe this is an error, please contact support.</blockquote>\n\n💬 <b>24/7 Support:</b> @{OWNER_USERNAME}")
        except:
            pass


    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton("➕ Add Me To Your Group", url=f'http://t.me/{temp.U_NAME}?startgroup=start', style=enums.ButtonStyle.PRIMARY)
        ],[
            InlineKeyboardButton('📢 Updates', url=UPDATES_LINK),
            InlineKeyboardButton('💬 Support', url=SUPPORT_LINK)
        ],[
            InlineKeyboardButton('💡 Help', callback_data='help'),
            InlineKeyboardButton('ℹ️ About', callback_data='about')
        ],[
            InlineKeyboardButton('💎 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium"),
            InlineKeyboardButton('🔍 Search Inline', switch_inline_query_current_chat=''),
        ],[
            InlineKeyboardButton('🎬 Popular Movies', url="https://www.themoviedb.org/movie"),
            InlineKeyboardButton('📺 Popular TV Shows', url="https://www.themoviedb.org/tv")
        ]]
        if URL:
            buttons.append([InlineKeyboardButton('🌐 Mini WebApp', style=enums.ButtonStyle.SUCCESS, web_app=WebAppInfo(url=URL))])
        reply_markup = InlineKeyboardMarkup(buttons)
        await safe_edit_media_caption(
            query,
            caption=script.START_TXT.format(query.from_user.mention, get_wish()),
            reply_markup=reply_markup
        )
        
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('📊 Status', callback_data='stats'),
            InlineKeyboardButton('📂 Source Code', callback_data='source')
        ],[
            InlineKeyboardButton('🧑‍💻 Bot Owner', callback_data='owner')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await safe_edit_media_caption(
            query,
            caption=script.MY_ABOUT_TXT,
            reply_markup=reply_markup
        )

    elif query.data == "stats":
        if query.from_user.id not in ADMINS:
            return await query.answer("🚫 Administrator Access Only!", show_alert=True)
        files = await db_count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        prm = await db.get_premium_count()
        used_files_db_size = get_size(await db.get_files_db_size())
        used_data_db_size = get_size(await db.get_data_db_size())

        if SECOND_FILES_DATABASE_URL:
            secnd_files_db_used_size = get_size(await db.get_second_files_db_size())
            secnd_files = await second_db_count_documents()
        else:
            secnd_files_db_used_size = '-'
            secnd_files = '-'
        uptime = get_readable_time(time_now() - temp.START_TIME)
        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='about')
        ]]
        await safe_edit_media_caption(
            query,
            caption=script.STATUS_TXT.format(users, prm, chats, used_data_db_size, files, used_files_db_size, secnd_files, secnd_files_db_used_size, uptime),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif query.data == "owner":
        buttons = [[InlineKeyboardButton('🔙 Back', callback_data='about')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await safe_edit_media_caption(
            query,
            caption=script.MY_OWNER_TXT,
            reply_markup=reply_markup
        )
        
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('💡 User Commands', callback_data='user_command'),
            InlineKeyboardButton('🛡️ Admin Commands', callback_data='admin_command')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await safe_edit_media_caption(
            query,
            caption=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup
        )

    elif query.data == "user_command":
        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await safe_edit_media_caption(
            query,
            caption=script.USER_COMMAND_TXT,
            reply_markup=reply_markup
        )
        
    elif query.data == "admin_command":
        if query.from_user.id not in ADMINS:
            return await query.answer("🚫 Administrator Access Only!", show_alert=True)
        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await safe_edit_media_caption(
            query,
            caption=script.ADMIN_COMMAND_TXT,
            reply_markup=reply_markup
        )

    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await safe_edit_media_caption(
            query,
            caption=script.SOURCE_TXT,
            reply_markup=reply_markup
        )
  
    elif query.data.startswith("bool_setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer("🚫 You must be an administrator in this group to use settings!", show_alert=True)
            return

        if status == "True":
            await save_group_settings(int(grp_id), set_type, False)
        else:
            await save_group_settings(int(grp_id), set_type, True)

        settings = await get_settings(int(grp_id))
        
        if set_type == 'shortlink':
            btn = [[
                InlineKeyboardButton(f'🔗 Shortlink {"✅" if settings["shortlink"] else "❌"}', callback_data=f'bool_setgs#shortlink#{settings["shortlink"]}#{grp_id}')
            ],[
                InlineKeyboardButton('✏️ Set Shortlink', callback_data=f'set_shortlink#{grp_id}'),
                InlineKeyboardButton('🔄 Default Shortlink', callback_data=f'default_shortlink#{grp_id}')
            ],[
                InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
            ]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))
            
        elif set_type == 'welcome':
            btn = [[
                InlineKeyboardButton(f'👋 Welcome {"✅" if settings["welcome"] else "❌"}', callback_data=f'bool_setgs#welcome#{settings["welcome"]}#{grp_id}')
            ],[
                InlineKeyboardButton('✏️ Set Welcome Text', callback_data=f'set_welcome#{grp_id}'),
                InlineKeyboardButton('🔄 Default Welcome', callback_data=f'default_welcome#{grp_id}')
            ],[
                InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
            ]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))

        elif set_type == 'imdb':
            btn = [[
                InlineKeyboardButton(f'🎬 IMDb Poster {"✅" if settings["imdb"] else "❌"}', callback_data=f'bool_setgs#imdb#{settings["imdb"]}#{grp_id}')
            ],[
                InlineKeyboardButton('✏️ Set IMDb Template', callback_data=f'set_imdb#{grp_id}'),
                InlineKeyboardButton('🔄 Default Template', callback_data=f'default_imdb#{grp_id}')
            ],[
                InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
            ]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))

        elif set_type == 'auto_delete':
            time_str = get_readable_time(settings.get("auto_delete_time", DELETE_TIME))
            btn = [[
                InlineKeyboardButton(f'⏰ Auto Delete {"✅" if settings["auto_delete"] else "❌"}', callback_data=f'bool_setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')
            ],[
                InlineKeyboardButton('✏️ Set Time', callback_data=f'set_auto_delete#{grp_id}'),
                InlineKeyboardButton('🔄 Default Time', callback_data=f'default_auto_delete#{grp_id}')
            ],[
                InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
            ]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))

        else:
            btn = [[
                InlineKeyboardButton(f'🔒 Protect Content {"✅" if settings.get("file_secure", False) else "❌"}', callback_data=f'bool_setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}')
            ],[
                InlineKeyboardButton(f'📝 Spelling Check {"✅" if settings["spell_check"] else "❌"}', callback_data=f'bool_setgs#spell_check#{settings["spell_check"]}#{grp_id}')
            ],[
                InlineKeyboardButton(f"🔗 Result Page: Link" if settings["links"] else "🔘 Result Page: Button", callback_data=f'bool_setgs#links#{settings["links"]}#{grp_id}')
            ],[
                InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
            ]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))

    elif query.data.startswith("shortlink_menu"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        settings = await get_settings(int(grp_id))
        btn = [[
            InlineKeyboardButton(f'🔗 Shortlink {"✅" if settings["shortlink"] else "❌"}', callback_data=f'bool_setgs#shortlink#{settings["shortlink"]}#{grp_id}')
        ],[
            InlineKeyboardButton('✏️ Set Shortlink', callback_data=f'set_shortlink#{grp_id}'),
            InlineKeyboardButton('🔄 Default Shortlink', callback_data=f'default_shortlink#{grp_id}')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
        ]]
        await query.message.edit(f'🔗 <b>Shortlink Settings Panel</b>\n\n🌐 <b>Current URL:</b> <code>{settings["url"]}</code>\n🔑 <b>Current API:</b> <code>{settings["api"]}</code>', reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("welcome_menu"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        settings = await get_settings(int(grp_id))
        btn = [[
            InlineKeyboardButton(f'👋 Welcome {"✅" if settings["welcome"] else "❌"}', callback_data=f'bool_setgs#welcome#{settings["welcome"]}#{grp_id}')
        ],[
            InlineKeyboardButton('✏️ Set Welcome Text', callback_data=f'set_welcome#{grp_id}'),
            InlineKeyboardButton('🔄 Default Welcome', callback_data=f'default_welcome#{grp_id}')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
        ]]
        await query.message.edit(f'👋 <b>Welcome Settings Panel</b>\n\n💬 <b>Current Welcome Text:</b>\n<blockquote><code>{settings["welcome_text"]}</code></blockquote>', reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("imdb_menu"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        settings = await get_settings(int(grp_id))
        btn = [[
            InlineKeyboardButton(f'🎬 IMDb Poster {"✅" if settings["imdb"] else "❌"}', callback_data=f'bool_setgs#imdb#{settings["imdb"]}#{grp_id}')
        ],[
            InlineKeyboardButton('✏️ Set IMDb Template', callback_data=f'set_imdb#{grp_id}'),
            InlineKeyboardButton('🔄 Default Template', callback_data=f'default_imdb#{grp_id}')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
        ]]
        await query.message.edit(f'🎬 <b>IMDb Settings Panel</b>\n\n📝 <b>Current Template:</b>\n<blockquote><code>{settings["template"]}</code></blockquote>', reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("caption_menu"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        settings = await get_settings(int(grp_id))
        btn = [[
            InlineKeyboardButton('✏️ Set Caption', callback_data=f'set_caption#{grp_id}'),
            InlineKeyboardButton('🔄 Default Caption', callback_data=f'default_caption#{grp_id}')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
        ]]
        await query.message.edit(f'📝 <b>Caption Settings Panel</b>\n\n🏷 <b>Current Caption:</b>\n<blockquote><code>{settings["caption"]}</code></blockquote>', reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("misc_menu"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        settings = await get_settings(int(grp_id))
        btn = [[
            InlineKeyboardButton(f'🔒 Protect Content {"✅" if settings.get("file_secure", False) else "❌"}', callback_data=f'bool_setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}')
        ],[
            InlineKeyboardButton(f'📝 Spelling Check {"✅" if settings["spell_check"] else "❌"}', callback_data=f'bool_setgs#spell_check#{settings["spell_check"]}#{grp_id}')
        ],[
            InlineKeyboardButton(f"🔗 Result Page: Link" if settings["links"] else "🔘 Result Page: Button", callback_data=f'bool_setgs#links#{settings["links"]}#{grp_id}')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
        ]]
        await query.message.edit(text="⚙️ <b>Miscellaneous Settings Panel</b>\n\nConfigure additional protection and display settings below:", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("auto_delete_menu"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        settings = await get_settings(int(grp_id))
        time_str = get_readable_time(settings.get("auto_delete_time", DELETE_TIME))
        btn = [[
            InlineKeyboardButton(f'⏰ Auto Delete {"✅" if settings["auto_delete"] else "❌"}', callback_data=f'bool_setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')
        ],[
            InlineKeyboardButton('✏️ Set Time', callback_data=f'set_auto_delete#{grp_id}'),
            InlineKeyboardButton('🔄 Default Time', callback_data=f'default_auto_delete#{grp_id}')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data=f'back_setgs#{grp_id}')
        ]]
        await query.message.edit(text=f"⏰ <b>Auto Delete Settings Panel</b>\n\n⏳ <b>Current Delete Timer:</b> <code>{time_str}</code>\n\nConfigure how long bot responses stay before auto-deleting:", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("set_imdb"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        m = await query.message.edit("✏️ <b>Set IMDb Template</b>\n\nPlease send your custom IMDb template formatting strings:")
        msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"imdb_menu#{grp_id}")
        ]]
        if not msg:
            await m.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
        await save_group_settings(int(grp_id), 'template', msg.text)
        await m.delete()
        await query.message.reply("✅ <b>IMDb Template Successfully Updated!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("default_imdb"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        await save_group_settings(int(grp_id), 'template', script.IMDB_TEMPLATE)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"imdb_menu#{grp_id}")
        ]]
        await query.message.edit("🔄 <b>IMDb Template Reset to Default Successfully!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("set_welcome"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        m = await query.message.edit("✏️ <b>Set Welcome Text</b>\n\nPlease send your custom welcome text formatting strings:")
        msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"welcome_menu#{grp_id}")
        ]]
        if not msg:
            await m.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
        await save_group_settings(int(grp_id), 'welcome_text', msg.text)
        await m.delete()
        await query.message.reply("✅ <b>Welcome Text Successfully Updated!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("default_welcome"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        await save_group_settings(int(grp_id), 'welcome_text', script.WELCOME_TEXT)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"welcome_menu#{grp_id}")
        ]]
        await query.message.edit("🔄 <b>Welcome Text Reset to Default Successfully!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("tutorial_setgs"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        settings = await get_settings(int(grp_id))
        btn = [[
            InlineKeyboardButton("✏️ Set Tutorial Link", callback_data=f"set_link_tutorial#{grp_id}"),
            InlineKeyboardButton("✏️ Set Tutorial Name", callback_data=f"set_name_tutorial#{grp_id}")
        ],[
            InlineKeyboardButton("🔄 Default Tutorial", callback_data=f"default_tutorial#{grp_id}")
        ],[
            InlineKeyboardButton("🔙 Back", callback_data=f"back_setgs#{grp_id}")
        ]]
        await query.message.edit(f'📖 <b>Tutorial Settings Panel</b>\n\n🔗 <b>Current Link:</b> <code>{settings.get("tutorial", TUTORIAL)}</code>\n🏷 <b>Button Name:</b> <code>{settings.get("tutorial_name", TUTORIAL_NAME)}</code>', reply_markup=InlineKeyboardMarkup(btn), link_preview_options=LinkPreviewOptions(is_disabled=True))
        
    elif query.data.startswith("set_link_tutorial"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        m = await query.message.edit("✏️ <b>Set Tutorial Link</b>\n\nPlease send your new tutorial URL (starting with http:// or https://):")
        msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"tutorial_setgs#{grp_id}")
        ]]
        if not msg:
            await m.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
            
        if not msg.text.startswith("http"):
            await m.delete()
            return await query.message.reply("⚠️ <b>Invalid URL Format!</b>\n\nMust start with <code>http://</code> or <code>https://</code>", reply_markup=InlineKeyboardMarkup(btn))
            
        await save_group_settings(int(grp_id), 'tutorial', msg.text)
        await m.delete()
        await query.message.reply("✅ <b>Tutorial Link Successfully Updated!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("set_name_tutorial"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        m = await query.message.edit("✏️ <b>Set Tutorial Button Name</b>\n\nPlease send your custom text for the tutorial button:")
        msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"tutorial_setgs#{grp_id}")
        ]]
        if not msg:
            await m.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
            
        await save_group_settings(int(grp_id), 'tutorial_name', msg.text)
        await m.delete()
        await query.message.reply("✅ <b>Tutorial Button Name Successfully Updated!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("set_auto_delete"):
        import re
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        m = await query.message.edit("✏️ <b>Set Auto Delete Time</b>\n\nPlease send the auto delete timer value (e.g. <code>1m</code>, <code>1h</code>, <code>1d</code>):")
        msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"auto_delete_menu#{grp_id}")
        ]]
        if not msg:
            await m.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
        
        match = re.match(r"^(\d+)([smhd])$", msg.text.strip().lower())
        if not match:
            await m.delete()
            return await query.message.reply("⚠️ <b>Invalid Timer Format!</b>\n\nPlease use formats like <code>30s</code>, <code>5m</code>, <code>1h</code>, or <code>1d</code>.", reply_markup=InlineKeyboardMarkup(btn))
            
        val = int(match.group(1))
        unit = match.group(2)
        multiplier = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]
        seconds = val * multiplier
        
        await save_group_settings(int(grp_id), 'auto_delete_time', seconds)
        await m.delete()
        await query.message.reply(f"✅ <b>Auto Delete Timer Successfully Changed to:</b> <code>{val}{unit}</code>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("default_auto_delete"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        await save_group_settings(int(grp_id), 'auto_delete_time', DELETE_TIME)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"auto_delete_menu#{grp_id}")
        ]]
        await query.message.edit("🔄 <b>Auto Delete Timer Reset to Default Successfully!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("default_tutorial"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        await save_group_settings(int(grp_id), 'tutorial', TUTORIAL)
        await save_group_settings(int(grp_id), 'tutorial_name', TUTORIAL_NAME)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"tutorial_setgs#{grp_id}")
        ]]
        await query.message.edit("🔄 <b>Tutorial Settings Reset to Default Successfully!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("set_shortlink"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"shortlink_menu#{grp_id}")
        ]]
        m = await query.message.edit("✏️ <b>Set Shortlink URL</b>\n\nPlease send your shortlink domain (starting with http:// or https://):")
        url_msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        if not url_msg:
            await m.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
            
        if not url_msg.text.startswith("http"):
            await m.delete()
            return await query.message.reply("⚠️ <b>Invalid URL Format!</b>\n\nMust start with <code>http://</code> or <code>https://</code>", reply_markup=InlineKeyboardMarkup(btn))
            
        m2 = await query.message.reply("🔗 <b>URL Received!</b>\n\nNow send your shortlink API key:")
        api_msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        if not api_msg:
            await m2.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
            
        await save_group_settings(int(grp_id), 'url', url_msg.text)
        await save_group_settings(int(grp_id), 'api', api_msg.text)
        await m.delete()
        await m2.delete()
        await query.message.reply("✅ <b>Shortlink URL and API Key Successfully Updated!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("default_shortlink"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        await save_group_settings(int(grp_id), 'url', SHORTLINK_URL)
        await save_group_settings(int(grp_id), 'api', SHORTLINK_API)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"shortlink_menu#{grp_id}")
        ]]
        await query.message.edit("🔄 <b>Shortlink Reset to Default Successfully!</b>", reply_markup=InlineKeyboardMarkup(btn))
        
    elif query.data.startswith("set_caption"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        m = await query.message.edit("✏️ <b>Set Custom Caption</b>\n\nPlease send your new file caption formatting string:")
        msg = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"caption_menu#{grp_id}")
        ]]
        if not msg:
            await m.delete()
            return await query.message.reply("⏳ <b>Operation Timed Out!</b>", reply_markup=InlineKeyboardMarkup(btn))
        await save_group_settings(int(grp_id), 'caption', msg.text)
        await m.delete()
        await query.message.reply("✅ <b>File Caption Successfully Updated!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("default_caption"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        await save_group_settings(int(grp_id), 'caption', script.FILE_CAPTION)
        btn = [[
            InlineKeyboardButton("🔙 Back", callback_data=f"caption_menu#{grp_id}")
        ]]
        await query.message.edit("🔄 <b>File Caption Reset to Default Successfully!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("back_setgs"):
        _, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        btn = await get_grp_stg(int(grp_id))
        chat = await client.get_chat(int(grp_id))
        await query.message.edit(text=f"⚙️ <b>Group Settings Panel</b>\n\nModify your configurations for <b>{chat.title}</b> below:", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data == "open_group_settings":
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, query.message.chat.id, userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        btn = await get_grp_stg(query.message.chat.id)
        await query.message.edit(text=f"⚙️ <b>Group Settings Panel</b>\n\nModify your configurations for <b>{query.message.chat.title}</b> below:", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data == "open_pm_settings":
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, query.message.chat.id, userid):
            return await query.answer("⚠️ You must be an admin in this group to use settings!", show_alert=True)
        btn = await get_grp_stg(query.message.chat.id)
        try:
            await client.send_message(query.from_user.id, f"⚙️ <b>Group Settings Panel</b>\n\nModify your configurations for <b>{query.message.chat.title}</b> below:", reply_markup=InlineKeyboardMarkup(btn))
        except:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start=settings_{query.message.chat.id}")
        btn = [[
            InlineKeyboardButton("💬 Go To PM", url=f"https://t.me/{temp.U_NAME}")
        ]]
        await query.message.edit("💬 <b>Settings panel has been dispatched to your Private Messages!</b>", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("delete"):
        _, query_ = query.data.split("_", 1)
        await query.message.edit("🗑️ <b>Deleting matching files from database...</b>")
        deleted = await delete_files(query_)
        await query.message.edit(f"✅ <b>Database Cleaned!</b>\n\nSuccessfully deleted <code>{deleted}</code> files matching query: <code>{query_}</code>.")
     
    elif query.data.startswith("send_all"):
        ident, key, req = query.data.split("#")
        if int(req) != query.from_user.id:
            return await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThese results are not for you! Please search for your own movie/series.", show_alert=True)        
        files = temp.GET_ALL_FILES.get(key)
        if not files:
            await query.answer(f"⚠️ Hello {query.from_user.first_name},\nThis batch delivery link has expired. Please send your request again!", show_alert=True)
            return        
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}")

    elif query.data == "unmute_all_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("⚠️ You do not have administrator permissions to perform this action!", show_alert=True)
            return
        users_id = []
        await query.message.edit("🔄 <b>Unmuting All Members...</b>\n\n<blockquote>⏳ Please wait, this operation may take several minutes depending on group size.</blockquote>")
        try:
            async for member in client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.RESTRICTED):
                users_id.append(member.user.id)
            for user_id in users_id:
                await client.unban_chat_member(query.message.chat.id, user_id)
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f"❌ <b>Operation Failed!</b>\n\n<blockquote>⚠️ Error details: <code>{e}</code></blockquote>")
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"✅ <b>Action Completed!</b>\n\nSuccessfully unmuted <code>{len(users_id)}</code> restricted users.")
        else:
            await query.message.reply("ℹ️ <b>No Restricted Users Found!</b>\n\nThere are currently no muted members in this group.")

    elif query.data == "unban_all_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("⚠️ You do not have administrator permissions to perform this action!", show_alert=True)
            return
        users_id = []
        await query.message.edit("🔄 <b>Unbanning All Members...</b>\n\n<blockquote>⏳ Please wait while we process the group ban list.</blockquote>")
        try:
            async for member in client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.BANNED):
                users_id.append(member.user.id)
            for user_id in users_id:
                await client.unban_chat_member(query.message.chat.id, user_id)
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f"❌ <b>Operation Failed!</b>\n\n<blockquote>⚠️ Error details: <code>{e}</code></blockquote>")
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"✅ <b>Action Completed!</b>\n\nSuccessfully unbanned <code>{len(users_id)}</code> users.")
        else:
            await query.message.reply("ℹ️ <b>No Banned Users Found!</b>\n\nThere are currently no banned members in this group.")

    elif query.data == "kick_muted_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("⚠️ You do not have administrator permissions to perform this action!", show_alert=True)
            return
        users_id = []
        await query.message.edit("🔄 <b>Kicking Muted Members...</b>\n\n<blockquote>⏳ Please wait while restricted members are removed from the chat.</blockquote>")
        try:
            async for member in client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.RESTRICTED):
                users_id.append(member.user.id)
            for user_id in users_id:
                await client.ban_chat_member(query.message.chat.id, user_id, datetime.now() + timedelta(seconds=30))
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f"❌ <b>Operation Failed!</b>\n\n<blockquote>⚠️ Error details: <code>{e}</code></blockquote>")
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"✅ <b>Action Completed!</b>\n\nSuccessfully kicked <code>{len(users_id)}</code> muted members.")
        else:
            await query.message.reply("ℹ️ <b>No Muted Users Found!</b>\n\nThere are no muted members to remove.")

    elif query.data == "kick_deleted_accounts_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("⚠️ You do not have administrator permissions to perform this action!", show_alert=True)
            return
        users_id = []
        await query.message.edit("🔄 <b>Scanning & Kicking Deleted Accounts...</b>\n\n<blockquote>⏳ Please wait while we clean up ghost accounts from the member list.</blockquote>")
        try:
            async for member in client.get_chat_members(query.message.chat.id):
                if member.user.is_deleted:
                    users_id.append(member.user.id)
            for user_id in users_id:
                await client.ban_chat_member(query.message.chat.id, user_id, datetime.now() + timedelta(seconds=30))
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f"❌ <b>Operation Failed!</b>\n\n<blockquote>⚠️ Error details: <code>{e}</code></blockquote>")
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"✅ <b>Action Completed!</b>\n\nSuccessfully removed <code>{len(users_id)}</code> deleted accounts from the chat.")
        else:
            await query.message.reply("ℹ️ <b>Clean Chat!</b>\n\nNo deleted accounts were found in this group.")



async def auto_filter(client, msg, s, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        search = re.sub(r"\s+", " ", re.sub(r"[-:\"';!]", " ", message.text)).strip()
        cache_key = search.lower()
        if cache_key in QUERY_CACHE:
            files = QUERY_CACHE[cache_key]
        else:
            files = await get_search_results(search)
            QUERY_CACHE[cache_key] = files
        if not files:
            if settings["spell_check"]:
                await advantage_spell_chok(message, s)
            else:
                await s.edit(f'🥲 <b>Title Not Found!</b>\n\n<blockquote>We could not locate <code>{search}</code> in our database or via Google suggestions.</blockquote>')
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files = spoll
        cache_key = search.lower()
        if cache_key not in QUERY_CACHE:
            QUERY_CACHE[cache_key] = files
    
    key = f"{message.chat.id}-{message.id}"
    FILES[key] = files
    ALL_FILES[key] = files
    files, offset, total_results = await handle_next_back(files, max_results=MAX_BTN)

    req = message.from_user.id if message and message.from_user else 0
    BUTTONS[key] = search
    temp.GET_ALL_FILES[key] = files
    SELECT[key] = {'lang': 'any', 'qual': 'any', 'season': 'any', 'episode': 'any'}

    files_link = ""
    if settings['links'] and message.chat.type != enums.ChatType.PRIVATE:
        btn = []
        for file_num, file in enumerate(files, start=1):
            files_link += f"""<b>\n\n{file_num}. <a href="https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file['_id']}">[{get_size(file['file_size'])}] {file['file_name']}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"{get_size(file['file_size'])} - {file['file_name']}", callback_data=f'file#{file["_id"]}')
        ]
            for file in files
        ]   

    if offset != 0:
        btn.append(
            [InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton(text="⏭️ Next", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton("🚫 No More Pages", callback_data="buttons")]
        )
    
    btn.insert(0,
                [InlineKeyboardButton("🌐 Language", callback_data=f"languages#{key}#{req}#{offset}"),
                InlineKeyboardButton("💎 Quality", callback_data=f"quality#{key}#{req}#{offset}")]
            )
    btn.insert(1,
                [InlineKeyboardButton("📁 Season", callback_data=f"season#{key}#{req}#{offset}"),
                InlineKeyboardButton("🎬 Episode", callback_data=f"episode#{key}#{req}#{offset}")]
            )

    if settings['shortlink'] and not await is_premium(message.from_user.id, client):
        btn.insert(2,
            [InlineKeyboardButton("⚡ Send All", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{message.chat.id}_{key}')),
             InlineKeyboardButton(settings['tutorial_name'], url=settings['tutorial'])]
        )
    else:
        btn.insert(2,
            [InlineKeyboardButton("⚡ Send All", callback_data=f"send_all#{key}#{req}"),
             InlineKeyboardButton(settings['tutorial_name'], url=settings['tutorial'])]
        )
    btn.append(
        [InlineKeyboardButton('💎 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")]
    )

    imdb = await get_poster(search) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            kind=imdb['kind'],
            votes=imdb['votes'],
            tmdb_id=imdb["tmdb_id"],
            runtime=imdb["runtime"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            languages=imdb['languages'],
            countries=imdb['countries'],
            mention=message.from_user.mention,
            group_title=message.chat.title,
        )
    else:
        cap = f"<b>💭 Hello {message.from_user.mention},\n♻️ here i found for your search {search}...</b>"
    CAP[key] = cap
    auto_del_time = settings.get("auto_delete_time", DELETE_TIME)
    del_msg = f"\n\n<b>⚠️ this message will be auto delete after <code>{get_readable_time(auto_del_time)}</code> to avoid copyright issues</b>" if settings["auto_delete"] else ''
    if imdb and imdb.get('poster'):
        await s.delete()
        try:
            k = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML, reply_parameters=ReplyParameters(message_id=message.id))
            if settings["auto_delete"]:
                await asyncio.sleep(auto_del_time)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
        except Exception as e:
            k = await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), link_preview_options=LinkPreviewOptions(is_disabled=True), parse_mode=enums.ParseMode.HTML, reply_parameters=ReplyParameters(message_id=message.id))
            if settings["auto_delete"]:
                await asyncio.sleep(auto_del_time)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
    else:
        k = await s.edit_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), link_preview_options=LinkPreviewOptions(is_disabled=True), parse_mode=enums.ParseMode.HTML)
        if settings["auto_delete"]:
            await asyncio.sleep(auto_del_time)
            await k.delete()
            try:
                await message.delete()
            except:
                pass

async def advantage_spell_chok(message, s):
    search = message.text
    btn = [[
        InlineKeyboardButton("💡 Instructions", callback_data='instructions'),
        InlineKeyboardButton("🌐 Search Google", url=f"https://www.google.com/search?q={quote(search)}")
    ]]
    try:
        movies = await get_imdb_suggestions(search)
    except:
        n = await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return
    if not movies:
        n = await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return

    user = message.from_user.id if message.from_user else 0
    
    buttons = []
    for movie in movies:
        temp.SPELL_CHECK[movie['id']] = movie['title']
        buttons.append([InlineKeyboardButton(text=f"🎬 {movie['title']}", callback_data=f"spolling#{movie['id']}#{user}")])
    buttons.append(
        [InlineKeyboardButton("✖️ Close", callback_data="close_data")]
    )
    s = await s.edit_text(text=f"👋 <b>Hello {message.from_user.mention},</b>\n\n<blockquote>🥲 I couldn't find exactly <b>{search}</b> in our current database!</blockquote>\n\n💡 <b>Did you mean one of these titles below?</b> 👇", reply_markup=InlineKeyboardMarkup(buttons))
    await asyncio.sleep(300)
    await s.delete()
    try:
        await message.delete()
    except:
        pass

