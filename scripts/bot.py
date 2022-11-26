import yaml
import asyncio
import logging
import nest_asyncio
from os import environ
from io import BytesIO
from dotenv import load_dotenv
from bot_buttons import Buttons
from ldm.generate import Generate
from aiogram import Bot, Dispatcher, executor
from aiogram.dispatcher.filters import IDFilter, Text
from aiogram.types import CallbackQuery, InputFile, InputMediaPhoto, Message

load_dotenv()
nest_asyncio.apply()

BOT_TOKEN = environ.get("BOT_TOKEN")
OWNER_ID = int(environ.get("OWNER_ID"))
DEFAULT_ITERATIONS = int(environ.get("DEFAULT_ITERATIONS"))
DEFAULT_PREVIEW = environ.get("DEFAULT_PREVIEW").lower() == "true"

user_state = {
    "show_preview": DEFAULT_PREVIEW,
    "is_generating": False,
    "num_gen": 1,
}

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode="html")
Bot.set_current(bot)
dp = Dispatcher(bot=bot)
Dispatcher.set_current(dp)

# Initialize stable diffusion generator
with open("configs/models.yaml") as f:
    config = yaml.safe_load(f)

sd = Generate(max_loaded_models=1)
sd.iterations = DEFAULT_ITERATIONS

for model in config:
    if config.get(model).get("default"):
        sd.set_model(model)
        break


def make_step_callback(message: Message, total):
    def callback(img, step):
        nonlocal message
        loop = asyncio.get_event_loop()
        if step == 0:
            image = sd.sample_to_image(img)
            with BytesIO() as buf:
                image.save(buf, "PNG")
                buf.seek(0)
                message = loop.run_until_complete(
                    bot.send_photo(
                        message.chat.id,
                        buf.getvalue(),
                        caption=f"Passaggio {step}/{total}",
                    )
                )

        elif step + 1 == total:
            loop.run_until_complete(message.delete())

        elif step % 5 == 0:
            image = sd.sample_to_image(img)
            with BytesIO() as buf:
                image.save(buf, "PNG")
                buf.seek(0)
                loop.run_until_complete(
                    message.edit_media(
                        InputMediaPhoto(
                            InputFile(buf, filename="image.png"),
                            caption=f"Passaggio {step}/{total}",
                        )
                    )
                )

    return callback


def make_image_callback(message, status_message, s):
    def callback(image, seed, first_seed=None):
        loop = asyncio.get_event_loop()
        with BytesIO() as buf:
            image.save(buf, "png")
            loop.run_until_complete(
                message.reply_photo(
                    buf.getvalue(),
                    f"Prompt: <code>{s['prompt']}</code>\n"
                    f"Model name: <code>{s['model']}</code>\n"
                    f"Steps: <code>{s['steps']}</code>\n"
                    f"Cfg Scale: <code>{s['scale']}</code>\n"
                    f"Sampler: <code>{s['sampler']}</code>\n"
                    f"seed <code>{seed}</code>",
                    reply_markup=Buttons.generate_keyboard(),
                )
            )
        user_state["num_gen"] += 1
        loop.run_until_complete(
            status_message.edit_text(
                f"🔄 Generazione in corso {user_state['num_gen']}/{s['iterations']}"
            )
        )

    return callback


async def generate_image(message: Message, prompt: str):
    """
    generate the images and send them to the user
    """
    if user_state["is_generating"]:
        await message.reply(
            "Non puoi generare immagini mentre ne stai già generando altre, attendi"
        )
        return

    user_state["is_generating"] = True

    current_settings = {
        "prompt": prompt,
        "model": sd.model_name,
        "steps": sd.steps,
        "scale": sd.cfg_scale,
        "sampler": sd.sampler_name,
        "iterations": sd.iterations,
        "seed": sd.seed,
    }

    status_message = await message.reply(
        f"🔄 Generazione in corso {user_state['num_gen']}/{current_settings['iterations']}"
    )
    await status_message.pin()

    sd.prompt2image(
        prompt,
        seed=sd.seed,
        step_callback=make_step_callback(message, sd.steps)
        if user_state["show_preview"]
        else None,
        image_callback=make_image_callback(message, status_message, current_settings),
    )

    user_state["is_generating"] = False
    user_state["num_gen"] = 1
    await status_message.unpin()
    await status_message.delete()


