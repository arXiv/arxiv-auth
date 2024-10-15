"""
keycloak_tapir_bridge subscribes to the audit events from keycloak and updates the tapir db accordingly.
"""
import argparse
import signal
import threading
import typing
# from datetime import datetime, timedelta
# from pathlib import Path
from time import sleep, gmtime, strftime as time_strftime

import json
import os
import logging.handlers
import logging
import logging_json

from google.cloud.pubsub_v1.subscriber.message import Message
from google.cloud.pubsub_v1 import SubscriberClient

class JsonFormatter(logging_json.JSONFormatter):
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        return time_strftime("%Y-%m-%dT%H:%M:%S", ct) + ".%03d" % record.msecs + time_strftime("%z", ct)

    pass

RUNNING = True

logging.basicConfig(level=logging.INFO, format='(%(levelname)s): (%(asctime)s) %(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

LOG_FORMAT_KWARGS = {
    "fields": {
        "timestamp": "asctime",
        "level": "levelname",
    },
    "message_field_name": "message",
    # time.strftime has no %f code "datefmt": "%Y-%m-%dT%H:%M:%S.%fZ%z",
}

def signal_handler(_signal: int, _frame: typing.Any):
    """Graceful shutdown request"""
    global RUNNING
    RUNNING = False # Just a very negative int


# Attach the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def subscribe_keycloak_events(project_id: str, subscription_id: str, request_timeout: int) -> None:
    """
    Create a subscriber client and pull messages from the keycloak events

    Args:
        project_id (str): Google Cloud project ID
        subscription_id (str): ID of the Pub/Sub subscription
        request_timeout: request timeout
    """

    def handle_keycloak_event(message: Message) -> None:
        """Keycloak event handler
        the event looks like
        {
            "id" : "1e2abec5-bf62-42b1-a000-8773cf177fab",
            "time" : 1727796557187,
            "realmId" : "e9b31419-5843-4014-9bd1-f05a2df3b96b",
            "realmName" : "arxiv",
            "authDetails" : {
                "realmId" : "e34fe449-a841-4c0c-887d-a123a565d315",
                "realmName" : "master",
                "clientId" : "350cacca-500f-41a5-a1a2-ab57a0df45b4",
                "userId" : "84e2038c-3726-463d-a131-0d09c08c0829",
                "ipAddress" : "172.17.0.1"
            },
            "resourceType" : "REALM_ROLE_MAPPING",
            "operationType" : "DELETE",
            "resourcePath" : "users/28396986-0c90-42be-b39b-73f4714debaf/role-mappings/realm",
            "representation" : "[{\"id\":\"e6350ae5-2083-46ae-bed8-ba72e3c9dfcf\",\"name\":\"Test Role\",\"composite\":false}]",
            "resourceTypeAsString" : "REALM_ROLE_MAPPING"
        }

        Some events may not be interesting to Tapir
        """
        log_extra = {"service": "keycloak-tapir", "subscription": subscription_id}

        try:
            json_str = message.data.decode('utf-8')
        except UnicodeDecodeError:
            logger.error(f"bad data {str(message.message_id)}", extra=log_extra)
            message.nack()
            return

        print(json_str)

        try:
            data = json.loads(json_str)
        except Exception as _exc:
            logger.warning("bad(%s): %s", message.message_id, json_str, extra=log_extra)
            return

        # If this is not for arxiv realm, I don't care so eat it up and move on
        realm_name = data.get("realmName")
        if realm_name != "arxiv":
            logger.info("Not for arxiv - ack %s", data.get('id', '<no-id>'))
            message.ack()
            return

        message.ack()
        logger.info("ack %s", data.get('id', '<no-id>'))
        return

    subscriber_client = SubscriberClient()
    subscription_path = subscriber_client.subscription_path(project_id, subscription_id)
    streaming_pull_future = subscriber_client.subscribe(subscription_path, callback=handle_keycloak_event)
    log_extra = {"app": "kc-to-tapir"}
    logger.info("Starting %s %s", project_id, subscription_id, extra=log_extra)
    with subscriber_client:
        try:
            while RUNNING:
                sleep(0.2)
            streaming_pull_future.cancel()  # Trigger the shutdown
            streaming_pull_future.result(timeout=30)  # Block until the shutdown is complete
        except TimeoutError:
            logger.info("Timeout")
            streaming_pull_future.cancel()
        except Exception as e:
            logger.error("Subscribe failed: %s", str(e), exc_info=True, extra=log_extra)
            streaming_pull_future.cancel()
    logger.info("Exiting", extra=log_extra)


if __name__ == "__main__":
    # projects/arxiv-production/subscriptions/webnode-pdf-compilation
    ad = argparse.ArgumentParser(epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ad.add_argument('--project',
                    help='GCP project name. Default is arxiv-production',
                    dest="project", default="arxiv-production")
    ad.add_argument('--subscription',
                    help='Subscription name. Default is the one in production',
                    dest="subscription",
                    default="keycloak-arxiv-events-sub")
    ad.add_argument('--json-log-dir',
                    help='JSON logging directory. The default is correct on the sync-node',
                    default='/var/log/e-prints')
    ad.add_argument('--timeout', help='Web node request timeout',
                    default=10, type=int)
    ad.add_argument('--debug', help='Set logging to debug.',
                    action='store_true')
    args = ad.parse_args()

    project_id = args.project

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.json_log_dir and os.path.exists(args.json_log_dir):
        json_logHandler = logging.handlers.RotatingFileHandler(os.path.join(args.json_log_dir, "kc-to-tapir.log"),
                                                               maxBytes=4 * 1024 * 1024,
                                                               backupCount=10)
        json_formatter = JsonFormatter(**LOG_FORMAT_KWARGS)
        json_formatter.converter = gmtime
        json_logHandler.setFormatter(json_formatter)
        json_logHandler.setLevel(logging.DEBUG if args.debug else logging.INFO)
        logger.addHandler(json_logHandler)

    listeners = [
        threading.Thread(target=subscribe_keycloak_events, args=(project_id, args.subscription, args.timeout))
    ]

    for listener in listeners:
        listener.start()

    for listener in listeners:
        listener.join()

