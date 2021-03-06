#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, logging
from telegram import Bot
from telegram.utils.request import Request as TGRequest
from utils import load
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    ConversationHandler,
)
from utils import (
    messages as _msg,
    restricted as _r,
    get_set as _set,
    get_functions as _func,
    task_box as _box,
    task_payload as _payload,
)

from workflow import (
    start_workflow as _start,
    quick_workflow as _quick,
    copy_workflow as _copy,
)
from multiprocessing import Process as _mp, Manager
from threading import Thread
from utils.load import ns


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ############################### Main ####################################


def main():
    ### bot define
    request = TGRequest(con_pool_size=8)
    bot = Bot(token=f"{load.cfg['tg']['token']}", request=request)
    updater = Updater(bot=bot, use_context=True)

    ### judge is restart
    is_restart = load.db_counters.find_one({"_id": "is_restart"})
    if is_restart is not None:
        if is_restart["status"] == 0:
            pass
        else:
            _func.check_restart(bot)

    else:
        load.db_counters.update(
            {"_id": "is_restart"}, {"status": 0}, upsert=True,
        )

    dp = updater.dispatcher

    # Entry Conversation
    conv_handler = ConversationHandler(
        entry_points=[
            # Entry Points
            CommandHandler("set", _set._setting),
            CommandHandler("menu", _start.menu),
            CommandHandler("quick", _quick.quick),
            CommandHandler("copy", _copy.copy),
            CommandHandler("task", _box.taskinfo),
        ],
        states={
            _set.SET_FAV_MULTI: [
                # fav settings function
                MessageHandler(Filters.text, _set._multi_settings_recieved),
            ],
            _start.CHOOSE_MODE: [
                # call function  judged via callback pattern
                CallbackQueryHandler(_quick.quick, pattern="quick"),
                CallbackQueryHandler(_copy.copy, pattern="copy"),
            ],
            _quick.GET_LINK: [
                # get Shared_Link states
                MessageHandler(Filters.text, _func.get_share_link),
            ],
            _set.IS_COVER_QUICK: [
                # cover quick setting
                CallbackQueryHandler(_func.modify_quick_in_db, pattern="cover_quick"),
                CallbackQueryHandler(_func.cancel, pattern="not_cover_quick"),
                MessageHandler(Filters.text, _func.cancel),
            ],
            _copy.GET_DST: [
                # request DST
                CallbackQueryHandler(_copy.request_srcinfo),
            ],
        },
        fallbacks=[CommandHandler("cancel", _func.cancel)],
    )

    def stop_and_restart():
        progress.terminate()
        load.myclient.close()
        updater.stop()
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)

    def restart(update, context):
        restart_msg = update.message.reply_text(load._text[load._lang]["is_restarting"])
        restart_chat_id = restart_msg.chat_id
        restart_msg_id = restart_msg.message_id
        load.db_counters.update_one(
            {"_id": "is_restart"},
            {
                "$set": {
                    "status": 1,
                    "chat_id": restart_chat_id,
                    "message_id": restart_msg_id,
                }
            },
            True,
        )
        Thread(target=stop_and_restart).start()

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("start", _start.start))
    dp.add_handler(CommandHandler("kill", _func.taskill))
    dp.add_handler(CommandHandler("ver", _func._version))

    dp.add_handler(
        CommandHandler(
            "restart",
            restart,
            filters=Filters.user(user_id=int(load.cfg["tg"]["usr_id"])),
        )
    )

    dp.add_error_handler(_func.error)

    updater.start_polling()
    logger.info(f"Fxxkr LAB iCopy {load._version} Start")
    updater.idle()


if __name__ == "__main__":
    ns.x = 0
    progress = _mp(target=_payload.task_buffer, args=(ns,))
    progress.start()
    main()
