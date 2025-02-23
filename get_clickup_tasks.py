import requests
from dotenv import load_dotenv
import os
import time

# Load API token
load_dotenv()
api_token = os.getenv("CLICKUP_API_TOKEN")
headers = {"Authorization": api_token}
base_url = "https://api.clickup.com/api/v2"

# Step 1: Get Space ID (replace with your Space ID if known)
space_id = "42504415"  # Your Space ID

# Step 2: Get all Lists in the Space
response = requests.get(f"{base_url}/space/{space_id}/list", headers=headers)
lists = response.json()["lists"]
list_ids = [lst["id"] for lst in lists]

# Step 3: Fetch tasks by creator with pagination
creator_id = 43131627  # Your creator ID
all_tasks = []

for list_id in list_ids:
    page = 0
    while True:
        params = {
            "archived": False,
            "include_closed": True,
            "subtasks": True,
            "page": page
        }
        response = requests.get(f"{base_url}/list/{list_id}/task", headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error fetching list {list_id}, page {page}: {response.status_code}")
            break
        
        tasks = response.json()["tasks"]
        if not tasks:  # No more tasks on this page
            break
        
        creator_tasks = [task for task in tasks if task["creator"]["id"] == creator_id]
        all_tasks.extend(creator_tasks)
        page += 1
        time.sleep(0.1)  # Small delay to avoid rate limits

# Step 4: Save tasks as .txt files in data/ folder
data_folder = "data"
if not os.path.exists(data_folder):
    os.makedirs(data_folder)

for task in all_tasks:
    task_content = (
        f"Task ID: {task['id']}\n"
        f"Name: {task['name']}\n"
        f"Description: {task.get('description', 'No description')}\n"
        f"Status: {task['status']['status']}\n"
        f"Creator: {task['creator']['username']}\n"
        f"Date Created: {task['date_created']}\n"
        f"Due Date: {task.get('due_date', 'N/A')}\n"
    )
    file_path = os.path.join(data_folder, f"task_{task['id']}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(task_content)

print(f"Exported {len(all_tasks)} tasks to {data_folder}/ folder as .txt files")