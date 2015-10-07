"""

crawls lolibrary.org for new items

"""
import time
import sys
import re
import requests
from bs4 import BeautifulSoup
import argparse

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            "-s",
            "--start-page",
            dest="start_page",
            type=int,
            help="start crawling on this page",
            default=0
            )
    parser.add_argument(
            "-e",
            "--end-page",
            dest="end_page",
            type=int,
            help="end crawling on this page",
            default=-1
            )
    return parser


def link_is_valid(link):
    href = link.get("href")
    if href is None:
        return False
    if "#comment" in href:
        return False
    if link.get("class") is not None:
        return False
    if "/apparel/" not in href and "/shoes/" not in href:
        return False
    return True

def make_absolute(link):
    return "http://www.lolibrary.org" + link.get("href")

def crawl_one_page(res):
    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.find_all(link_is_valid)
    item_links = [
            make_absolute(link)
            for link in links
            ]
    return item_links

def get_end_page(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    last_link = soup.find(class_="pager-last")
    if last_link is None or last_link.a is None:
        return -1
    last_href = last_link.a.get("href")
    m = re.search(r"page=(\d+)$", last_href)
    if m:
        return int(m.group(1))
    return -1

def make_search_url(page):
    return "http://www.lolibrary.org/node?page=%d" % page

def main(args):
    parsed = get_parser().parse_args(args[1:])
    if parsed.end_page < 0:
        end_page = get_end_page(make_search_url(parsed.start_page))
        if end_page < 0:
            end_page = parsed.start_page
    else:
        end_page = parsed.end_page
    curr_page = parsed.start_page
    while curr_page <= end_page: 
        time.sleep(0.5)
        res = requests.get(make_search_url(curr_page))
        item_links = crawl_one_page(res)
        for link in item_links: print link
        curr_page += 1

if __name__ == "__main__":
    main(sys.argv)
