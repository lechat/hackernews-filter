#!/usr/bin/env python
import os
import json
import sys
import logging
from functools import wraps

import click
import bottle

from passlib.context import CryptContext

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketError
from bottle_login import LoginPlugin

from hn_filter_core import (
    get_hn_stories, get_lob_stories, filter_stories, find_user,
    register_user, update_filter, why_crap
)
import redis_pool


CONFIG_PATH = "./"
DEFAULT_FILTER_LINES = "filter.txt"
USER_FILE = "users.json"
REDIS_POOL = None

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s %(levelname)-8s "
        "%(pathname)s::%(funcName)s:%(lineno)d: %(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
# disable all loggers from different files
bottle_logger = logging.getLogger("bottle").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("asyncio.coroutines").setLevel(logging.ERROR)
logging.getLogger("websockets.server").setLevel(logging.ERROR)
logging.getLogger("websockets.protocol").setLevel(logging.ERROR)

log = logging.getLogger("hn-filter")

app = bottle.Bottle()
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "not_a_secret_at_all")
app.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
login = app.install(LoginPlugin())


def json_response(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        bottle.response.content_type = 'application/json'
        return route_func(*args, **kwargs)
    return wrapper


@login.load_user
def load_user(user_id):
    return find_user(user_id)


def user_filter():
    user = login.get_user()
    if user:
        return user["filter_lines"]

    return DEFAULT_FILTER_LINES


@app.route("/")
def index():
    bottle.response.headers["Content-Type"] = "text/html"
    return bottle.static_file("home_ws.html", root="src/views")


@app.route("/ws/<site>/<num_pages>")
def data_processing(site, num_pages):
    log.info(f"num pages: {num_pages}")
    wsock = bottle.request.environ.get("wsgi.websocket")
    if not wsock:
        bottle.abort(400, "Expected WebSocket request.")
    try:
        stories = []
        # Send progress updates until the data is ready
        for page in range(0, int(num_pages)):
            log.info(f"Reading page {page}")
            if site == "hn":
                page_stories = get_hn_stories(page)
            else:
                page_stories = get_lob_stories(page)

            stories.extend(page_stories)
            wsock.send(json.dumps({"type": "progress", "data": page}))

        data = filter_stories(stories, user_filter())

        wsock.send(json.dumps({"type": "data", "data": data}))

    except WebSocketError:
        pass


@app.route("/editcrap")
@json_response
def edit_crap():
    return {"filter": "".join(user_filter())}


@app.route("/savecrap", method="POST")
@json_response
def save_filter():
    filter_lines = bottle.request.forms.get("filter_lines")

    update_filter(login.get_user(), [
        x + "\n" for x in filter_lines.split("\n")
    ])
    return {"success": True}


@app.route("/showwhy", method="POST")
@json_response
def show_why():
    descr = bottle.request.forms.get("story")
    url = bottle.request.forms.get("url")

    why = why_crap(descr, url, user_filter())
    return {"why": why}


@app.route("/css/<filename>")
def css_files(filename):
    return bottle.static_file(filename, root="src/views/css")


@app.route("/webfonts/<filename>")
def fonts_files(filename):
    return bottle.static_file(filename, root="src/views/fonts")


@app.route("/js/<filename>")
def js_files(filename):
    return bottle.static_file(filename, root="src/views/js")


@app.route("/img/<filename>")
def img_files(filename):
    return bottle.static_file(filename, root="src/views/img")


@app.route("/favicon.ico")
def favicon():
    return bottle.static_file("y18.ico", root="src/views/img")


@app.route("/check_login_status")
@json_response
def check_login_status():
    user = login.get_user()
    if user:
        data = {"logged_in": True, "email": user["email"]}
    else:
        data = {"logged_in": False, "email": ""}

    return data


@app.route("/register", method="POST")
@json_response
def do_register():
    user_id = bottle.request.forms.get("email")
    pw = bottle.request.forms.get("pass")
    hashed_pw = app.pwd_context.hash(pw)

    register_user(
        user_id, hashed_pw, DEFAULT_FILTER_LINES
    )
    login.login_user(user_id)

    return {"success": True}


@app.route("/login", method="POST")
@json_response
def do_login():
    user_id = bottle.request.forms.get("email")
    pw = bottle.request.forms.get("pass")

    reg_user = find_user(user_id)
    if reg_user:
        if app.pwd_context.verify(pw, reg_user["password"]):
            login.login_user(user_id)
            return {"success": True}

    return {"success": False}


@app.route("/logout")
@json_response
def do_logout():
    login.logout_user()

    return {"success": True}


@click.command()
@click.option(
    "--port",
    default=os.environ.get("APP_PORT", "31337"),
    help="File path for filter.txt and user.json files",
)
@click.option(
    "--configpath",
    type=click.Path(exists=True),
    default=CONFIG_PATH,
    help="File path for filter.txt and user.json files",
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
def main(port, configpath, redishost, redisport):
    global CONFIG_PATH
    global DEFAULT_FILTER_LINES
    global USER_FILE
    global REDIS_POOL

    CONFIG_PATH = configpath

    with open(os.path.join(configpath, "filter.txt"), "r") as df:
        DEFAULT_FILTER_LINES = df.readlines()

    USER_FILE = os.path.join(configpath, "users.json")

    REDIS_POOL = redis_pool.RedisPool(host=redishost, port=redisport)

    log.info(f"Listening on {port}. Config path is {configpath}")

    server = pywsgi.WSGIServer(
        ("0.0.0.0", int(port)),
        app,
        handler_class=WebSocketHandler,
        log=pywsgi._NoopLog(),
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
