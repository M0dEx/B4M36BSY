import threading
from queue import Queue
from comm import Type, Channel
from time import sleep


class Bot:
    def __init__(self, token: str, gist: str):
        self.channel = Channel(Type.BOT, token, gist)
        self.unprocessed_commands = Queue()
        self.active = True
        self.worker_thread = None

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

            print(f"Processing command = {current_command.body}")

            if current_command.body == Channel.PING_MESSAGE:
                self.channel.send_message(
                    "Me!"
                )  # TODO: Put the id of the message we are reacting to to the message
            # TODO: Additional commands

            self.unprocessed_commands.task_done()
