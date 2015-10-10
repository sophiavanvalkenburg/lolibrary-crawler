"""

crawls lolibrary.org for new items

"""
import time
import sys
import re
import requests
from bs4 import BeautifulSoup
import argparse
from pprint import pprint

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

def scrape_search_page(res):
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

def clean_item_data(obj):
    if not obj:
        return ""
    data = obj.text
    data = re.sub(r".*:", "", data) 
    data = data.strip()
    return data

def make_field_list(field):
    return [f.strip() for f in field.split(",")]
    
def make_year(year):
    try:
        return int(year)
    except ValueError:
        return 0

def make_price(price):
    extra, currency, price = price.partition(u"\xa5")
    return (extra + currency, price)

def make_other_notes(notes):
    pass 

def get_item_data(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text)
    title = clean_item_data(soup.find("h2", class_="title"))
    japanese_name = clean_item_data(soup.find(class_="field-field-altitle"))
    brand = clean_item_data(soup.find(class_="field-field-brand"))
    product_number = clean_item_data(soup.find(class_="field-field-productnumber"))
    item_type = clean_item_data(soup.find(class_="field-field-items"))
    price = clean_item_data(soup.find(class_="field-field-price"))
    year = clean_item_data(soup.find(class_="field-field-year"))
    colorways = clean_item_data(soup.find(class_="field-field-colorways"))
    other_notes = clean_item_data(soup.find(class_="field-field-featureshide"))
    features = clean_item_data(soup.find(class_="field-field-features"))
    bust = clean_item_data(soup.find(class_="field-field-shopbust"))
    waist = clean_item_data(soup.find(class_="field-field-shopwaist"))
    length = clean_item_data(soup.find(class_="field-field-shoplength"))
    shoulder_width = clean_item_data(soup.find(class_="field-field-shopshoulderwidth"))
    sleeve_length = clean_item_data(soup.find(class_="field-field-shopsleevelength"))
    cuff = clean_item_data(soup.find(class_="field-field-shopcuff"))
    main_image = soup.find(class_="imagefield-field_teaserimage").get("src") 
    return {
        "name":             title,
        "japanese_name":    japanese_name,
        "brand":            brand,
        "product_number":   product_number,
        "item_type":        item_type,
        "price":            make_price(price),
        "year":             make_year(year),
        "colorways":        make_field_list(colorways),
        "other_notes":      other_notes,
        "features":         make_field_list(features),
        "image_main":       main_image,
        "measurements":     {
            "bust":             bust,
            "waist":            waist,
            "length":           length,
            "shoulder_width":   shoulder_width,
            "sleeve_length":    sleeve_length,
            "cuff":             cuff
        },
    }

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
        item_links = scrape_search_page(res)
        item_data = {}
        for link in item_links:
            data = get_item_data(link)
            if data:
                item_data[link] = data
        pprint(item_data)
        curr_page += 1

if __name__ == "__main__":
    main(sys.argv)
