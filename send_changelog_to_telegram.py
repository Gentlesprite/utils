# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-10-24 14:21:49
# File:send_changelog_to_telegram.py
import os
import re
import sys
import hashlib
import asyncio
import argparse

import pyrogram
from pyrogram import raw, utils, types
from pyrogram.types import InputRichMessage
from pyrogram.errors import FloodWait

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

SCRIPT_PARSER = argparse.ArgumentParser(description='发送release note到Telegram会话。')
SCRIPT_PARSER.add_argument('-c', '--chat', required=True, help='接收release note的会话,支持@用户名或数字id。')
SCRIPT_PARSER.add_argument('-n', '--note', default='',
                           help='release note文件路径,默认为release目录内最新版本的release_note.md。')
SCRIPT_PARSER.add_argument('-u', '--upload', action='store_true',
                           help='先将output下所有.rar作为相册上传发送,再用富文本release note回复到该相册下方。')
SCRIPT_PARSER.add_argument('-b', '--bot_token', required=False, default='', type=str, help='自定义bot_token')
SCRIPT_ARGS = SCRIPT_PARSER.parse_args()
sys.argv = [os.path.join(PROJECT_ROOT, 'main.py'), '-q']

try:
    from module import (
        console,
        SOFTWARE_FULL_NAME
    )
    from module.enums import (
        UploadStatus,
        BotButton
    )
    from module.remote import rc
    from module.app import Application
    from module.task import UploadTask
    from module.config import UserConfig
except ImportError as e:
    print(f'缺少必要环境,原因:"{e}"。')
    sys.exit(-1)

RELEASE_DIRECTORY = os.path.join(PROJECT_ROOT, 'release')
OUTPUT_DIRECTORY = os.path.join(PROJECT_ROOT, 'output')
NOTE_FILE_NAME = 'release_note.md'
VERSION_DIRECTORY_PATTERN = re.compile(r'^v(\d+)\.(\d+)\.(\d+)$')


def get_latest_note_path() -> str:
    latest_version: tuple = ()
    latest_note_path: str = ''
    if not os.path.isdir(RELEASE_DIRECTORY):
        return latest_note_path
    for directory_name in os.listdir(RELEASE_DIRECTORY):
        version_match = VERSION_DIRECTORY_PATTERN.match(directory_name)
        if version_match is None:
            continue
        note_path = os.path.join(RELEASE_DIRECTORY, directory_name, NOTE_FILE_NAME)
        if not os.path.isfile(note_path):
            continue
        version_tuple = tuple(map(int, version_match.groups()))
        if version_tuple > latest_version:
            latest_version = version_tuple
            latest_note_path = note_path
    return latest_note_path


def build_bot_client(user_config: UserConfig) -> pyrogram.Client:
    return pyrogram.Client(
        name=SOFTWARE_FULL_NAME.replace(' ', ''),
        api_id=user_config.api_id,
        api_hash=user_config.api_hash,
        bot_token=SCRIPT_ARGS.bot_token or user_config.bot_token,
        proxy=user_config.proxy if user_config.enable_proxy else None,
        in_memory=True,
        workdir=user_config.work_directory,
        app_version=Application.APP_VERSION,
        device_model=Application.DEVICE_MODEL
    )


def get_rar_paths() -> list:
    if not os.path.isdir(OUTPUT_DIRECTORY):
        return []
    return sorted(
        os.path.join(OUTPUT_DIRECTORY, name)
        for name in os.listdir(OUTPUT_DIRECTORY)
        if name.lower().endswith('.rar') and os.path.isfile(os.path.join(OUTPUT_DIRECTORY, name))
    )


def resolve_chat_id(chat: str) -> int | str:
    if isinstance(chat, str) and chat.lstrip('-').isdigit():
        return int(chat)
    return chat


def read_changelog() -> str:
    note_path: str = SCRIPT_ARGS.note or get_latest_note_path()
    if note_path and not os.path.isabs(note_path):
        note_path = os.path.join(PROJECT_ROOT, note_path)
    if not note_path or not os.path.isfile(note_path):
        console.log(f'未找到release note文件:"{note_path or RELEASE_DIRECTORY}",请用-n参数指定路径。', style='#FF4689')
        return ''
    with open(file=note_path, mode='r', encoding='UTF-8') as file:
        return file.read()


