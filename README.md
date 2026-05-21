# 서울시립대학교 학칙 및 규정 검색 MCP 서버

본 프로젝트는 서울시립대학교의 학칙, 규정, 지침 등의 마크다운 문서들을 임베딩하여 벡터 데이터베이스를 구축하고, 이를 기반으로 시맨틱 검색(Semantic Search)을 제공하는 **MCP(Model Context Protocol) 서버**입니다.

## 폴더 구조 및 주요 파일

* **`regulations/`**: 대학 규정, 학칙, 지침 등이 담긴 마크다운(`.md`) 파일들이 저장된 디렉토리입니다.
* **`regulation_search_server.py`**: FastMCP 프레임워크를 기반으로 동작하는 검색 서버입니다. 실행 시 벡터 DB가 존재하지 않으면 `regulations` 폴더의 데이터를 읽어 자동으로 벡터 DB를 구축합니다.
* **`uos_regulations_qwen3/`**: 스크립트 실행 시 자동으로 생성되는 Chroma 벡터 데이터베이스 폴더입니다.

## 1. 사전 준비 (Ollama 및 임베딩 모델)

이 시스템은 로컬 환경에서 Ollama와 `qwen3-embedding` 모델을 사용하여 문서 임베딩을 수행합니다. 서버를 실행하기 전 반드시 해당 모델이 다운로드되어 있어야 합니다.

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3-embedding:latest
```

## 2. 가상환경 및 패키지 설치

파이썬 가상환경을 생성하고 필요한 패키지들을 설치합니다.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 최초 실행 및 벡터 DB 자동 구축

MCP 클라이언트에 등록하기 전, 수동으로 스크립트를 한 번 실행하여 **최초 벡터 DB를 구축**하는 것을 권장합니다. (데이터 양에 따라 시간이 소요될 수 있습니다.)

```bash
python regulation_search_server.py
```
* **작동 방식**: 스크립트는 `uos_regulations_qwen3` 경로를 확인하고, 폴더가 비어있거나 존재하지 않으면 `regulations/` 폴더 내의 `.md` 파일들을 읽어들여 텍스트를 분할(Chunking)하고 Chroma DB에 임베딩하여 저장합니다.

## 4. Gemini CLI 환경에서 MCP 서버 등록 및 사용하기

**Gemini CLI**의 커맨드라인 도구를 사용하여 서버를 간단하게 등록할 수 있습니다.

### 4-1. MCP 서버 등록 커맨드

터미널에서 아래 명령어를 실행하여 서버를 등록합니다. (반드시 **절대 경로**를 사용해 주세요.)

```bash
gemini mcp add university-regulations .venv/bin/python regulation_search_server.py
```
*(참고: 가상환경 파이썬 경로와 서버 스크립트 경로는 실제 환경의 절대 경로로 입력해 주세요.)*

### 4-2. 설정 파일 확인 (Manual Setup)

위의 커맨드를 실행하면 프로젝트 루트의 `.gemini/settings.json` 파일에 아래와 같이 서버 정보가 저장됩니다. 만약 수동으로 설정하고 싶다면 이 파일을 직접 편집할 수도 있습니다.

```json
{
  "mcpServers": {
    "university-regulations": {
      "command": ".venv/bin/python",
      "args": [
        "regulation_search_server.py"
      ]
    }
  }
}
```

### 4-3. 검색 테스트

등록이 완료되면 Gemini CLI를 실행(또는 재시작)한 후, 다음과 같이 자연어로 질문하여 규정 검색이 잘 동작하는지 테스트합니다.

```
User: 서울시립대학교 장학금 지급 기준에 대한 규정을 찾아줘.
```

Gemini CLI는 자동으로 등록된 `retrieve_regulations` 도구를 호출하여 관련 문서 조각들을 검색한 후, 그 내용을 바탕으로 사용자에게 답변을 제공하게 됩니다.
