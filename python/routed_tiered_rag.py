from langchain_ollama import ChatOllama
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from redis import Redis

import os
import json
import requests

"""
This implementation demonstrates a routed and tiered RAG system
running fully in local using Ollama.

It aims to show the various techniques used for RAG, such as:
- Vector storage and cache
- Task routing
- Metadata filtering
- Chunking

For simplicity, we use Chromadb as the vector storage and 
Redis as the hot cache.
"""


class ChatSession:
    def __init__(self, model):
        self.llm = ChatOllama(model=model)

    def _generate(self, prompt):
        return self.llm.invoke(prompt).content

    def ask(self, query):
        print("Prompt:\n", query, "\n")
        print("Response:\n", self._generate(prompt=query), "\n")


class ChromaVectorStore:
    def __init__(self, collection_name, embedding_model):
        self.chroma = Chroma(
            collection_name=collection_name,
            embedding_function=OllamaEmbeddings(model=embedding_model),
            host="localhost",
            port=8000
        )

    def similarity_search(self, query, top_k, filter):
        return self.chroma.similarity_search(query, k=top_k, filter=filter)

    def _ingest(self, docs):
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        self.chroma.add_documents(chunks)

    def add_required_documents(self):
        def download(url, file):
            if not os.path.exists(file):
                print("Downloading pdf from ", url)
                r = requests.get(url)
                with open(file, "wb") as f:
                    f.write(r.content)

        def load_pdf(path, doc_id):
            loader = PyPDFLoader(path)
            docs = loader.load()

            for d in docs:
                d.metadata.update({
                    "docId": doc_id,
                    "section": "speech"
                })

            return docs

        download(
            "https://www.govinfo.gov/content/pkg/DCPD-202200069/pdf/DCPD-202200069.pdf",
            "speech_2022.pdf"
        )
        download(
            "https://www.govinfo.gov/content/pkg/DCPD-202300086/pdf/DCPD-202300086.pdf",
            "speech_2023.pdf"
        )
        docs = (
                load_pdf("speech_2022.pdf", "state_union_2022")
                + load_pdf("speech_2023.pdf", "state_union_2023")
        )
        self._ingest(docs)


class RedisCache:
    def __init__(self):
        self.redis = Redis(host="localhost", port=6379, decode_responses=True)

    def lookup(self, key):
        val = self.redis.get(key)
        if val:
            return json.loads(val)
        return None

    def cache(self, key, docs):
        data = [d.page_content for d in docs]
        self.redis.setex(key, 3600, json.dumps(data))


class RAGChatSession(ChatSession):
    def __init__(self, vector_store, model):
        super().__init__(model)
        self.vector_store = ChromaVectorStore(collection_name=vector_store['collection_name'],
                                              embedding_model=vector_store['embedding_model'])
        self.cache = RedisCache()

    def check_routes(self, query):
        route_query = f"""
            You are a routing system.
            Choose which corpus is relevant for the query:
            Options:
                - state_union_2022
                - state_union_2023
                - both 
            Answer with ONLY one option.
            query: {query}
        """

        response = self._generate(route_query)

        if "2022" in response:
            return ["state_union_2022"]

        if "2023" in response:
            return ["state_union_2023"]

        return ["state_union_2022", "state_union_2023"]

    def retrieve(self, query, top_k=2):
        routes = self.check_routes(query)
        all_docs = []
        for route in routes:
            metadata_filter = {"docId": route}
            docs = self.vector_store.similarity_search(
                query,
                top_k,
                metadata_filter
            )
            all_docs.extend(docs)

        return all_docs

    def get_context(self, query):
        key = f"route:{query}"
        cached = self.cache.lookup(key)
        if cached:
            context = "\n".join(cached)
            print("Context (from cache):\n", context, "\n")
        else:
            docs = self.retrieve(query)
            context = "\n".join(d.page_content for d in docs)
            print("Context (from vector store):\n", context, "\n")
            self.cache.cache(key, docs)

        return context

    def ask(self, query):
        print("Prompt:\n", query, "\n")
        context = self.get_context(query)
        prompt = f"""
            Use ONLY the context to answer the query.
            Context: {context}
            Query:{query}
        """
        print("Response:\n", self._generate(prompt), "\n")


if __name__ == "__main__":
    q1 = "What projects were mentioned in 2022 speech by the President?"
    q2 = "What did the President say in 2023 about Afghanistan?"

    print("\n-------------")
    print("Chat Session")
    print("-------------")
    chat_session = ChatSession(model="gemma:2b")
    chat_session.ask(q1)
    chat_session.ask(q2)

    print("\n**********************************")
    print("Populating vector store for RAG...")
    print("**********************************")
    chroma_vector_store = ChromaVectorStore(collection_name="rag", embedding_model="embeddinggemma")
    chroma_vector_store.add_required_documents()

    print("\n-------------------")
    print("RAG Chat Session 1")
    print("-------------------")
    rag_chat_session_1 = RAGChatSession(model="gemma:2b",
                                        vector_store={"collection_name": "rag", "embedding_model": "embeddinggemma"})
    rag_chat_session_1.ask(q1)
    rag_chat_session_1.ask(q2)

    print("\n-------------------")
    print("RAG Chat Session 2")
    print("-------------------")
    rag_chat_session_2 = RAGChatSession(model="gemma:2b",
                                        vector_store={"collection_name": "rag", "embedding_model": "embeddinggemma"})
    rag_chat_session_2.ask(q1)
    rag_chat_session_2.ask(q2)
