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
from dataclasses import (
    dataclass,
    field
)
from typing import (
    Union,
    Optional
)

import pyrogram
from pyrogram import raw, utils, types
from pyrogram.types import InputRichMessage
from pyrogram.errors import (
    FloodWait,
    FilePartMissing,
    FilePartLengthInvalid
)

from utils import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

sys.argv = [os.path.join(PROJECT_ROOT, 'main.py'), '--quiet']

try:
    from module.remote import rc  # noqa.
    from module.task import UploadTask  # noqa.
    from detect_system_proxy import resolve_proxy  # noqa.
except ImportError as e:
    print(f'缺少必要环境,原因:"{e}"。')
    sys.exit(-1)

RELEASE_DIRECTORY = os.path.join(PROJECT_ROOT, 'release')
OUTPUT_DIRECTORY = os.path.join(PROJECT_ROOT, 'output')
NOTE_FILE_NAME = 'release_note.md'
VERSION_DIRECTORY_PATTERN = re.compile(r'^v(\d+)\.(\d+)\.(\d+)$')


class UploadStatus:
    PENDING = 'pending'
    UPLOADING = 'uploading'
    SUCCESS = 'success'
    FAILURE = 'failure'
    SENT = 'sent'


class BotButton:
    GITHUB: str = '📦GitHub'
    SUBSCRIBE_CHANNEL: str = '📌订阅频道'
    VIDEO_TUTORIAL: str = '🎬视频教程'
    PROXY_SELLER: str = '🛒购买代理'
    PAY: str = '💰支持作者'


@dataclass
class TelegramConfig:
    api_id: Union[int, str]
    api_hash: str
    bot_token: str
    name: Optional[str]
    work_directory: Optional[str]
    enable_proxy: Optional[bool]
    proxy: Optional[str] = field(default_factory=resolve_proxy)


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


def get_client(telegram_config: TelegramConfig) -> pyrogram.Client:
    return pyrogram.Client(
        name=telegram_config.name,
        api_id=telegram_config.api_id,
        api_hash=telegram_config.api_hash,
        bot_token=telegram_config.bot_token,
        proxy=telegram_config.proxy if telegram_config.enable_proxy else None,
        in_memory=True,
        workdir=telegram_config.work_directory
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


def read_changelog(release_note_path: Optional[str]) -> str:
    release_note_path: str = release_note_path or get_latest_note_path()
    if release_note_path and not os.path.isabs(release_note_path):
        release_note_path = os.path.join(PROJECT_ROOT, release_note_path)
    if not release_note_path or not os.path.isfile(release_note_path):
        logging.warning(f'未找到release note文件:"{release_note_path or RELEASE_DIRECTORY}"。')
        return ''
    with open(file=release_note_path, mode='r', encoding='UTF-8') as file:
        return file.read()


def dedent_markdown_tables(text: str) -> str:
    def is_table_row(_line: str) -> bool:
        content = _line.strip()
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
    logging.info(f'正在发送release note到"{chat_id}"。')
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
        except FloodWait as _e:
            logging.info(f'发送请求频繁,需等待{_e.value}秒后重试。')
            await asyncio.sleep(_e.value)
            continue
        break
    logging.info(f'已将release note发送至"{chat_id}"。')
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
            media=media  # noqa.
        )
    )
    return raw.types.InputMediaDocument(
        id=raw.types.InputDocument(
            id=media.document.id,  # noqa.
            access_hash=media.document.access_hash,  # noqa.
            file_reference=media.document.file_reference  # noqa.
        )
    )


