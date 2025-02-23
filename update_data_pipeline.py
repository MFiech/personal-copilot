import os
import json
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone as PineconeClient
from bs4 import BeautifulSoup
import re

# Step 1: Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_TOKEN")
if not pinecone_api_key:
    raise ValueError("PINECONE_API_TOKEN not found in environment variables")

# Step 2: Initialize Pinecone client
pc = PineconeClient(api_key=pinecone_api_key)
index_name = "poc-pm-copilot"
index = pc.Index(index_name)

# Step 3: Define cleaning and chunking functions
def clean_text(text):
    """Remove HTML tags and special characters from text."""
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    text = re.sub(r"[^a-zA-Z0-9\s.,]", "", text)
    text = " ".join(text.split())
    return text

def chunk_text(text, max_words=150):
    """Split text into chunks of max_words."""
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# Step 4: Load and process .txt files from data/ folder
data_folder = "data"
text_chunks = []
chunk_id = 0  # Unique ID counter

for filename in os.listdir(data_folder):
    if filename.endswith(".txt"):
        file_path = os.path.join(data_folder, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            cleaned_text = clean_text(text)
            chunks = chunk_text(cleaned_text)
            for chunk in chunks:
                text_chunks.append({"id": f"chunk_{chunk_id}", "text": chunk})
                chunk_id += 1

print(f"Processed {len(text_chunks)} chunks from {data_folder}/")

# Step 5: Generate embeddings with SentenceTransformers
model = SentenceTransformer("all-mpnet-base-v2")
embeddings = []

for chunk in text_chunks:
    embedding = model.encode(chunk["text"]).tolist()
    embeddings.append({"id": chunk["id"], "embedding": embedding, "text": chunk["text"]})

# Optional: Save embeddings locally for debugging
with open("embeddings.json", "w", encoding="utf-8") as f:
    json.dump(embeddings, f)

print(f"Generated embeddings for {len(embeddings)} chunks")

# Step 6: Upload embeddings to Pinecone
upsert_data = [(item["id"], item["embedding"], {"text": item["text"]}) for item in embeddings]
index.upsert(vectors=upsert_data)

print(f"Uploaded {len(upsert_data)} vectors to Pinecone index '{index_name}'")