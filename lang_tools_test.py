from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Literal
import tiktoken
from dotenv import load_dotenv

load_dotenv()
import os

openai_api_key = os.environ.get("OPENAI_API_KEY")


# completion llm
llm = ChatOpenAI(
    openai_api_key=openai_api_key,
    model_name="gpt-3.5-turbo",
    temperature=0.1,
    max_tokens=500,
)


def summarize_text(
    text: str, chain_type: Literal["stuff", "refine", "map_reduce"]
) -> str:
    if text == "" or len(text) < 30:
        return "No text to summarize"
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=50)
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
    Generate a summary of the following text that includes the following elements:

    * A title that accurately reflects the content of the text.
    * An introduction paragraph that provides an overview of the topic.
    * Bullet points that list the key points of the text.
    * A conclusion paragraph that summarizes the main points of the text.

    Text:`{text}`
    """

    combine_prompt_template = PromptTemplate(
        input_variables=["text"], template=combine_custom_prompt
    )

    print("MAP PROMPT TEMPLATE", map_prompt_template)
    if chain_type == "map_reduce":
        summary_chain = load_summarize_chain(
            llm=llm,
            chain_type=chain_type,
            verbose=True,
            map_prompt=map_prompt_template,
            combine_prompt=combine_prompt_template,
        )
    else:
        # STUFF OR REFINE METHOD
        summary_chain = load_summarize_chain(
            llm=llm, chain_type=chain_type, verbose=True
        )

    print(f"summary_chain using {chain_type}")
    summary = summary_chain.run(chunks)
    print(summary)
    return summary


# # WIKIPEDIA API WRAPPER
def wikipedia_lookup(query, top_k_result=1, doc_content_chars_max=1000):
    api_wrapper = WikipediaAPIWrapper(
        top_k_result=top_k_result, doc_content_chars_max=doc_content_chars_max
    )
    wikipedia = WikipediaQueryRun(api_wrapper=api_wrapper)

    result = wikipedia.invoke(
        {
            "query": query,
        }
    )
    print(result)
    return result


# # DUCKDUCKGO API WRAPPER
def duckduckgo_lookup(query):
    search = DuckDuckGoSearchRun()
    output = search.invoke(query)
    print(output)
    return output


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
