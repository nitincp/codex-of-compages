"""
Faber — Chainlit UI shell.

Bare stub for M0. The full agent chain (SME → Spec Advisor → Spec Specialist →
Coordinator) is wired in at M7 once all layers are proven.
"""

import chainlit as cl
from dotenv import load_dotenv

load_dotenv()


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content=(
            "**Faber** is ready.\n\n"
            "Describe your project and I will generate a layered formal specification.\n\n"
            "*(Council not yet wired — M0 shell only)*"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    await cl.Message(
        content=f"Received: {message.content!r}\n\n*(Agent chain coming in M6–M8)*"
    ).send()
