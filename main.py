# -*- config: utf-8 -*-

import configparser
import io
import logging
from pathlib import Path
from typing import Final, Dict, List

from telegram import ChatAction
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
config = configparser.ConfigParser()
config.read('bot.ini')

TOKEN = config.get('auth', 'token')
REQUEST_KWARGS: Dict[str, str] = {
    'proxy_url': 'socks5://localhost:9050/',
}
ZIP_EXT: Final[str] = '.zip'


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Send me a ZIP archive! I will try to create a PDF file from it.')


def unzip(data: io.BytesIO, temp_dir: Path, temp_sub_dir: Path) -> str:
    import zipfile
    try:
        archive = zipfile.ZipFile(data)
        archive.extractall(temp_dir / temp_sub_dir)
    except Exception as ex:
        return repr(ex)
    else:
        return ''


def compile_pdf(temp_dir: Path) -> str:
    from subprocess import CompletedProcess, run
    sub_folders: List[Path] = list(temp_dir.iterdir())
    assert (len(sub_folders) == 1)
    sub_folder: Path = sub_folders[0]
    tex_files: List[Path] = list(sub_folder.glob('*.tex'))
    if len(tex_files) != 1:
        return f'In the archive, I see {len(tex_files)} TeX files.' \
               ' I do not know what to compile.'

    tex_file: Path = tex_files[0]
    cwd: Path = tex_file.parent.absolute()

    def run_pdflatex():
        # noinspection PyTypeChecker
        result: CompletedProcess = run(('pdflatex', '-shell-escape', '-halt-on-error',
                                        tex_file.name),
                                       cwd=cwd,
                                       capture_output=True)
        if result.stdout:
            with tex_files[0].with_suffix('.stdout').open('ab') as f_out:
                f_out.write(result.stdout)
        if result.stderr:
            with tex_files[0].with_suffix('.stderr').open('ab') as f_out:
                f_out.write(result.stderr)

    def run_biblatex(backend: str):
        # noinspection PyTypeChecker
        result: CompletedProcess = run((backend, tex_file.with_suffix('').name),
                                       cwd=cwd,
                                       capture_output=True)
        if result.stdout:
            with tex_files[0].with_suffix('.blg.stdout').open('ab') as f_out:
                f_out.write(result.stdout)
        if result.stderr:
            with tex_files[0].with_suffix('.blg.stderr').open('ab') as f_out:
                f_out.write(result.stderr)

    run_pdflatex()
    bib_files: List[Path] = list(sub_folder.glob('*.bib'))
    if bib_files:
        run_biblatex('bibtex')
        run_pdflatex()
        run_pdflatex()


def compress(temp_dir: Path, temp_sub_dir: Path) -> str:
    import shutil
    # noinspection PyTypeChecker
    return shutil.make_archive(temp_dir / temp_sub_dir, 'zip', temp_dir / temp_sub_dir)


def get(update, context):
    import tempfile
    document = update.message.document
    new_file = context.bot.get_file(document.file_id)
    zip_file = io.BytesIO()
    zip_file.name = document.file_name
    new_file.download(out=zip_file)
    context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                 action=ChatAction.TYPING)
    with tempfile.TemporaryDirectory() as temp:
        temp_sub_dir: Path = Path(document.file_name)
        if temp_sub_dir.suffix.lower() == ZIP_EXT:
            temp_sub_dir = temp_sub_dir.with_suffix('')
        resp: str = unzip(zip_file, Path(temp), temp_sub_dir)
        if resp:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=resp)
        else:
            resp = compile_pdf(Path(temp))
            if resp:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=resp)
            else:
                resp = compress(Path(temp), temp_sub_dir)
                if resp:
                    context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                                 action=ChatAction.UPLOAD_DOCUMENT)
                    context.bot.send_document(chat_id=update.effective_chat.id,
                                              document=open(resp, 'rb'))
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Failed to compress the result')


if __name__ == '__main__':
    updater = Updater(token=TOKEN, use_context=True, request_kwargs=REQUEST_KWARGS)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    get_file_handler = MessageHandler(Filters.document.zip, get)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(get_file_handler)
    updater.start_polling()
    updater.idle()
