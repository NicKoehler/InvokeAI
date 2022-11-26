from numpy import arange
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class Buttons:
    @staticmethod
    def close():
        return [InlineKeyboardButton(text="❌ Chiudi", callback_data="close")]

    @staticmethod
    def back():
        return [InlineKeyboardButton(text="↩️ Indietro", callback_data="back")]

    @staticmethod
    def generate_keyboard():
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔁 Genera utilizzando il prompt", callback_data="genera")]]
        )

    @staticmethod
    def settings_buttons(sd, preview=True):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        f"Modello: {sd.model_name}", callback_data="model"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        f"Immagini da generare: {sd.iterations}",
                        callback_data="iterations",
                    ),
                    InlineKeyboardButton(
                        f"Mostra anteprima: {'✅' if preview else '❌'}",
                        callback_data="preview",
                    ),
                ],
                [
                    InlineKeyboardButton(f"Steps: {sd.steps}", callback_data="steps"),
                    InlineKeyboardButton(
                        f"Cfg scale: {sd.cfg_scale}", callback_data="scale"
                    ),
                    InlineKeyboardButton(
                        f"Sampler: {sd.sampler_name}", callback_data="sampler"
                    ),
                ],
                Buttons.close(),
            ]
        )

    @staticmethod
    def __gen_buttons(setting_name: str, current_value: int | float):
        return lambda x: InlineKeyboardButton(
            f"{x} ✅" if x == current_value else str(x),
            callback_data=f"{setting_name}|{x}",
        )

    @staticmethod
    def iterations(current_value: int):
        b = list(map(Buttons.__gen_buttons("iterations", current_value), range(1, 51)))

        return InlineKeyboardMarkup(
            inline_keyboard=[
                *[b[i : i + 5] for i in range(0, len(b), 5)],
                Buttons.back(),
                Buttons.close(),
            ]
        )

    @staticmethod
    def steps(current_value: int):
        b = list(map(Buttons.__gen_buttons("steps", current_value), range(5, 101, 5)))

        return InlineKeyboardMarkup(
            inline_keyboard=[
                *[b[i : i + 5] for i in range(0, len(b), 5)],
                Buttons.back(),
                Buttons.close(),
            ]
        )

    @staticmethod
    def scale(current_value: float):
        b = list(
            map(Buttons.__gen_buttons("scale", current_value), arange(1, 20.5, 0.5))
        )

        return InlineKeyboardMarkup(
            inline_keyboard=[
                *[b[i : i + 5] for i in range(0, len(b), 5)],
                Buttons.back(),
                Buttons.close(),
            ]
        )

    @staticmethod
    def model(model: dict, current_value: str):
        b = list(map(Buttons.__gen_buttons("model", current_value), model.keys()))

        return InlineKeyboardMarkup(
            inline_keyboard=[
                *[b[i : i + 2] for i in range(0, len(b), 2)],
                Buttons.back(),
                Buttons.close(),
            ]
        )

    @staticmethod
    def sampler(current_value: str):
        b = list(
            map(
                Buttons.__gen_buttons("sampler", current_value),
                (
                    "plms",
                    "ddim",
                    "k_dpm_2_a",
                    "k_dpm_2",
                    "k_euler_a",
                    "k_euler",
                    "k_heun",
                    "k_lms",
                ),
            )
        )

        return InlineKeyboardMarkup(
            inline_keyboard=[
                *[b[i : i + 3] for i in range(0, len(b), 3)],
                Buttons.back(),
                Buttons.close(),
            ]
        )
