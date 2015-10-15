"""

crawls lolibrary.org for new items

"""
import time
import sys
import re
import requests
from bs4 import BeautifulSoup
import argparse
import pymongo


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
    parser.add_argument(
            "-p",
            "--persist",
            dest="persist",
            action="store_true",
            help="persist the item data to the DB",
            )
    parser.add_argument(
            "-t",
            "--test-mode",
            dest="test_mode",
            action="store_true",
            help="run in test mode (uses test DB)"
            )
    parser.add_argument(
            "-b",
            "--bulk-load",
            dest="bulk_load",
            action="store_true",
            help="add items to DB in bulk instead of one at a time",
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

def is_shoe_page(url):
    return "/shoes/" in url

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
    data = re.sub(r".*?:", "", data) 
    data = data.strip()
    return data

def make_field_list(field, delimiter=","):
    return [f.strip() for f in field.split(delimiter) if f.strip()]

def get_images(soup):
    image_links = []
    pics_div = soup.find(class_="field-field-pics")
    if pics_div:
        images = pics_div.find_all("img")
        image_links.extend([img.get("src") for img in images if img.get("src")])
    return image_links

def get_title(soup):
    return clean_item_data(soup.find("h2", class_="title"))

def get_japanese_name(soup):
    return clean_item_data(soup.find(class_="field-field-altitle"))

def get_brand(soup):
    return clean_item_data(soup.find(class_="field-field-brand"))

def get_product_number(soup, is_shoes):
    if is_shoes:
        class_ = "field-field-shoeprodnumb"
    else:
        class_ = "field-field-productnumber"
    return clean_item_data(soup.find(class_=class_))

def get_item_type(soup, is_shoe):
    if is_shoe:
        return "Shoes"
    return clean_item_data(soup.find(class_="field-field-items"))

def get_price(soup):
    price = clean_item_data(soup.find(class_="field-field-price"))
    extra, currency, price = price.partition(u"\xa5")
    return (extra + currency, price)

def get_year(soup):
    year = clean_item_data(soup.find(class_="field-field-year"))
    try:
        return int(year)
    except ValueError:
        return 0

def get_colorways(soup, is_shoes):
    if is_shoes:
        class_ = "field-field-shoecolors"
    else:
        class_ = "field-field-colorways"
    return make_field_list(clean_item_data(soup.find(class_=class_)), "\n")

def get_other_notes(soup):
    return clean_item_data(soup.find(class_="field-field-featureshide"))

def get_features(soup):
    return clean_item_data(soup.find(class_="field-field-features"))

def get_measurements(soup):
    return {
            "bust":             clean_item_data(soup.find(class_="field-field-shopbust")),
            "waist":            clean_item_data(soup.find(class_="field-field-shopwaist")),
            "length":           clean_item_data(soup.find(class_="field-field-shoplength")),
            "shoulder_width":   clean_item_data(soup.find(class_="field-field-shopshoulderwidth")),
            "sleeve_length":    clean_item_data(soup.find(class_="field-field-shopsleevelength")),
            "cuff":             clean_item_data(soup.find(class_="field-field-shopcuff")),
            "shoe_height":      clean_item_data(soup.find(class_="field-field-shoe-height"))
        }

def get_shoe_material(soup):
    return clean_item_data(soup.find(class_="field-field-shoematerials"))

def get_shoe_finishes(soup):
    return clean_item_data(soup.find(class_="field-field-shoefinishes"))

def get_tags(soup):
    all_links = soup.find_all("a")
    tags = []
    for link in all_links:
        href = link.get("href")
        if href and "/category/tags/" in href and link.text:
            tags.append({
                "name": link.text.lower().strip(),
                "url":  make_absolute(link) 
            })
    return tags

def get_item_data(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    item_is_shoe = is_shoe_page(url)
    return {
        "url":              url,
        "name":             get_title(soup),
        "japanese_name":    get_japanese_name(soup),
        "brand":            get_brand(soup),
        "product_number":   get_product_number(soup, item_is_shoe),
        "item_type":        get_item_type(soup, item_is_shoe),
        "price":            get_price(soup),
        "year":             get_year(soup),
        "colors":           get_colorways(soup, item_is_shoe),
        "other_notes":      get_other_notes(soup),
        "features":         get_features(soup),
        "images":           get_images(soup),
        "measurements":     get_measurements(soup),
        "shoe_material":    get_shoe_material(soup),
        "shoe_finishes":    get_shoe_finishes(soup),
        "tags":             get_tags(soup)
    }

def print_item_data(data):
    for item in data:
        for key, value in item.iteritems():
            print "%s: " % key,
            if not value:
                print "\n",
                continue
            if type(value) is list:
                print "\n",
                for v in value:
                    print "\t" + v
            elif type(value) is dict:
                print "\n",
                for k, v in value.iteritems():
                    print "\t%s: %s" % (k, v)
            elif type(value) is tuple:
                for v in value:
                    print v,
                print "\n",
            else:
                print value
        print "\n\n",

def write_data(db, data, bulk_load=False):
    if not db:
        print_item_data(data)
        return len(data)
    try:
        if bulk_load:
            db.items.insert_many(data)
            written = len(data)
        else:
            written = 0
            for d in data:
                db.items.insert_one(d)
                written += 1
        return written
    except pymongo.errors.PyMongoError as e:
        print "persisting failed: %s" % e.message
    return 0

def set_up_db(run_in_test_mode):
    try:
        client = pymongo.MongoClient()
        if run_in_test_mode:
            db = client.lolibrary_test
        else:
            db = client.lolibrary
        index_info = db.items.index_information()
        if "url" not in index_info.keys():
            db.items.create_index("url", unique=True)
        return db
    except ConnectionFailure:
        return None

def main(args):
    parsed = get_parser().parse_args(args[1:])
    if parsed.persist:
        print "Connecting to DB for persisting data..."
        db = set_up_db(parsed.test_mode)
        if db is None:
            print "Failure to connect to DB: printing to stdout instead"
    else:
        print "Printing data to stdout"
        db = None
    if parsed.end_page < 0:
        end_page = get_end_page(make_search_url(parsed.start_page))
        if end_page < 0:
            end_page = parsed.start_page
    else:
        end_page = parsed.end_page
    written_items = 0
    all_items = []
    curr_page = parsed.start_page
    while curr_page <= end_page: 
        time.sleep(0.25)
        url = make_search_url(curr_page)
        print "Processing %s\n" % url
        res = requests.get(url)
        item_links = scrape_search_page(res)
        for link in item_links:
            data = get_item_data(link)
            if data:
                if parsed.bulk_load:
                    all_items.append(data)
                else:
                    written_items += write_data(db, [data], bulk_load=False)
        curr_page += 1
    if parsed.bulk_load:
        print "Attempting to bulk write %d items..." % len(all_items)
        written_items = write_data(db, all_items, bulk_load=True)
    print "Wrote data for %d items." % written_items

if __name__ == "__main__":
    main(sys.argv)