def dedent_markdown_tables(text: str) -> str:
    def is_table_row(line: str) -> bool:
        content = line.strip()
        return content.startswith('|') and content.endswith('|') and content.count('|') >= 2

    result = []
    in_table = False
    for line in text.split('\n'):
        if is_table_row(line):
            if not in_table:
                if result and result[-1].strip() != '':
                    result.append('')  # 表格前补空行,避免被并进上一段落。
                in_table = True
            result.append(line.strip())
        else:
            if in_table:
                if line.strip() != '':
                    result.append('')  # 表格后补空行,干净结束表格块。
                in_table = False
            result.append(line)
    return '\n'.join(result)


async def send_changelog_text(
        client: pyrogram.Client,
        chat_id,
        changelog: str,
        reply_to_message_id: int | None = None
) -> pyrogram.types.Message | None:
    console.log(f'正在发送release note到"{SCRIPT_ARGS.chat}"...')
    message: pyrogram.types.Message | None = None
    reply_parameters = pyrogram.types.ReplyParameters(message_id=reply_to_message_id) if reply_to_message_id else None
    config = rc.cached_config()
    while True:
        try:
            message = await client.send_rich_message(
                chat_id=chat_id,
                rich_message=InputRichMessage(markdown=dedent_markdown_tables(changelog), skip_entity_detection=True),
                reply_parameters=reply_parameters,
                reply_markup=types.InlineKeyboardMarkup(
                    [
                        [
                            types.InlineKeyboardButton(
                                text=BotButton.PAY,
                                url='https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/pay.png',
                                style=pyrogram.enums.ButtonStyle.SUCCESS
                            ),
                            types.InlineKeyboardButton(
                                text=BotButton.PROXY_SELLER,
                                url=config.get('proxy_seller', rc.DEFAULT_PROXY_SELLER),
                                style=pyrogram.enums.ButtonStyle.DANGER
                            )
                        ],
                        [
                            types.InlineKeyboardButton(
                                text=BotButton.GITHUB,
                                url=config.get('github', rc.DEFAULT_GITHUB) + '/releases',
                                style=pyrogram.enums.ButtonStyle.DEFAULT),
                            types.InlineKeyboardButton(
                                text=BotButton.VIDEO_TUTORIAL,
                                url=config.get('video_tutorial', rc.DEFAULT_VIDEO_TUTORIAL),
                                style=pyrogram.enums.ButtonStyle.PRIMARY
                            )
                        ],

                    ]
                )
            )
        except FloodWait as e:
            console.log(f'发送请求频繁,需等待{e.value}秒后重试。', style='#FF4689')
            await asyncio.sleep(e.value)
            continue
        break
    console.log(f'已将release note发送至"{SCRIPT_ARGS.chat}"。', style='#B1DB74')
    return message


async def get_input_media_document(
        client: pyrogram.Client,
        chat_id,
        file,
        attributes: list,
        mime_type: str
) -> raw.types.InputMediaDocument:
    media = raw.types.InputMediaUploadedDocument(
        mime_type=mime_type,
        file=file,
        attributes=attributes,
        force_file=False,
        thumb=None
    )
    media = await client.invoke(
        raw.functions.messages.UploadMedia(
            peer=await client.resolve_peer(chat_id),
            media=media
        )
    )
    return raw.types.InputMediaDocument(
        id=raw.types.InputDocument(
            id=media.document.id,
            access_hash=media.document.access_hash,
            file_reference=media.document.file_reference
        )
    )


