import base64
import re
import threading
from queue import Queue, Empty
from time import sleep

from github.GistComment import GistComment

from channel import Channel


class Controller:
    def __init__(self, token: str, gist: str):
        self.channel = Channel(token, gist)
        self.unprocessed_responses = Queue()
        self.active = True
        self.response_thread = threading.Thread(
            target=self.receive_responses, daemon=True
        )
        self.ping_thread = threading.Thread(
            target=self.ping_bots, daemon=True
        )
        self.last_ping = None

        self.bots = {}

        self.response_thread.start()
        self.ping_thread.start()
        self.wait_for_commands()

    def receive_responses(self):
        while self.active:
            for new_response in self.channel.check_messages():
                self.handle_response(new_response)

            sleep(2)

    def handle_response(self, response: GistComment):
        response_footer = response.body[response.body.rfind("["):]
        response_id = base64.b64decode(response_footer.split("(")[1].split(")")[0].encode('utf-8')).decode('utf-8')

        if Channel.PING_RESPONSE in response.body:
            self.bots[response_id.split("-")[1]] = int(response_id.split("-")[0])
            self.channel.delete_message(response.id)

    def ping_bots(self):
        while self.active:

            if self.last_ping:
                self.channel.delete_message(self.last_ping)

            self.last_ping = self.channel.send_message(
                f"{Channel.PING_REQUEST}"
            ).id

            sleep(60)

    def wait_for_commands(self):

        while self.active:
            input_str = input("$ ")
            args = input_str.split(" ")

            if args[0].lower() == "exit":
                self.exit()
            elif args[0].lower() == "status":
                self.print_status()

    def exit(self):
        self.active = False

        if self.last_ping:
            self.channel.delete_message(self.last_ping)

    def print_status(self):
        print(f"Bots currently online: {len([x for x, y in self.bots.items() if y == self.last_ping])}")
