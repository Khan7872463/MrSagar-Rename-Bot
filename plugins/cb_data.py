from helper.progress import progress_for_pyrogram
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.database import find, find_one, dateupdate, used_limit
from helper.ffmpeg import take_screen_shot, fix_thumb
from helper.progress import humanbytes, escape_invalid_curly_brackets
from PIL import Image
import os
import random
import time
from datetime import timedelta

log_channel = int(os.environ.get("LOG_CHANNEL", ""))
API_ID = int(os.environ.get("API_ID", ""))
API_HASH = os.environ.get("API_HASH", "")
STRING = os.environ.get("STRING", "")

app = Client("test", api_id=API_ID, api_hash=API_HASH, session_string=STRING)


def get_caption(data, filename, file_size, duration=None):
    if data:
        caption_list = ["filename", "filesize", "duration"] if duration else ["filename", "filesize"]
        new_text = escape_invalid_curly_brackets(data[1], caption_list)
        caption = new_text.format(filename=filename, filesize=humanbytes(file_size), duration=timedelta(seconds=duration) if duration else "")
    else:
        caption = f"**{filename}**"
    return caption


async def download_and_upload(bot, update, file_type):
    new_name = update.message.text
    used_data = find_one(update.from_user.id)
    used, date = used_data["used_limit"], used_data["date"]

    name = new_name.split(":-")
    new_filename = name[1]

    file_path = f"downloads/{new_filename}"

    message = update.message.reply_to_message
    file = message.document or message.video or message.audio

    ms = await update.message.edit(f"Trying To Download {file_type.capitalize()}...")

    used_limit(update.from_user.id, file.file_size)
    c_time = time.time()
    total_used = used + int(file.file_size)
    used_limit(update.from_user.id, total_used)

    try:
        path = await bot.download_media(message=file, progress=progress_for_pyrogram,
                                        progress_args=("Trying To Download...", ms, c_time))
    except Exception as e:
        neg_used = used - int(file.file_size)
        used_limit(update.from_user.id, neg_used)
        await ms.edit(e)
        return

    split_path = path.split("/downloads/")
    dow_file_name = split_path[1]
    old_file_name = f"downloads/{dow_file_name}"
    os.rename(old_file_name, file_path)

    user_id = int(update.message.chat.id)
    data = find(user_id)

    try:
        c_caption = data[1]
    except:
        pass

    thumb = data[0]

    if thumb:
        ph_path = await bot.download_media(thumb)
        Image.open(ph_path).convert("RGB").save(ph_path)
        img = Image.open(ph_path)
        img.resize((320, 320))
        img.save(ph_path, "JPEG")
        c_time = time.time()
    else:
        ph_path = None

    return file_path, c_caption, ph_path, used, ms, c_time


@Client.on_callback_query(filters.regex('cancel'))
async def cancel(bot, update):
    try:
        await update.message.delete()
    except:
        return


@Client.on_callback_query(filters.regex('rename'))
async def rename(bot, update):
    date_fa = str(update.message.date)
    pattern = '%Y-%m-%d %H:%M:%S'
    date = int(time.mktime(time.strptime(date_fa, pattern)))
    chat_id = update.message.chat.id
    id = update.message.reply_to_message_id
    await update.message.delete()
    await update.message.reply_text(f"**Please Enter The New Filename...\n\nNote - Extension Not Required.**",
                                   reply_to_message_id=id,
                                   reply_markup=ForceReply(True))
    dateupdate(chat_id, date)


@Client.on_callback_query(filters.regex("doc"))
async def doc(bot, update):
    file_path, c_caption, ph_path, used, ms, c_time = await download_and_upload(bot, update, "document")

    try:
        await bot.send_document(update.from_user.id, document=file_path, thumb=ph_path, caption=caption,
                                progress=progress_for_pyrogram, progress_args=("Trying To Uploading", ms, c_time))
        await ms.delete()
        os.remove(file_path)
        try:
            os.remove(ph_path)
        except:
            pass
    except Exception as e:
        neg_used = used - int(file.file_size)
        used_limit(update.from_user.id, neg_used)
        await ms.edit(e)
        os.remove(file_path)
        try:
            os.remove(ph_path)
        except:
            return


@Client.on_callback_query(filters.regex("vid"))
async def vid(bot, update):
    file_path, c_caption, ph_path, used, ms, c_time = await download_and_upload(bot, update, "video")

    duration = 0
    metadata = extractMetadata(createParser(file_path))
    if metadata.has("duration"):
        duration = metadata.get('duration').seconds

    caption = get_caption(data, new_filename, file.file_size, duration)

    try:
        await bot.send_video(update.from_user.id, video=file_path, thumb=ph_path, duration=duration, caption=caption,
                             progress=progress_for_pyrogram, progress_args=("Trying To Uploading", ms, c_time))
        await ms.delete()
        os.remove(file_path)
        try:
            os.remove(ph_path)
        except:
            pass
    except Exception as e:
        neg_used = used - int(file.file_size)
        used_limit(update.from_user.id, neg_used)
        await ms.edit(e)
        os.remove(file_path)
        try:
            os.remove(ph_path)
        except:
            return


@Client.on_callback_query(filters.regex("aud"))
async def aud(bot, update):
    file_path, c_caption, ph_path, used, ms, c_time = await download_and_upload(bot, update, "audio")

    duration = 0
    metadata = extractMetadata(createParser(file_path))
    if metadata.has("duration"):
        duration = metadata.get('duration').seconds

    caption = get_caption(data, new_filename, file.file_size, duration)

    try:
        await bot.send_audio(update.message.chat.id, audio=file_path, caption=caption, thumb=ph_path, duration=duration,
                              progress=progress_for_pyrogram, progress_args=("Trying To Uploading", ms, c_time))
        await ms.delete()
        os.remove(file_path)
        try:
            os.remove(ph_path)
        except:
            pass
    except Exception as e:
        await ms.edit(e)
        neg_used = used - int(file.file_size)
        used_limit(update.from_user.id, neg_used)
        os.remove(file_path)
