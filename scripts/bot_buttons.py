from numpy import arange
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)


class Buttons:
    @staticmethod
    def default(sd, preview=True):
        return ReplyKeyboardMarkup(
            [
                [f"👤 Modello: {sd.model_name}"],
                [f"🔢 Immagini da generare: {sd.iterations}"],
                [f"🌄 Mostra anteprima: {'✅' if preview else '❌'}"],
                [f"↕ Altezza: {sd.height}", f"↔ Larghezza: {sd.width}"],
                [
                    f"👣 Steps: {sd.steps}",
                    f"📏 Cfg scale: {sd.cfg_scale}",
                    f"🔮 Sampler: {sd.sampler_name}",
                ],
                [f"🪴 Reset seed: {sd.seed if sd.seed else '🎲'}"],
            ],
            resize_keyboard=True,
            one_time_keyboard=False,
        )

    @staticmethod
    def inline_cancel():
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton("❌", callback_data="cancel")]]
        )

    @staticmethod
    def cancel():
        return ["❌ Annulla"]

    @staticmethod
    def generate_keyboard():
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔁 Genera con questo prompt", callback_data="genera"
                    )
                ]
            ]
        )

    @staticmethod
    def __gen_buttons(current_value: int | float):
        return lambda x: f"{x} ✅" if x == current_value else str(x)

    @staticmethod
    def iterations(current_value: int):
        b = list(map(Buttons.__gen_buttons(current_value), range(1, 51)))

        return ReplyKeyboardMarkup(
            [
                *[b[i : i + 5] for i in range(0, len(b), 5)],
                Buttons.cancel(),
            ],
            one_time_keyboard=False,
        )

    @staticmethod
    def steps(current_value: int):
        b = list(map(Buttons.__gen_buttons(current_value), range(5, 101, 5)))

        return ReplyKeyboardMarkup(
            [
                *[b[i : i + 5] for i in range(0, len(b), 5)],
                Buttons.cancel(),
            ],
            one_time_keyboard=False,
        )

    @staticmethod
    def scale(current_value: float):
        b = list(map(Buttons.__gen_buttons(current_value), arange(1, 20.5, 0.5)))

        return ReplyKeyboardMarkup(
            [
                *[b[i : i + 5] for i in range(0, len(b), 5)],
                Buttons.cancel(),
            ],
            one_time_keyboard=False,
        )

    @staticmethod
    def model(model: dict, current_value: str):
        b = list(map(Buttons.__gen_buttons(current_value), model.keys()))

        return ReplyKeyboardMarkup(
            [
                *[b[i : i + 2] for i in range(0, len(b), 2)],
                Buttons.cancel(),
            ],
            one_time_keyboard=False,
        )

    @staticmethod
    def sampler(current_value: str, samplers: tuple[str]):
        b = list(map(Buttons.__gen_buttons(current_value), samplers))

        return ReplyKeyboardMarkup(
            [
                *[b[i : i + 3] for i in range(0, len(b), 3)],
                Buttons.cancel(),
            ],
            one_time_keyboard=False,
        )

    @staticmethod
    def height_width(current_value: int):
        b = list(map(Buttons.__gen_buttons(current_value), range(32, 1025, 32)))

        return ReplyKeyboardMarkup(
            [
                *[b[i : i + 5] for i in range(0, len(b), 5)],
                Buttons.cancel(),
            ],
            one_time_keyboard=False,
        )