async def upload_file_with_cache(client: pyrogram.Client, chat_id, path: str):
    file_size: int = os.path.getsize(path)
    if file_size == 0:
        console.log(f'文件大小为0,跳过上传:"{path}"', style='#FF4689')
        return None
    task = UploadTask(
        chat_id=None,
        file_path=path,
        file_id=client.rnd_id(),
        file_size=file_size,
        file_part=[],
        status=UploadStatus.PENDING
    )
    task.chat_id = chat_id  # 赋值chat_id会触发load_json,恢复缓存里的file_id与已传分片。
    for part in task.get_missing_parts():
        while True:
            try:
                await client.save_file(path=path, file_id=task.file_id, file_part=part)
                break
            except FloodWait as e:
                console.log(f'上传"{os.path.basename(path)}"分片遇频率限制,等待{e.value}秒后重试。', style='#FF4689')
                await asyncio.sleep(e.value)
        task.update_file_part(part)
    file_name: str = os.path.basename(path)
    if file_size > 10 * 1024 * 1024:
        file = raw.types.InputFileBig(id=task.file_id, parts=task.file_total_parts, name=file_name)
    else:
        md5_hash = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5_hash.update(chunk)
        md5_sum = ''.join(hex(i)[2:].zfill(2) for i in md5_hash.digest())
        file = raw.types.InputFile(id=task.file_id, parts=task.file_total_parts, name=file_name, md5_checksum=md5_sum)
    mime_type = client.guess_mime_type(path) or 'application/octet-stream'
    attributes = [raw.types.DocumentAttributeFilename(file_name=file_name)]
    return await get_input_media_document(client, chat_id, file, attributes, mime_type)


async def upload_rar_media(client: pyrogram.Client, chat_id) -> pyrogram.types.Message | None:
    rar_paths = get_rar_paths()
    if not rar_paths:
        console.log(f'未在"{OUTPUT_DIRECTORY}"下找到任何.rar文件,跳过上传。', style='#FF4689')
        return None
    UploadTask.DIRECTORY_NAME = os.path.join(UploadTask.DIRECTORY_NAME, str(client.me.id))
    client.save_file_semaphore = asyncio.Semaphore(1)
    console.log(f'正在上传{len(rar_paths)}个.rar文件到"{SCRIPT_ARGS.chat}"...')
    documents = []
    for path in rar_paths:
        media = await upload_file_with_cache(client, chat_id, path)
        if media is not None:
            documents.append(media)
    if not documents:
        console.log('没有可上传的.rar文件。', style='#FF4689')
        return None
    multi_media = [
        raw.types.InputSingleMedia(media=media, random_id=client.rnd_id(), message='')
        for media in documents
    ]
    peer = await client.resolve_peer(chat_id)
    result = None
    while True:
        try:
            result = await client.invoke(
                raw.functions.messages.SendMultiMedia(peer=peer, multi_media=multi_media),
                sleep_threshold=60
            )
        except FloodWait as e:
            console.log(f'发送请求频繁,需等待{e.value}秒后重试。', style='#FF4689')
            await asyncio.sleep(e.value)
            continue
        break
    messages = await utils.parse_messages(client, result)
    album_message: pyrogram.types.Message | None = messages[0] if messages else None
    console.log(f'已上传{len(documents)}个.rar文件至"{SCRIPT_ARGS.chat}"。', style='#B1DB74')
    return album_message


async def send_release() -> None:
    user_config = UserConfig()
    if not user_config.api_id or not user_config.api_hash:
        console.log('配置文件中未填写api_id或api_hash,无法发送。', style='#FF4689')
        return
    chat_id = resolve_chat_id(SCRIPT_ARGS.chat)
    client = build_bot_client(user_config)
    await client.start()
    try:
        album_message = await upload_rar_media(client, chat_id)
        changelog = read_changelog()
        if changelog:
            await send_changelog_text(
                client, chat_id, changelog,
                reply_to_message_id=album_message.id if album_message else None
            )
    finally:
        await client.stop()


async def send_changelog() -> None:
    user_config = UserConfig()
    if not user_config.api_id or not user_config.api_hash:
        console.log('配置文件中未填写api_id或api_hash,无法发送release note。', style='#FF4689')
        return
    if not user_config.bot_token:
        console.log('配置文件中未填写bot_token,无法通过机器人发送富文本release note。', style='#FF4689')
        return
    changelog = read_changelog()
    if not changelog:
        return
    client = build_bot_client(user_config)
    await client.start()
    try:
        await send_changelog_text(client, resolve_chat_id(SCRIPT_ARGS.chat), changelog)
    finally:
        await client.stop()


if __name__ == '__main__':
    if SCRIPT_ARGS.upload:
        asyncio.run(send_release())
    else:
        asyncio.run(send_changelog())
