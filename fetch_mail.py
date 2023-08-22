"""This module fetches the mails for the given folder and save this in
the persistent storage

USAGE:
    e.g) python fetch_mail.py inbox

    The default folder to fetch mails is inbox, if we want to retrieve from other folder we can give that
    folder name.
"""

import argparse
from datetime import datetime

from utils import get_header_data, decode_data
from models import Mail
from mail_service import build_gmail_service


MIME_TYPE_TEXT_MAPPING = {
        "text/plain": "plain_body",
        "text/html": "html_body"
}


def list_mails():
    """
    Lists the user's Gmail from the configured folder.
    """

    service = build_gmail_service()
    input_folder = args.input_folder
    print("fetching messages from: ", input_folder)
    filter_query = f'in:{input_folder}'
    last_received_on = Mail.get_last_received_date()
    if last_received_on:
        filter_query += f" after:{last_received_on}"
    print("filter query: ", filter_query)

    # Call the Gmail API
    try:
        results = service.users().messages().list(userId='me', q=filter_query).execute()
    except Exception as err:
        print(f"Exception in fetch mail: {err}")
        raise
    total_messages = len(results["messages"])
    print("total messages: ", total_messages)
    if total_messages > 0:
        for message in results["messages"]:
            result = get_mail(message["id"], service)
            if result is not None:
                result = parse_mail(result, service)
                Mail.save_mail(**result)


def get_mail(mail_id, service=None):
    """
    It retrieves the mail data for the given mail id
    :param mail_id: User mail id
    :param service: mail connection
    :return: mail data
    """
    result = None
    if service is None:
        service = build_gmail_service()
    try:
        result = service.users().messages().get(userId='me', id=mail_id).execute()
    except Exception as err:
        print(f"Exception in get mail: {err}")
    return result


def parse_mail(mail, service):
    """
    Parse the given mail data and extract headers
    :param mail: mail data
    :param service: mail connection
    :return: returns the parsed mail data
    """
    result = {
        "attachments": []
    }
    mail_id = mail["id"]
    payload = mail["payload"]
    headers = payload["headers"]
    from_email = get_header_data(headers, "From")
    subject = get_header_data(headers, "Subject")
    to = get_header_data(headers, "To")
    cc = get_header_data(headers, "Cc")
    received_on = datetime.utcfromtimestamp(int(mail["internalDate"])/1000)
    parsed_payload_result = parse_payload(mail_id, payload, result, service)
    # result = parse_payload_parts(mail_id, payload_parts, result, service)
    result.update(id=mail_id, subject=subject, from_email=from_email, cc=cc, to=to,
                  received_on=received_on, **parsed_payload_result)
    return result


def parse_payload(mail_id, payload, result, service):
    """
    Parse the message payload data and extract attachments
    :param mail_id: user mail id
    :param payload: mail data
    :param result: result obj
    :param service: mail connection
    """
    mime_type = payload["mimeType"]
    if mime_type.startswith("multipart"):
        return parse_payload_parts(mail_id, payload["parts"], result, service)
    result[MIME_TYPE_TEXT_MAPPING[mime_type]] = decode_data(payload["body"]["data"])
    return result


def parse_payload_parts(mail_id, parts, result, service=None):
    """
    If the email body contains multimedia, then parse its parts
    :param mail_id: user mail id
    :param parts: multimedia parts
    :param result: object to store the results
    :param service: mail connection
    :return: It returns the parsed payload data
    """
    for part in parts:
        try:
            mime_type = part["mimeType"]
            filename = part["filename"]
            if mime_type.startswith("multipart"):
                parse_payload_parts(mail_id, part["parts"], result, service)
            elif filename:
                result["attachments"].append(process_attachment(mail_id, part["body"], filename, service))
            else:
                result[MIME_TYPE_TEXT_MAPPING[mime_type]] = decode_data(part["body"]["data"])
        except Exception as err:
            print("error in payload parts: ", err)
    return result


def process_attachment(mail_id, attachment, filename, service=None):
    """
    If mail body contains attachment, decode the data or if it contains attachment id then
    fetch the attachment using the id
    :param mail_id: user mail id
    :param attachment: attachment data
    :param filename: attachment filename
    :param service: mail connection
    :return: It returns the decoded attachment
    """
    if service is None:
        service = build_gmail_service()
    data = attachment.get("data")
    attachment.update(name=filename, id=attachment["attachmentId"])
    if data:
        attachment["data"] = decode_data(data)
        return attachment
    attachment["data"] = decode_data(get_attachment(mail_id, attachment["attachmentId"], service)["data"])
    return attachment


def get_attachment(mail_id, attachment_id, service=None):
    """Retrieve the attachment data for the given attachment id"""
    result = None
    if service is None:
        service = build_gmail_service()
    try:
        result = service.users().messages().attachments().get(userId='me', messageId=mail_id, id=attachment_id).execute()
    except Exception as err:
        print(f"Exception in get mail: {err}")
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_folder', help="Source folder from where the messages will be filtered",
                        default="inbox")
    args = parser.parse_args()
    list_mails()