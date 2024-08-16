from bs4 import BeautifulSoup
import requests
import json
import numpy as np
import requests
from requests.models import MissingSchema
import trafilatura
from trafilatura.spider import focused_crawler
from bs4.element import Comment

from .google import *


def beautifulsoup_extract_text_fallback(response_content):
    """
    This is a fallback function, so that we can always return a value for text content.
    Even for when both Trafilatura and BeautifulSoup are unable to extract the text from a
    single URL.
    """

    # Create the beautifulsoup object:
    soup = BeautifulSoup(response_content, "html.parser")

    # Finding the text:
    text = soup.find_all(text=True)

    # Remove unwanted tag elements:
    cleaned_text = ""
    blacklist = [
        "[document]",
        "noscript",
        "header",
        "html",
        "meta",
        "head",
        "input",
        "script",
        "style",
    ]

    # Then we will loop over every item in the extract text and make sure that the beautifulsoup4 tag
    # is NOT in the blacklist
    for item in text:
        if item.parent.name not in blacklist:
            cleaned_text += "{} ".format(item)

    # Remove any tab separation and strip the text:
    cleaned_text = cleaned_text.replace("\t", "")
    return cleaned_text.strip()


def crawl_web_page(url, max_urls=10):
    print("Crawling web page...", url)
    to_visit, known_urls = focused_crawler(
        url, max_seen_urls=max_urls, max_known_urls=100
    )
    print("Crawling complete. Extracting text from web pages...")
    all_text = []
    for url in to_visit:
        text = extract_text_from_single_web_page(url)
        print(text)
        all_text.append(text)
    return all_text


def extract_text_from_single_web_page(url):

    downloaded_url = trafilatura.fetch_url(url)
    try:
        a = trafilatura.extract(
            downloaded_url,
            output_format="json",
            with_metadata=True,
            include_comments=False,
            date_extraction_params={"extensive_search": True, "original_date": True},
        )
    except AttributeError:
        a = trafilatura.extract(
            downloaded_url,
            output_format="json",
            with_metadata=True,
            date_extraction_params={"extensive_search": True, "original_date": True},
        )
    if a:
        json_output = json.loads(a)
        return json_output["text"]
    else:
        try:
            resp = requests.get(url)
            # We will only extract the text from successful requests:
            if resp.status_code == 200:
                return beautifulsoup_extract_text_fallback(resp.content)
                # Handling for any URLs that don't have the correct protocol
            else:
                raw_text = requests.get(url).text
                print(
                    "Something broke with the trafilatura response, using beautifulsoup4 to extract text"
                )
                return text_from_html(raw_text)

        except MissingSchema:
            # Try grabbing what we can from the URL's text:
            raw_text = requests.get(url).text
            print("URL is missing a schema, using beautifulsoup4 to extract text")
            return text_from_html(raw_text)


def tag_visible(element):
    if element.parent.name in [
        "style",
        "script",
        "head",
        "title",
        "meta",
        "[document]",
    ]:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, "html.parser")
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)
    return " ".join(t.strip() for t in visible_texts)

