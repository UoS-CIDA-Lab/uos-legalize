import os
import glob
from tqdm import tqdm
from mcp.server.fastmcp import FastMCP
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

mcp = FastMCP("university_regulations_search")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_PATH = os.path.join(BASE_DIR, "uos_regulations_qwen3")
COLLECTION_NAME = "uos_regulations"
EMBEDDING_MODEL = "qwen3-embedding:latest"
MD_DIR = os.path.join(BASE_DIR, "regulations")

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)


def parse_frontmatter(content):
    meta = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2].strip()
            for line in frontmatter.split("\n"):
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


def initialize_vector_db():
    if os.path.exists(VECTOR_DB_PATH) and os.listdir(VECTOR_DB_PATH):
        print(f"Loading Vector Store from {VECTOR_DB_PATH}...")
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=VECTOR_DB_PATH,
        )
    print(f"Vector Store not found. Initializing from markdown files in {MD_DIR}...")
    md_files = glob.glob(os.path.join(MD_DIR, "*.md"))
    if not md_files:
        print(f"Warning: No markdown files found in {MD_DIR}.")
        raise FileNotFoundError(f"No markdown files found in {MD_DIR}.")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
    )
    documents = []
    for file_path in tqdm(md_files, desc="Reading and chunking markdown files"):
        base_title = os.path.splitext(os.path.basename(file_path))[0]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            meta, body = parse_frontmatter(content)
            title = meta.get("title", base_title)
            seq = meta.get("seq", "Unknown")
            chunks = text_splitter.split_text(body)
            for i, chunk in enumerate(chunks):
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "title": title,
                            "seq": seq,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "source": file_path,
                        },
                    )
                )
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    print(f"Total documents to embed: {len(documents)}")
    print("Starting embedding and saving to Chroma DB...")
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=VECTOR_DB_PATH,
    )
    batch_size = 50
    for i in tqdm(range(0, len(documents), batch_size), desc="Embedding Batches"):
        batch = documents[i : i + batch_size]
        vector_store.add_documents(batch)
    print(f"Successfully embedded {len(documents)} chunks into {VECTOR_DB_PATH}")
    return vector_store


vector_store = initialize_vector_db()


@mcp.tool()
def retrieve_regulations(query: str, k: int = 5) -> str:
    """
    Search for relevant university regulations and attachment documents based on a user's query.
    Returns the top k most relevant chunks of text.

    Args:
        query (str): The search query or user's question about university regulations.
        k (int): Number of relevant document chunks to retrieve. Defaults to 5.
    """
    try:
        results = vector_store.similarity_search(query, k=k)
        if not results:
            return "검색 결과가 없습니다."
        formatted_results = []
        formatted_results.append(f"'{query}'에 대한 검색 결과 {len(results)}건:\n")
        for i, doc in enumerate(results):
            meta = doc.metadata
            title = meta.get("title", "제목 없음")
            seq = meta.get("seq", "Unknown")
            chunk_idx = meta.get("chunk_index", 0)
            total_chunks = meta.get("total_chunks", 1)
            content = doc.page_content.strip()
            section = f"[{i + 1}] 규정명: {title} (SEQ: {seq})\n"
            section += f"정보: {chunk_idx + 1}/{total_chunks} 번째 섹션\n"
            section += f"내용:\n{content}\n"
            section += "-" * 50
            formatted_results.append(section)
        return "\n".join(formatted_results)
    except Exception as e:
        return f"검색 중 오류가 발생했습니다: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