async def upload_file_with_cache(client: pyrogram.Client, chat_id, path: str, max_retry: int = 3):
    """复用TRMD上传缓存上传单个文件,返回可直接发送的InputMediaDocument。

    针对续传缓存做了容错:缓存标记已传但服务端分片缺失(FilePartMissing)时,把该分片
    移出缓存重传;历史分片整体失效(FilePartLengthInvalid)时,更换file_id重传全部分片。
    """
    file_size: int = os.path.getsize(path)
    if file_size == 0:
        logging.info(f'文件大小为0,跳过上传:"{path}"。')
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
    file_name: str = os.path.basename(path)
    mime_type = client.guess_mime_type(path) or 'application/octet-stream'
    attributes = [raw.types.DocumentAttributeFilename(file_name=file_name)]
    reset = 0
    while True:
        # 补传缺失分片。
        for part in task.get_missing_parts():
            while True:
                try:
                    await client.save_file(path=path, file_id=task.file_id, file_part=part)
                    break
                except FloodWait as _e:
                    logging.info(f'上传"{file_name}"分片遇频率限制,等待{_e.value}秒后重试。')
                    await asyncio.sleep(_e.value)
            task.update_file_part(part)
        # 组装InputFile并发起UploadMedia。
        if file_size > 10 * 1024 * 1024:
            file = raw.types.InputFileBig(id=task.file_id, parts=task.file_total_parts, name=file_name)
        else:
            md5_hash = hashlib.md5()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5_hash.update(chunk)
            md5_sum = ''.join(hex(i)[2:].zfill(2) for i in md5_hash.digest())
            file = raw.types.InputFile(id=task.file_id, parts=task.file_total_parts, name=file_name,
                                       md5_checksum=md5_sum)
        try:
            return await get_input_media_document(client, chat_id, file, attributes, mime_type)
        except FilePartMissing as _e:
            # 缓存标记已传、但服务端该分片缺失:移出缓存并重传后再试。
            missing_part = getattr(_e, 'value', None)
            logging.info(f'"{file_name}"分片{missing_part}在服务端缺失,移出缓存并重传。')
            if missing_part is not None and missing_part in task.file_part:
                task.file_part.remove(missing_part)
                task.save_json()
            continue
        except FilePartLengthInvalid as _e:
            # 复用了历史会话的分片缓存但服务端已整体失效:更换file_id重传全部分片。
            reset += 1
            if reset > max_retry:
                logging.error(f'"{file_name}"分片长度无效,重置重传{max_retry}次仍失败,放弃。原因:"{_e}"')
                raise
            logging.info(f'"{file_name}"服务端分片已失效,更换file_id重传全部分片({reset}/{max_retry})。')
            task.reset_upload(file_id=client.rnd_id())
            continue


async def upload_rar_media(client: pyrogram.Client, chat_id) -> pyrogram.types.Message | None:
    rar_paths = get_rar_paths()
    if not rar_paths:
        logging.info(f'未在"{OUTPUT_DIRECTORY}"下找到任何.rar文件,跳过上传。')
        return None
    UploadTask.DIRECTORY_NAME = os.path.join(UploadTask.DIRECTORY_NAME, str(client.me.id))
    client.save_file_semaphore = asyncio.Semaphore(1)
    logging.info(f'正在上传{len(rar_paths)}个.rar文件到"{chat_id}"。')
    documents = []
    for path in rar_paths:
        media = await upload_file_with_cache(client, chat_id, path)
        if media is not None:
            documents.append(media)
    if not documents:
        logging.warning('没有可上传的.rar文件。')
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
        except FloodWait as _e:
            logging.info(f'发送请求频繁,需等待{_e.value}秒后重试。')
            await asyncio.sleep(_e.value)
            continue
        break
    messages = await utils.parse_messages(client, result)
    album_message: pyrogram.types.Message | None = messages[0] if messages else None
    logging.info(f'已上传{len(documents)}个.rar文件至"{chat_id}"。')
    return album_message


async def send_release(
        telegram_config: TelegramConfig,
        target_chat: Union[int, str] = None,
        release_note_path: Optional[str] = None
) -> None:
    chat_id = resolve_chat_id(target_chat)
    client = get_client(telegram_config)
    await client.start()
    try:
        album_message = await upload_rar_media(client, chat_id)
        changelog = read_changelog(release_note_path=release_note_path)
        if changelog:
            await send_changelog_text(
                client=client,
                chat_id=chat_id,
                changelog=changelog,
                reply_to_message_id=album_message.id if album_message else None
            )
    finally:
        await client.stop()


async def send_changelog(
        telegram_config: TelegramConfig,
        target_chat: Union[int, str] = None,
        release_note_path: Optional[str] = None
) -> None:
    changelog = read_changelog(release_note_path=release_note_path)
    if not changelog:
        return
    client = get_client(telegram_config)
    await client.start()
    try:
        await send_changelog_text(
            client=client,
            chat_id=resolve_chat_id(target_chat),
            changelog=changelog
        )
    finally:
        await client.stop()


def send(
        telegram_config: TelegramConfig,
        target_chat: Union[int, str] = None,
        release_note_path: Optional[str] = None,
        upload: Optional[bool] = None
):
    if upload:
        asyncio.run(
            send_release(
                telegram_config=telegram_config,
                target_chat=target_chat,
                release_note_path=release_note_path
            )
        )
    else:
        asyncio.run(
            send_changelog(
                telegram_config=telegram_config,
                target_chat=target_chat,
                release_note_path=release_note_path
            )
        )