@dp.message_handler(IDFilter(user_id=OWNER_ID), commands=["start", "help"])
async def send_welcome(message: Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply(
        "Ciao sono Stable Diffusion Bot.\n\n"
        "· Genera immagini con /genera &lt;prompt&gt;\n"
        "· Regola i settaggi con /impostazioni\n"
        "· Imposta il seed semplicemente digitando un numero"
    )


@dp.message_handler(IDFilter(user_id=OWNER_ID), commands="impostazioni")
async def send_settings(message: Message):

    await message.reply(
        "Impostazioni",
        reply_markup=Buttons.settings_buttons(sd, user_state["show_preview"]),
    )


@dp.message_handler(IDFilter(user_id=OWNER_ID), commands=["genera"])
async def send_image(message: Message):

    if user_state["is_generating"]:
        await message.reply(
            "Non puoi generare immagini mentre ne stai già generando altre, attendi"
        )
        return

    args = message.get_args()

    if not args:
        await message.reply(
            "Utilizza il comando /genera seguito da un prompt, per esempio:\n"
            "<code>/genera a horse in the moon</code>"
        )
        return

    # clean up the prompt
    prompt = args.replace("\n", "")

    await generate_image(message, prompt)


@dp.message_handler(IDFilter(user_id=OWNER_ID), lambda m: m.text.isnumeric())
async def set_seed(message: Message):
    sd.seed = int(message.text)
    await message.reply(f"Seed impostato su <code>{sd.seed}</code>")


@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="close"))
async def delete_message(callback: CallbackQuery):
    await callback.message.delete()


@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="back"))
async def callback_back(callback: CallbackQuery):

    await callback.message.edit_text(
        "Impostazioni",
        reply_markup=Buttons.settings_buttons(sd, user_state["show_preview"]),
    )


@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="genera"))
async def callback_genera(callback: CallbackQuery):
    text = callback.message.caption
    prompt = text.splitlines()[0][8:]
    await generate_image(callback.message, prompt)


@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="iterations"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="steps"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="scale"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="model"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="sampler"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="preview"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="seed"))
async def callback_settings(callback: CallbackQuery):
    match callback.data:
        case "iterations":
            keyboard = Buttons.iterations(sd.iterations)
            text = "🔢 Immagini da generare"
        case "steps":
            keyboard = Buttons.steps(sd.steps)
            text = "👣 Steps"
        case "scale":
            keyboard = Buttons.scale(sd.cfg_scale)
            text = "📏 Cfg scale"
        case "model":
            keyboard = Buttons.model(config, sd.model_name)
            text = "👤 Seleziona il modello"
        case "sampler":
            keyboard = Buttons.sampler(sd.sampler_name)
            text = "🔮 Selezione il sampler"
        case "seed":
            if sd.seed:
                sd.seed = None
                await callback.answer("Seed resettato")
                await callback.message.edit_reply_markup(
                    Buttons.settings_buttons(sd, user_state["show_preview"])
                )
            else:
                await callback.answer("Il seed è già casuale")
            return
        case "preview":
            user_state["show_preview"] = not user_state["show_preview"]
            await callback.answer(
                "Anteprima abilitata"
                if user_state["show_preview"]
                else "Anteprima disabilitata"
            )
            await callback.message.edit_reply_markup(
                Buttons.settings_buttons(sd, user_state["show_preview"])
            )
            return

    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(startswith="iterations|"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(startswith="steps|"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(startswith="scale|"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(startswith="model|"))
@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(startswith="sampler|"))
async def callback_handler(callback: CallbackQuery):

    setting, value = callback.data.split("|")
    match setting:
        case "iterations":
            sd.iterations = int(value)
            keyboard = Buttons.iterations(sd.iterations)
            text = "🔢 Immagini da generare"
        case "steps":
            sd.steps = int(value)
            keyboard = Buttons.steps(sd.steps)
            text = "👣 Steps"
        case "scale":
            sd.cfg_scale = float(value)
            keyboard = Buttons.scale(sd.cfg_scale)
            text = "📏 Cfg scale"
        case "model":
            m = await callback.message.edit_text(
                "Cambiare il modello richiede un po' di tempo, attendi"
            )
            await m.pin()

            sd.set_model(value)

            await m.unpin()

            keyboard = Buttons.model(config, sd.model_name)

            text = "👤 Seleziona il modello"
        case "sampler":
            sd.sampler_name = value
            sd._set_sampler()
            keyboard = Buttons.sampler(sd.sampler_name)
            text = "🔮 Selezione il sampler"

    await callback.message.edit_text(text, reply_markup=keyboard)


async def ready(_):
    await bot.send_message(OWNER_ID, "Bot pronto")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=ready)
