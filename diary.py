"""Simple web scraper for manodienynas.lt
"""
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urljoin
from os.path import exists
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def get_config(path):
    """get config from json file

    Args:
        path (str): path to file

    Returns:
        data (dict): config dictionary
    """
    with open(path, "r", encoding="utf-8") as content:
        data = json.loads(content.read())
    return data


class DiaryClient():
    """Diary Clients Class
    """

    def __init__(self, uri=None, password=None, username=None):
        """constructor for DiaryClient

        Args:
            uri (str, optional): base uri. Defaults to None.
            password (str, optional): password. Defaults to None.
            username (str, optional): username. Defaults to None.
        """
        self.__username = username
        self.__password = password
        self.__uri = uri.rstrip('/') if uri else None
        self.__session = None
        self.login()

    def __enter__(self):
        return self

    def __invoke_session(self):
        """Create session method
        """
        self.__session = requests.Session()
        self.__session.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
            "Accept": "application/json"}

    def login(self):
        """login method
        """
        if not self.__session:
            self.__invoke_session()
        payload = {'password': self.__password,
                   'username': self.__username}
        endpoint = self.__uri + "/1/lt/ajax/user/login"
        try: 
            self.__session.post(url=endpoint, data=payload)
        except requests.exceptions.HTTPError as err:
            print(f"Http error ocured {err}")
        except requests.exceptions.TooManyRedirects as err:
            print(f"Too many redirects {err}")



    def get_messages(self):
        """get messages html content

        Returns:
            data (str): message html content
        """
        endpoint = self.__uri + "/1/lt/page/message_new/message_list"
        data = (self.__session.get(endpoint)).content
        return data

    def get_homework(self):
        """get homework metadata

        Returns:
            data (str): homework html content
        """
        endpoint = self.__uri + "/1/lt/page/classhomework/home_work"
        data = (self.__session.get(endpoint)).content
        return data

    def get_event(self):
        """get event metadata

        Returns:
            data (str): events html content
        """
        endpoint = self.__uri + "/1/lt/page/sf/resolve_post/event/list"
        data = (self.__session.get(endpoint)).content
        return data

    def get_message_content(self, message_uri):
        """get html content for specific uri

        Args:
            message_uri (str): message enpoint

        Returns:
            data (str): html content
        """
        endpoint = urljoin(self.__uri, message_uri)
        data = (self.__session.get(endpoint)).content
        return data

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__session.close()


class SoupExeption(Exception):
    """Soup Exception Class
    """


class SoupReader():
    """some class docs
    """

    def __init__(self, parser="html.parser", **kwargs):
        self.__parser = parser
        self.__uri = kwargs.get("uri")
        self.__username = kwargs.get("username")
        self.__password = kwargs.get("password")
        self.__diary_client = DiaryClient(
            self.__uri, self.__password, self.__username)

    def __enter__(self):
        return self

    def __invoke_soap(self, content):
        """method to create BeautifulSoup object

        Args:
            content (str): html content

        Returns:
            soap (obj): returns BeautifulSoup object
        """
        soup = BeautifulSoup(content, self.__parser)
        return soup

    def get_new_messages(self):
        """get unread messages

        Returns:
            messages_summary (dict): messages summary
        """
        messages_summary = {}
        if self.__diary_client:
            message_html_content = self.__diary_client.get_messages()
        soup = self.__invoke_soap(message_html_content)
        for tr_element in soup("tr", class_="msg-url"):
            for span in tr_element("span", class_="unreadMessage"):
                key = span.find("a").get('href')
                value = span.find("a").get('title')
                if key and key != "#":
                    if messages_summary.get(key):
                        messages_summary[key].append(value)
                    else:
                        messages_summary[key] = [value]
        return messages_summary

    def read_messages(self, message_uri):
        """read new messages

        Args:
            message_uri (str): endpoint address

        Returns:
            message_html_body (str): html message content
            sender (str): sender label
        """
        content = self.__diary_client.get_message_content(message_uri)
        soup = self.__invoke_soap(content)
        message_html_body = (soup.find("div", class_="messageText")).prettify()
        sender = soup.find(
            "span", class_="messageInboxSenderLabel").contents[0]
        return message_html_body, sender

    def read_homework(self):
        """method to read all homeworks

        Returns:
            homeworks (str): html homework content
        """
        homeworks = []
        content = self.__diary_client.get_homework()
        soup = self.__invoke_soap(content)
        homeworks = soup.find(
            "table", class_="classhomework_table fullWidth hoverTr")
        return homeworks

    def get_events(self):
        """method to return events

        Returns:
            _type_: _description_
        """
        events = []
        content = self.__diary_client.get_event()
        soup = self.__invoke_soap(content)
        events = soup.find_all(class_=lambda value: value and value.startswith(
            "md-block event-holder ev-count-cl event_block block-new_message"))
        br_tag = soup.new_tag("br")
        for event in events:
            event.a.insert(0,br_tag)
        return events

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("closing session")
        self.__diary_client.__exit__(None, None, None)


def event_check(event_id, **kwargs):
    """function to check event id

    Args:
        event_id (str): event id

    Returns:
        Boolen: true if event is new
    """
    data = []
    config_path = kwargs.get("events_file", "events.txt")
    if not exists(config_path):
        Path(config_path).touch()
    with open(config_path, "r", encoding="UTF-8") as file_obj:
        data = file_obj.readlines()
        event_id = event_id + '\n'
        if event_id in data:
            return False
        if len(data) > 15:
            del data[0]
        data.append(event_id)
    with open(config_path, "w", encoding="UTF-8") as file_obj:
        file_obj.writelines(data)
    return True


def mail_client(message_content, subject, **kwargs):
    """Function to send email messages

    Args:
        message_content (str): html content of message
        subject (str): emails subject
        kwargs (dict): mail client settings
    """
    sender_email = kwargs.get("sender_email")
    receiver_email = kwargs.get("receiver_email")
    smtp_server = kwargs.get("smtp_server")
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message_header = kwargs.get("message_header", "")
    html = f"""
    <html>
        <body>
        <style>
        .event-header {{
            color: green;
        }}
        a {{
            padding: 6px 15px 6px 45px;
            background-size: 25px;
        }}
        span {{
            display: block;
        }}
        </style>
            <h4 class="event-header">{message_header}</h4>
            <br>
            {message_content}
        </body>
    </html>
    """
    render = MIMEText(html, "html")
    message.attach(render)
    with smtplib.SMTP(smtp_server) as server:
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )


def main():
    """main function
    """
    events = []
    config = get_config(path="config.json")
    with SoupReader(**config) as reader:
        events = reader.get_events()
        for event in events:
            event_type = event.find("div", class_="trigger").contents[0]
            header = event.find("h4", class_="event-header").contents[0]
            create_date = event.find("div", class_="create-date").contents[0]
            event_id = event["id"]
            event_text = event.find("div", class_="event-text")
            if not event_check(event_id):
                continue
            if event_type == 'Gauti pranešimai':
                messages = {}
                messages = reader.get_new_messages()
                for message_uri, subject in messages.items():
                    message, sender = reader.read_messages(message_uri)
                    mail_client(message, '-'.join(subject),
                                message_header=sender, **config)
            else:
                mail_client(event_text, create_date+event_type,
                            message_header=header, **config)


if __name__ == "__main__":
    main()
