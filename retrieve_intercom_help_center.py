import requests
import os
from dotenv import load_dotenv

# Load Intercom API token
load_dotenv()
api_token = os.getenv("INTERCOM_API_TOKEN")
headers = {
    "Authorization": f"Bearer {api_token}",
    "Accept": "application/json"
}
base_url = "https://api.intercom.io"

# Create directory for Help Center articles
data_folder = "data/help_center"
if not os.path.exists(data_folder):
    os.makedirs(data_folder)

# Step 1: Fetch all collections from /help_center/collections
collections = {}
response = requests.get(f"{base_url}/help_center/collections", headers=headers)
if response.status_code == 200:
    collections_data = response.json()["data"]
    for collection in collections_data:
        collections[collection["id"]] = collection["name"]
    print("Collections:", collections)
else:
    print(f"Error fetching collections: {response.status_code}")

# Step 2: List all articles with proper pagination
all_articles = []
page_params = {"per_page": 50}
while True:
    response = requests.get(f"{base_url}/articles", headers=headers, params=page_params)
    if response.status_code != 200:
        print(f"Error listing articles: {response.status_code}")
        break
    data = response.json()
    all_articles.extend(data["data"])
    pages = data.get("pages", {})
    if pages and pages.get("next") and isinstance(pages["next"], dict) and "starting_after" in pages["next"]:
        page_params["starting_after"] = pages["next"]["starting_after"]
    else:
        break

# Step 3: Retrieve full article details and save as .txt
for article in all_articles:
    article_id = article["id"]
    response = requests.get(f"{base_url}/articles/{article_id}", headers=headers)
    if response.status_code != 200:
        print(f"Error retrieving article {article_id}: {response.status_code}")
        continue
    
    article_data = response.json()
    title = article_data["title"]
    body = article_data.get("body", "No content")
    language = article_data.get("translated_content", {}).get("language", "en") or "en"
    parent_id = article_data["parent_id"]
    print(f"Article {article_id} parent_id: {parent_id}")  # Debug

    # Get area from collections using parent_id
    area = collections.get(str(parent_id), "Uncategorized") if parent_id else "Uncategorized"

    # Prepare content with metadata
    content = (
        f"Title: {title}\n"
        f"Body: {body}\n"
        f"Metadata: source=HelpCenter, type=Article, language={language}, area={area}"
    )
    
    # Save to .txt file
    file_path = os.path.join(data_folder, f"article_{article_id}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Exported {len(all_articles)} articles to {data_folder}/")