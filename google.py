import os.path
from dotenv import load_dotenv
import requests

load_dotenv()



def google_search(query, num_results=5):

    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    print(search_engine_id)
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": search_engine_id, "q": query, "num": num_results}

    response = requests.get(url, params=params).json()
    # print(query, response)
    if "error" in response:
        return ["No results found due to error: " + response["error"]["message"]]
    if "items" not in response:
        return ["No results found"]
    returning_dict = [{} for i in response["items"]]
    for i, item in enumerate(response["items"]):
        returning_dict[i]["index"] = i
        returning_dict[i]["title"] = item.get("title", "")
        returning_dict[i]["link"] = item.get("link", "")
        returning_dict[i]["snippet"] = item.get("snippet", "")
        # returning_dict[i]["htmlFormattedUrl"] = item["htmlFormattedUrl"]

    return returning_dict

print(google_search("machine learning engineer job posting"))

"""#comment out the rest of the code to test the function 
for results in results:
    print(results["title"])
    print(results["link"])
    print(results["snippet"])
    print("----")   
    title = results["title"]
    link = results["link"]

    """