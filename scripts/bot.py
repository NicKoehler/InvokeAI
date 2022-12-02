import yaml
import asyncio
import logging
import nest_asyncio
from io import BytesIO
from os import environ, path
from dotenv import load_dotenv
from bot_buttons import Buttons
from ldm.invoke.args import Args
from ldm.generate import Generate
from ldm.invoke.globals import Globals
from aiogram import Bot, Dispatcher, executor
from aiogram.dispatcher.filters import IDFilter, Text
from aiogram.types import CallbackQuery, InputFile, InputMediaPhoto, Message

load_dotenv()
nest_asyncio.apply()

SAMPLERS = (
    "plms",
    "ddim",
    "k_dpm_2_a",
    "k_dpm_2",
    "k_dpmpp_2_a",
    "k_dpmpp_2",
    "k_euler_a",
    "k_euler",
    "k_heun",
    "k_lms",
)

BOT_TOKEN = environ.get("BOT_TOKEN")
OWNER_ID = int(environ.get("OWNER_ID"))
DEFAULT_ITERATIONS = int(environ.get("DEFAULT_ITERATIONS"))
DEFAULT_PREVIEW = environ.get("DEFAULT_PREVIEW").lower() == "true"
STEPS_UPDATE_PREVIEW = int(environ.get("STEPS_UPDATE_PREVIEW"))

user_state = {
    "show_preview": DEFAULT_PREVIEW,
    "is_generating": False,
    "num_gen": 1,
    "setting": None,
}

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode="html")
dp = Dispatcher(bot=bot)

args = Args().parse_args()

Globals.root = path.expanduser(
    args.root_dir or environ.get("INVOKEAI_ROOT") or path.abspath(".")
)

print(f'>> InvokeAI runtime directory is "{Globals.root}"')
conf = path.normpath(path.join(Globals.root, "configs/models.yaml"))

# Initialize stable diffusion generator
with open(conf) as f:
    config = yaml.safe_load(f)

sd = Generate(conf=conf, max_loaded_models=1)
sd.iterations = DEFAULT_ITERATIONS
sd.load_model()


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

        elif step % STEPS_UPDATE_PREVIEW == 0:
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
    def callback(image, seed, first_seed=s["seed"]):
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
        step_callback=(
            make_step_callback(message, sd.steps)
            if user_state["show_preview"]
            else None
        ),
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
        "· Genera immagini semplicemente digitando un prompt\n"
        "· Imposta il seed semplicemente digitando un numero",
        reply_markup=Buttons.default(sd, user_state["show_preview"]),
    )


@dp.message_handler(IDFilter(user_id=OWNER_ID), commands="impostazioni")
async def send_settings(message: Message):

    await message.reply(
        "Impostazioni",
        reply_markup=Buttons.settings_buttons(sd, user_state["show_preview"]),
    )


@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="👤"))
@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="🔢"))
@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="🌄"))
@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="👣"))
@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="📏"))
@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="🔮"))
@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="🪴"))
async def message_settings(message: Message):
    char = message.text[0]
    match char:
        case "👤":
            user_state["setting"] = char
            keyboard = Buttons.model(config, sd.model_name)
            text = "👤 Seleziona il modello"
        case "🔢":
            user_state["setting"] = char
            keyboard = Buttons.iterations(sd.iterations)
            text = "🔢 Immagini da generare"
        case "👣":
            user_state["setting"] = char
            keyboard = Buttons.steps(sd.steps)
            text = "👣 Steps"
        case "📏":
            user_state["setting"] = char
            keyboard = Buttons.scale(sd.cfg_scale)
            text = "📏 Cfg scale"
        case "🔮":
            user_state["setting"] = char
            keyboard = Buttons.sampler(sd.sampler_name, SAMPLERS)
            text = "🔮 Seleziona il sampler"
        case "🪴":
            if sd.seed:
                sd.seed = None
                await message.reply(
                    "Seed resettato",
                    reply_markup=Buttons.default(sd, user_state["show_preview"]),
                )
            else:
                await message.reply("Il seed è già casuale")
            return
        case "🌄":
            user_state["show_preview"] = not user_state["show_preview"]
            await message.reply(
                "Anteprima abilitata"
                if user_state["show_preview"]
                else "Anteprima disabilitata",
                reply_markup=Buttons.default(sd, user_state["show_preview"]),
            )
            return

    await message.reply(text, reply_markup=keyboard)


@dp.message_handler(IDFilter(user_id=OWNER_ID), Text(startswith="❌"))
async def cancel(message: Message):

    if user_state["setting"]:
        user_state["setting"] = None
        await message.reply(
            "Operazione annullata.",
            reply_markup=Buttons.default(sd, user_state["show_preview"]),
        )


@dp.message_handler(
    IDFilter(user_id=OWNER_ID), lambda _: user_state["setting"] is not None
)
async def setting_handler(message: Message):

    value = message.text.rstrip(" ✅")
    match user_state["setting"]:
        case "🔢":
            if value.isnumeric():
                sd.iterations = int(value)
                text = f"🔢 Immagini da generare impostate a <b>{sd.iterations}</b>"
            else:
                text = "Valore per immagini da generare non valido"
        case "👣":
            if value.isnumeric():
                sd.steps = int(value)
                text = f"👣 Steps impostati a <b>{sd.steps}</b>"
            else:
                text = "Valore per steps non valido"
        case "📏":
            try:
                sd.cfg_scale = float(value)
                text = f"📏 Cfg scale impostato a <b>{sd.cfg_scale}</b>"
            except ValueError:
                text = "Valore per scale non valido"
        case "👤":
            if value == sd.model_name:
                text = "Nulla da cambiare"
            elif value not in config.keys():
                text = "Modello non valido, riprova"
            else:
                m = await message.reply(
                    "Cambiare il modello richiede un po' di tempo, attendi"
                )
                await m.pin()
                sd.set_model(value)
                text = f"👤 Modello impostato su <b>{sd.model_name}</b>"
                await message.unpin()
        case "🔮":

            if value not in SAMPLERS:
                text = "Sampler non valido, riprova"
            else:
                sd.sampler_name = value
                sd._set_sampler()
                text = f"🔮 Sampler impostato su <b>{sd.sampler_name}</b>"

    user_state["setting"] = None

    await message.reply(
        text, reply_markup=Buttons.default(sd, user_state["show_preview"])
    )


@dp.message_handler(IDFilter(user_id=OWNER_ID), lambda m: m.text.isnumeric())
async def set_seed(message: Message):
    sd.seed = int(message.text)
    await message.reply(
        f"Seed impostato su <code>{sd.seed}</code>",
        reply_markup=Buttons.default(sd, user_state["show_preview"])
    )


@dp.message_handler(IDFilter(user_id=OWNER_ID))
async def send_image(message: Message):

    if user_state["is_generating"]:
        await message.reply(
            "Non puoi generare immagini mentre ne stai già generando altre, attendi"
        )
        return

    # clean up the prompt
    prompt = message.text.replace("\n", "")

    await generate_image(message, prompt)


@dp.callback_query_handler(IDFilter(user_id=OWNER_ID), Text(equals="genera"))
async def callback_genera(callback: CallbackQuery):
    text = callback.message.caption
    prompt = text.splitlines()[0][8:]
    await generate_image(callback.message, prompt)


async def ready(_):
    await bot.send_message(
        OWNER_ID,
        "Bot pronto",
        reply_markup=Buttons.default(sd, user_state["show_preview"]),
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=ready)
