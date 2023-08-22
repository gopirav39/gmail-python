import os
import calendar
from peewee import *
from utils import get_header_data

db = SqliteDatabase('mail.db')
BASE_ATTACHMENT_PATH = os.path.join(os.path.dirname(__file__), "attachments")


class Mail(Model):
    id = CharField(primary_key=True)
    from_email = CharField()
    to = CharField()
    cc = CharField(null=True)
    bcc = CharField(null=True)
    subject = CharField()
    plain_body = TextField(null=True)
    html_body = TextField(null=True)
    received_on = DateTimeField()

    class Meta:
        database = db

    @classmethod
    def save_mail(cls, **mail_data):
        """Save mail if it not exists already"""
        attachments = mail_data.pop("attachments")
        if not cls.select().where(cls.id == mail_data["id"]).exists():
            mail = cls.create(**mail_data)
            for attachment in attachments:
                Attachment.save_attachment(**attachment, mail=mail)

    @classmethod
    def get_last_received_date(cls):
        """Return the epoch time"""
        recent_mail = cls.select().order_by(cls.received_on.desc()).first()
        if recent_mail:
            return calendar.timegm(recent_mail.received_on.utctimetuple())
        return None


class Attachment(Model):
    id = CharField(primary_key=True)
    name = CharField()
    path = CharField()
    mail = ForeignKeyField(Mail, backref="attachments")

    class Meta:
        database = db

    @classmethod
    def save_attachment(cls, **attachment):
        data = attachment.pop("data")
        path = os.path.join(BASE_ATTACHMENT_PATH, f"{attachment['id'][:10]}_{attachment['name']}")
        with open(path, "wb") as file_obj:
            file_obj.write(data)
        cls.create(path=path, **attachment)


def create_tables():
    with db:
        db.create_tables([Mail, Attachment])


if __name__ == "__main__":
    create_tables()