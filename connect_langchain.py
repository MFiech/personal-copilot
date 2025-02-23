import os
from dotenv import load_dotenv
from langchain_pinecone import PineconeVectorStore  # Updated Pinecone integration
from langchain_huggingface import HuggingFaceEmbeddings  # Updated embeddings
from langchain_huggingface import HuggingFacePipeline  # Updated LLM pipeline
from langchain.chains import RetrievalQA
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from pinecone import Pinecone as PineconeClient

# Step 1: Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_TOKEN")
if not pinecone_api_key:
    raise ValueError("PINECONE_API_TOKEN not found in environment variables")

# Step 2: Initialize Pinecone client
pc = PineconeClient(api_key=pinecone_api_key)
index_name = "poc-pm-copilot"
index = pc.Index(index_name)

# Step 3: Set up SentenceTransformers embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

# Step 4: Initialize the vector store
vectorstore = PineconeVectorStore(
    index=index,
    embedding=embeddings,
    text_key="text",
    pinecone_api_key=pinecone_api_key
)

# Step 5: Set up a smaller, faster Hugging Face LLM (TinyLlama)
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=50,  # Reduced for speed
    device=-1  # Use CPU; set to 0 or higher for GPU if available
)
llm = HuggingFacePipeline(pipeline=pipe)

# Step 6: Create RetrievalQA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3})
)

# Step 7: Test it with a command-line interface
while True:
    query = input("Ask your Co-Pilot (or type 'exit' to quit): ")
    if query.lower() == "exit":
        break
    print("Thinking...")
    response = qa_chain.invoke(query)["result"]  # Updated to invoke
    print("Co-Pilot:", response)