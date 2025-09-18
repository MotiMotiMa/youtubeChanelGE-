"""Fetch and categorize YouTube channel subscriptions.

This module authenticates with the YouTube Data API v3 using OAuth
credentials, retrieves the current user's subscriptions, derives a set of
genres from each subscribed channel's topic categories, and renders a memo-like
Markdown summary grouped by genre.

Usage:

    python youtube_subscriptions.py --client-secret client_secret.json \
        --output subscriptions_memo.md

Before running the script you must create OAuth client credentials for a
"Desktop" application in the `Google Cloud Console` and download the JSON file.
The script stores the OAuth token in `token.json` by default so subsequent runs
do not require re-authentication unless the token expires or the scope changes.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
from collections import defaultdict
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional
from urllib.parse import unquote, urlparse

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


@dataclasses.dataclass
class Subscription:
    """Basic information about a subscription."""

    channel_id: str
    title: str
    description: str
    channel_url: str


def load_credentials(client_secret: pathlib.Path, token_path: pathlib.Path) -> Credentials:
    """Load OAuth credentials, prompting the user if required."""

    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


def fetch_subscriptions(youtube) -> List[Subscription]:
    """Fetch all subscriptions for the authenticated user."""

    subscriptions: List[Subscription] = []
    request = youtube.subscriptions().list(
        part="snippet",
        mine=True,
        maxResults=50,
        order="alphabetical",
    )

    while request is not None:
        response = request.execute()
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            resource_id = snippet.get("resourceId", {})
            channel_id = resource_id.get("channelId")
            if not channel_id:
                continue
            subscriptions.append(
                Subscription(
                    channel_id=channel_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    channel_url=f"https://www.youtube.com/channel/{channel_id}",
                )
            )
        request = youtube.subscriptions().list_next(request, response)

    return subscriptions


def _chunked(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    chunk: List[str] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def fetch_channel_topics(youtube, channel_ids: Iterable[str]) -> Mapping[str, List[str]]:
    """Fetch topic categories for each channel ID."""

    topics: Dict[str, List[str]] = {}
    for batch in _chunked(channel_ids, 50):
        request = youtube.channels().list(
            part="snippet,topicDetails",
            id=",".join(batch),
            maxResults=50,
        )
        response = request.execute()
        for item in response.get("items", []):
            channel_id = item.get("id")
            if not channel_id:
                continue
            topic_details = item.get("topicDetails", {})
            topic_categories = topic_details.get("topicCategories", [])
            topics[channel_id] = topic_categories
    return topics


def readable_topic(topic_url: str) -> str:
    """Convert a topic category URL into a human readable string."""

    parsed = urlparse(topic_url)
    label = parsed.path.rsplit("/", maxsplit=1)[-1]
    label = label.replace("_", " ")
    return unquote(label or "Uncategorized")


def categorize_subscriptions(
    subscriptions: Iterable[Subscription],
    topics: Mapping[str, List[str]],
) -> Mapping[str, List[Subscription]]:
    """Group subscriptions by their most prominent topic category."""

    grouped: MutableMapping[str, List[Subscription]] = defaultdict(list)
    for subscription in subscriptions:
        topic_urls = topics.get(subscription.channel_id)
        if topic_urls:
            genre = readable_topic(topic_urls[0])
        else:
            genre = "Uncategorized"
        grouped[genre].append(subscription)
    return grouped


def render_markdown(grouped: Mapping[str, List[Subscription]]) -> str:
    """Render grouped subscriptions into a Markdown memo."""

    lines = ["# YouTube Subscriptions by Genre", ""]
    for genre in sorted(grouped):
        lines.append(f"## {genre}")
        lines.append("")
        for subscription in sorted(grouped[genre], key=lambda s: s.title.lower()):
            description = subscription.description.strip().replace("\n", " ")
            if description:
                lines.append(f"- [{subscription.title}]({subscription.channel_url}) — {description}")
            else:
                lines.append(f"- [{subscription.title}]({subscription.channel_url})")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_output(markdown: str, output_path: pathlib.Path) -> None:
    output_path.write_text(markdown, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-secret",
        required=True,
        type=pathlib.Path,
        help="Path to the OAuth client secret JSON file downloaded from the Google Cloud Console.",
    )
    parser.add_argument(
        "--token",
        type=pathlib.Path,
        default=pathlib.Path("token.json"),
        help="Path where the OAuth token should be stored (default: token.json).",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("subscriptions_memo.md"),
        help="Path to write the memo Markdown file (default: subscriptions_memo.md).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    creds = load_credentials(args.client_secret, args.token)
    youtube = build("youtube", "v3", credentials=creds)

    try:
        subscriptions = fetch_subscriptions(youtube)
        topics = fetch_channel_topics(youtube, (s.channel_id for s in subscriptions))
    except HttpError as exc:
        raise SystemExit(f"YouTube API request failed: {exc}") from exc

    grouped = categorize_subscriptions(subscriptions, topics)
    markdown = render_markdown(grouped)
    write_output(markdown, args.output)

    print(f"Wrote {len(subscriptions)} subscriptions to {args.output}")


if __name__ == "__main__":
    main()
