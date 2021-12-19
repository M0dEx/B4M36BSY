from enum import Enum
from github import Github
from github.GistComment import GistComment


class Type(Enum):
    CONTROLLER = 0
    BOT = 1


class Channel:

    PING_REQUEST = "Who's still working on this?"
    PING_RESPONSE = "Me!"

    W_REQUEST = "What do you think about this?"
    W_RESPONSE = "Eh, I think some improvements could be made."

    LS_REQUEST = "What are you working on?"
    LS_RESPONSE = "I am currently working on something else, sorry. :("

    def __init__(self, type: Type, token: str, gist: str):
        self.type = type
        self.connector = Github(token)
        self.gist = self.connector.get_gist(gist)
        self.last_comment = None

    def check_messages(self) -> list[GistComment]:
        comments = self.gist.get_comments()

        new_comments = []

        if comments.totalCount == 0:
            return new_comments

        if self.last_comment is None:
            self.last_comment = comments[comments.totalCount - 1].id

        old_last_idx = next(
            (
                x
                for x in range(comments.totalCount)
                if comments[x].id == self.last_comment
            ),
            comments.totalCount - 1,
        )
        new_comments.extend(comments[old_last_idx + 1 :])
        self.last_comment = comments[comments.totalCount - 1].id

        return new_comments

    def send_message(self, message: str):
        new_comment = self.gist.create_comment(message)
        self.last_comment = new_comment.id
