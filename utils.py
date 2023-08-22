import base64


def get_header_data(mail_header, key):
    for data in mail_header:
        name = data["name"]
        if name == key:
            return data["value"]
    return ""


def decode_data(data):
    return base64.urlsafe_b64decode(data)