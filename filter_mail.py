"""
This module, filter the messages for the from the given folder and apply the defined
actions

USAGE:
    e.g) python filter_mail inbox -p all --move_to_folder test --mark_as_read

    Above filters the messages from the user inbox that matches all the given conditions
    move the filtered messages to "test" folder and also mark the messages as read
"""

import json
import requests
import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mail_service import build_gmail_service


CONDITION_OPERATOR_MAP = {
    "in": "",
    "not_in": "-",
    "=": "+",
    "!=": "-",
    "<": "after",
    ">": "before"
}


def make_api_request(url, method, data=None):
    """
    Generic method to make api request
    :param url: resource url
    :param method: resource method
    :param data: data
    :return:
    """
    if data is None:
        data = {}
    headers = {
        "Authorization": f"Bearer {get_api_token()}"
    }
    return requests.request(method, url, data=data, headers=headers)


def get_api_token():
    """return api token or fetch new token if it is expired"""
    with open("token.json") as file_obj:
        data = json.load(file_obj)
    expiry = datetime.strptime(data["expiry"], "%Y-%m-%dT%H:%M:%S.%fZ")
    if datetime.utcnow() > expiry:
        build_gmail_service()
    return data["token"]


def filter_messages():
    """Filter the messages from the given folder and apply actions on the filtered messages"""
    resource = "https://www.googleapis.com/gmail/v1/users/me/messages?q"
    rule_predicate = args.predicate
    filter_query = f"in:{args.folder_to_filter}"
    with open("rules.json") as file_obj:
        rules = json.load(file_obj)
    for rule in rules:
        if rule["type"] == "duration":
            filter_query = handle_duration_rule(rule, filter_query)
            continue
        rule_filter_operator = CONDITION_OPERATOR_MAP[rule["condition"]]
        filter_query += f" {rule_filter_operator}{rule['name']}:{rule['value']}"
    print("filter query: ", filter_query)
    if rule_predicate == "any":
        filter_query = "{"+filter_query+"}"
    resource = f"{resource}={filter_query}"
    request = make_api_request(resource, "GET")
    if request.ok:
        response = request.json()
        if 'messages' in response:
            messages = response["messages"]
            message_ids = list(map(lambda message: message["id"], messages))
            apply_actions(message_ids)
        else:
            print("No messages found for the given filters")


def apply_actions(message_ids):
    """Apply actions on the filtered messages
    :param message_ids: List of messages to which the actions will be applied
    """
    resource = "https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify"
    data = {
        "ids": message_ids,
        "addLabelIds": [],
        "removeLabelIds": []
    }
    if args.mark_as_read:
        data["removeLabelIds"].append("UNREAD")
    if args.move_to_folder:
        data["addLabelIds"].append(get_folder_id_from_name(args.move_to_folder))
        data["removeLabelIds"].append(get_folder_id_from_name(args.folder_to_filter))
    request = make_api_request(resource, "POST", data)
    if request.ok:
        print("Actions applied successfully...")


def handle_duration_rule(rule, filter_query=""):
    """
    Handle duration type rule, calculate the date for the given duration
    :param rule: duration type rule
    :return: It returns filter query with date for the given duration
    """
    duration_range = rule["duration_in"]
    duration_value = rule["value"]
    rule_condition = rule["condition"]
    value = relativedelta()
    if duration_range == "days":
        value = relativedelta(days=duration_value)
    elif duration_range == "months":
        value = relativedelta(months=duration_value)
    filter_query += f" {CONDITION_OPERATOR_MAP[rule_condition]}:{(datetime.utcnow() - value).date()}"
    return filter_query


def get_folder_id_from_name(folder_name):
    """
    Get the folder id from the folder name
    :param folder_name: folder name
    :return: It returns the folder id for the given name
    """
    resource = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
    print("folder name: ", folder_name)
    request = make_api_request(resource, "GET")
    if request.ok:
        result = request.json()["labels"]
        for label in result:
            if label["name"] == folder_name:
                return label["id"]
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Filter the mails based on the configured rule and apply actions')
    parser.add_argument('folder_to_filter', help="Source folder from where the messages will be filtered")
    parser.add_argument('-p', '--predicate', action='store', choices=['all', 'any'],
                        help="Either filter based on all or any of the conditions", required=True)
    parser.add_argument('-m', '--move_to_folder', action="store", help="move the filtered messages to the given folder")
    parser.add_argument('-r', '--mark_as_read', action="store_true", help="mark the message as read")
    args = parser.parse_args()
    filter_messages()