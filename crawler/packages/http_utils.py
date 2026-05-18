from __future__ import annotations

import random
import time
from typing import Optional
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session(*, user_agent: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    retry = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def load_robots(*, session: requests.Session, base_url: str) -> RobotFileParser:
    robots_url = urljoin(base_url, "/robots.txt")
    rp = RobotFileParser()
    rp.set_url(robots_url)

    try:
        resp = session.get(robots_url, timeout=30)
        if resp.status_code >= 400:
            rp.parse(["User-agent: *", "Disallow: /"])
            return rp
        rp.parse(resp.text.splitlines())
        return rp
    except requests.RequestException:
        rp.parse(["User-agent: *", "Disallow: /"])
        return rp


def polite_sleep(delay_seconds: float) -> None:
    if delay_seconds <= 0:
        return
    jitter = random.uniform(0.0, min(0.5, delay_seconds))
    time.sleep(delay_seconds + jitter)
