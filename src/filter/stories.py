import json
import logging
import os
import sys
import time
import requests
import traceback

from urllib.parse import urlparse
from bs4 import BeautifulSoup
import click

from redis_pool import RedisPool


HN_URL = "https://news.ycombinator.com/news?p="
LOB_URL = "https://lobste.rs/page/"

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s %(levelname)-8s "
        "%(pathname)s::%(funcName)s:%(lineno)d: %(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def get_stories(page):
    """Scrapes hackernews stories and filters the collection."""
    log.debug("in")
    story_rows = []
    stories = []

    # fetch!
    hn_page = HN_URL + str(page)
    start_time = time.time()
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.36')
    }
    r = requests.get(hn_page, verify=True, headers=headers)
    end_time = time.time()
    log.info(f"{hn_page} response " f"in {end_time - start_time:.2f} seconds")

    souped_body = BeautifulSoup(r.text, "html.parser")

    try:
        storytable_html = souped_body("table")[2]
    except IndexError:
        raise Exception(
            "Can't find news story table. "
            "hackernews HTML format probably changed."
        )

    raw_stories = storytable_html.find_all("tr")

    story_duo = []
    for tr in raw_stories:
        # we want strings, not BeautifulSoup tag objects
        row = tr.encode("utf-8").decode("utf-8")
        if 'class="spacer"' in row:
            continue

        if 'class="morespace"' in row:
            break

        story_duo.append(tr)
        if len(story_duo) == 2:
            story_rows.append(story_duo)
            story_duo = []

    for story_row in story_rows:
        story = {}
        link_line = story_row[0]
        meta_line = story_row[1]

        try:
            links_in_line = len(link_line.find_all("a"))
            if links_in_line == 3:
                story["title"] = link_line.find_all("a")[1].string
                story["link"] = link_line.find_all("a")[1].get("href")
            else:
                # YC announcement
                story["title"] = link_line.find_all("a")[0].string
                story["link"] = link_line.find_all("a")[0].get("href")
                if not story["title"]:
                    # ASK HN
                    story["title"] = link_line.find_all("a")[1].string
                    story["link"] = link_line.find_all("a")[1].get("href")

            all_links = meta_line.find_all("a")
            if len(all_links) >= 3:
                story["comments_num"] = all_links[3].string.replace(
                    "\xa0comments", ""
                )
                if story["comments_num"] == "discuss":
                    story["comments_num"] == "0"

                story[
                    "comments_link"
                ] = "https://news.ycombinator.com/" + all_links[3].get("href")
            else:
                story["comments_num"] = 0
                story["comments_link"] = ""

            parsed_link = urlparse(story["link"])
            story["host"] = "{uri.netloc}".format(uri=parsed_link)
            if len(meta_line.find_all("span")) >= 2:
                story["points"] = meta_line.find_all("span")[1].string.replace(
                    " points", ""
                )
            else:
                story["points"] = "0"

        except IndexError as ie:
            log.info("IndexError on ", link_line, ie)
            traceback.log.info_exc()
            continue

        # Handle relative HN links
        if not story["link"].startswith("http"):
            story["link"] = HN_URL + story["link"]
        stories.append(story)

    log.debug("out")
    return stories


def get_lobster_stories(page):
    stories = []
    lob_page = LOB_URL + str(page)
    start_time = time.time()
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.36')
    }
    r = requests.get(lob_page, verify=True, headers=headers)
    end_time = time.time()
    log.info(f"{lob_page} response " f"in {end_time - start_time:.2f} seconds")

    soup = BeautifulSoup(r.text, "html.parser")
    lines = soup.find_all("div", {"class": "story_liner h-entry"})
    for line in lines:
        title_elem = line.find('a', class_='u-url')
        title = title_elem.get_text()
        link = title_elem['href']
        points = line.find('div', class_='score').get_text()
        comm_le = line.find(
            'a', href=lambda href: href and '/s/' in href)
        comm_link = comm_le['href'] if comm_le else ''
        comm_num = comm_le.get_text().split()[0] if comm_le else ''
        parsed_link = urlparse(link)

        story = {
            "title": title,
            "link": link,
            "points": points,
            "comments_link": "https://lobste.rs" + comm_link,
            "comments_num": comm_num,
            "host": "{uri.netloc}".format(uri=parsed_link)
        }
        stories.append(story)

    return stories


@click.command()
@click.option(
    "--pages",
    default=os.environ.get("NUM_PAGES", "5"),
    help="Number of HN pages to read each time",
)
@click.option(
    "--redishost",
    default=os.environ.get("REDIS_HOST", "localhost"),
    help="Redis host",
)
@click.option(
    "--redisport",
    default=os.environ.get("REDIS_PORT", "6379"),
    help="Redis port",
)
def main(pages, redishost, redisport):
    hn_pages = []
    lob_pages = []
    for page in range(1, int(pages) + 1):
        log.info(f"Reading HN page {page}")
        hn_pages.append([get_stories(page)])

        log.info(f"Reading Lobsters page {page}")
        lob_pages.append([get_lobster_stories(page)])

    with RedisPool(host=redishost, port=redisport) as red:
        log.info("Storing to redis")
        red.set('hn_pages', json.dumps(hn_pages))
        red.set('lob_pages', json.dumps(lob_pages))


if __name__ == "__main__":
    main()
