from typing import List, Literal, Optional
import os
import json
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from urllib.parse import urlparse, urljoin
from prompt_toolkit import print_formatted_text

from openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain_core.output_parsers import JsonOutputParser

from trafilatura.spider import focused_crawler

import lang_tools_test

class Employee(BaseModel):
    name: str = Field(..., description="REQUIRED: The name of the person.")
    title: str = Field(default=None, description="The title of the person.")
    position: str = Field(default=None, description="The position of the person.")
    location: str = Field(default=None, description="The location of the person.")


class WebsiteSummary(BaseModel):
    title: str = Field(
        ..., description="REQUIRED: The title of the website to summarize."
    )
    summary: str = Field(
        ..., description="REQUIRED: The summary of the website's content."
    )
    company_name: str = Field(..., description="REQUIRED: The name of the company.")
    industry: str = Field(
        default=None, description="The industry that this company is in."
    )
    employees: List[Employee] = Field(
        default=[], description="Any employees identified in the website."
    )
    value_proposition: str = Field(
        default=None, description="The value proposition of the company."
    )
    competition: List[str] = Field(
        default=None, description="Competing firms to the company."
    )


def fetch_and_extract_text(url):
    """
    Fetch HTML content from the URL and extract text.
    """
    print(f"Fetching and extracting text from {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check if the request was successful
        soup = BeautifulSoup(response.text, "html.parser")
        text_content = soup.get_text(separator=" ", strip=True)
        return text_content
    except requests.RequestException as e:
        print(f"Error fetching or parsing {url}: {e}")
        return ""


def get_all_website_links(url, max_urls=5):
    """
    Returns all URLs that is found on `url` in which it belongs to the same website
    """
    # All URLs of `url`
    urls = set()
    # Domain name of the URL without the protocol
    domain_name = urlparse(url).netloc
    # Send a HTTP request to the given URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return urls  # Return empty set on failure

    # Parse the content of the request with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    for a_tag in soup.findAll("a"):
        href = a_tag.attrs.get("href")
        if len(urls) >= max_urls:
            break
        # if href == "" or href is None:
        #     # href empty tag
        #     continue
        # Join the URL if it's relative (not absolute link)
        href = urljoin(url, href)
        parsed_href = urlparse(href)
        # Remove URL GET parameters, URL fragments, etc.
        href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path

        if href in urls:
            # Already in the set
            continue
        if domain_name not in href:
            # External link
            continue
        urls.add(href)
    return urls


def fetch_text(start_url, chain_type="map_reduce", max_urls=5):
    combined_text = ""
    crawler_results = focused_crawler(start_url, max_seen_urls=max_urls)
    print("CRAWLER RESULTS: ", crawler_results)
    urls, _ = crawler_results
    if not urls:
        urls = get_all_website_links(start_url, max_urls=max_urls)

    # urls = get_all_website_links(start_url, max_urls=max_urls)
    # urls=['https://dolphinstudios.co/']
    if len(urls) > 5:
        urls = list(urls)[:5]
    print("******URLS TO SCRAPE : ", urls)
    for url in urls:
        # print(url)
        text_content = fetch_and_extract_text(url)

        combined_text += " " + text_content  # Concatenate text from all URLs
    # call summarize_text funcion to get summerise
    # print(combined_text)
    return combined_text


def scrape(start_url, chain_type="map_reduce", max_urls=5):
    combined_text = ""
    crawler_results = focused_crawler(start_url, max_seen_urls=max_urls)
    print("CRAWLER RESULTS: ", crawler_results)
    urls, _ = crawler_results
    if not urls:
        urls = get_all_website_links(start_url, max_urls=max_urls)
    # urls=['https://dolphinstudios.co/']
    if len(urls) > 5:
        urls = list(urls)[:5]
    print("******URLS TO SCRAPE : ", urls)
    for url in urls:
        print(url)
        text_content = fetch_and_extract_text(url)

        combined_text += " " + text_content  # Concatenate text from all URLs
    # call summarize_text funcion to get summerise
    print(combined_text)
    summary = Summarize()

    if lang_tools_test.num_tokens_from_string(combined_text) > 14000:
        print(
            "Text too long to summarize individually, splitting into chunks and summarizing separately"
        )
        summarize_text_data = summary.summarize_webpage(
            combined_text, chain_type=chain_type
        )
    else:
        summarize_text_data = {
            "output_text": "This is the raw data of the company, based on their website"
            + str(combined_text)
        }

    parser = JsonOutputParser(pydantic_object=WebsiteSummary)

    # Set up a parser + inject instructions into the prompt template.
    parser = JsonOutputParser(pydantic_object=WebsiteSummary)

    prompt = PromptTemplate(
        template="Answer the user query.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | summary.llm | parser

    # Note: At this point, summarize_text_data is a dictionary containing the output from summarize_webpage
    formatted_summarize_text_data = chain.invoke(
        {"query": "Please report on this company: " + str(summarize_text_data)}
    )

    print("summarize", formatted_summarize_text_data)
    # After obtaining summarize_text_data from summarize_webpage

    print("-----------------------------------------------------")
    print(formatted_summarize_text_data.get("title"))

    # the format of the schemas.py objects - WebsiteSummary and Employee
    # # call websitesummary class for schema
    print("-----------------------------------------------------")
    website_summary = WebsiteSummary(**formatted_summarize_text_data)
    print(website_summary)
    print("-----------------------------------------------------")
    # must we fetch employee details
    print(website_summary.employees)
    return website_summary.dict()



class Summarize:
    def __init__(self):
        self.__apikey = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            openai_api_key=self.__apikey,
            model_name="gpt-4o",
            temperature=0.5,
            max_tokens=4000,
        )

    def summarize_webpage(
        self, text: str, chain_type: Literal["stuff", "refine", "map_reduce"]
    ) -> str:
        try:
            if text == "" or len(text) < 30:
                return {"message": "No text to summarize"}
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=6000, chunk_overlap=1000
            )
            chunks = text_splitter.create_documents([text])
            map_custom_prompt = """
            Summarize the following text in a clear and concise way:
            TEXT:`{text}`
            Brief Summary:
            """
            map_prompt_template = PromptTemplate(
                input_variables=["text"], template=map_custom_prompt
            )
            combine_custom_prompt = """
            Generate a summary of the following text that includes the following elements in json format:
            
            * A title that accurately reflects the content of the text.
            * The summary of the website's content in string.
            * The company_name in string
            * The industry that this company is in
            * extract list of all employee like team member ,directors,advisors details about there names ,position, make sure you are not summarize the members and not generate AI employee list.
            * The value preposition of the company
            * Information about competing firms may include details about their products, pricing strategies,  market share, customer base, marketing approaches, and any other factors that impact their competitiveness in the industry
            Text:`{text}`
            """
            combine_prompt_template = PromptTemplate(
                input_variables=["text"], template=combine_custom_prompt
            )
            if chain_type == "map_reduce":
                summary_chain = load_summarize_chain(
                    llm=self.llm,
                    chain_type=chain_type,
                    verbose=True,
                    map_prompt=map_prompt_template,
                    combine_prompt=combine_prompt_template,
                )
            else:
                # STUFF OR REFINE METHOD
                summary_chain = load_summarize_chain(
                    llm=self.llm, chain_type=chain_type, verbose=True
                )
            summary = summary_chain.invoke(chunks)
            if summary and "output_text" in summary and summary["output_text"].strip():
                # Ensure the output text is not empty and is valid JSON before parsing
                try:
                    return summary
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from output_text: {e}")
                    print(f"Invalid JSON: {summary['output_text']}")
                    # Return or handle invalid JSON (for example, you can return an error message)
                    return {"error": "Invalid JSON in output_text"}
            else:
                print("No valid output_text found in summary")
                # Return or handle missing output_text (for example, you can return an error message)
                return {"error": "No output_text found"}

        except Exception as e:
            raise e

