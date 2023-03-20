import hashlib
import json
import re
import logging

from redis_pool import RedisPool


HN_URL = "https://news.ycombinator.com/news?p="
log = logging.getLogger(__name__)


def get_hn_stories(page):
    log.debug("in")
    one_page = []
    log.info(f"Reading page {page} from Redis")

    one_page = RedisPool().safe_read("hn_pages")
    one_page = json.loads(one_page)

    log.debug("out")
    return one_page[page][0]


def get_lob_stories(page):
    log.debug("in")
    one_page = []
    log.info(f"Reading page {page} from Redis")

    one_page = RedisPool().safe_read("lob_pages")
    one_page = json.loads(one_page)

    log.debug("out")
    return one_page[page][0]


def filter_stories(stories, filter_lines):
    """
    Filters HN stories.
    """
    result = {"good": [], "crap": []}
    log.debug("in")
    # suck in filter words
    patterns = set()
    for line in filter_lines:
        line = line.strip()
        # skip blank lines
        if len(line) < 3:
            continue
        # skip comments
        if re.match(r"^#", line):
            continue
        if re.match(r"^>", line):
            continue

        patterns.add(re.compile(line))

    patterns = frozenset(patterns)
    # combined_re = "(" + ")|(".join(patterns) + ")"
    # compiled_re = re.compile(combined_re)

    try:
        for story in stories:
            if any(
                patt.match(story["title"]) or patt.match(story["link"])
                for patt in patterns
            ):
                result["crap"].append(story)
            else:
                result["good"].append(story)
    except TypeError as te:
        log.warning(f"{story} {te}")

    result["gl"] = f"{len(result['good'])}"
    result["cl"] = f"{len(result['crap'])}"

    return result


def update_filter(user, filter_lines):
    with RedisPool() as red:
        red.hset(user["user_id"], "filter_lines", json.dumps(filter_lines))


def find_user(user_id):
    email_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
    with RedisPool() as red:
        user = red.hgetall(email_hash)
        if user:
            user = {
                k.decode("utf-8"): v.decode("utf-8") for k, v in user.items()
            }
            user["filter_lines"] = json.loads(user["filter_lines"])
            user["user_id"] = email_hash
            return user

    return {}


def register_user(user_id, pwd, filter_lines):
    email_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()

    with RedisPool() as red:
        red.hmset(email_hash, {
            "email": user_id,
            "password": pwd,
            "filter_lines": json.dumps(filter_lines)
        })


def why_crap(descr, url, filter_lines):
    """
    Filters HN stories.
    """
    # suck in filter words
    patterns = []
    section = ""
    for line in filter_lines:
        line = line.strip()
        # skip blank lines
        if len(line) < 3:
            continue
        # skip comments
        if re.match(r"^#", line):
            continue
        if re.match(r"^>", line):
            section = line
            continue

        patterns.append({
            "rex": re.compile(line),
            "section": section
        })

    for patt in patterns:
        if patt["rex"].match(descr) or patt["rex"].match(url):
            return patt["section"]

    return "unknown"
