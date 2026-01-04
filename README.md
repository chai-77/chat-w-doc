# chat-w-doc

## overview

agentic tool that makes going through documentation easier. minimalistic chatbot for going through code documentation.

## flow

1. **map**: provide base url to extract internal site structure.
2. **decide**: agent analyzes sitemap and identifies specific pages containing the answer.
3. **fetch**: crawl4ai retrieves content for only the selected pages.
4. **respond**: gemma 3 generates an answer from the retrieved markdown.
5. **reset**: context is cleared when switching queries or urls.


## dependencies

- python 3.10+
- ollama (running gemma3:4b)
- crawl4ai
- langchain-ollama
- playwright

## installation

```bash
# setup environment
python -m venv venv
venv\Scripts\activate

# install packages
pip install crawl4ai langchain-ollama playwright
playwright install

```
### usage
```Bash

python file_name.py

```
### output
```
set url: enters the mapping phase to discover documentation pages.

query: triggers the routing agent and multi-page crawler.

sub-options:

a: continue chat with current context.

b: new query (triggers new targeted crawl).

c: return to menu (wipes context).
```

### technical stack
```
orchestration: langchain

inference: ollama (gemma3:4b)

crawling: crawl4ai (asynchronous headless browser)
```

<br>

# disclaimer

``
rn the accurate.py is the best out of all. I will learn more about all this and update the others.
entirely vibe coded. i literally needed a tool like this to even build this :p
``

- fast.py: Quick syntax lookup. (Keyword search only).
- detailed.py: Learning concepts. (High context/wordy).
- accurate.py: The Best of both worlds. (Hybrid LLM-ranking).
- main.py: Baseline crawler + chat. (General-purpose, slower, exploratory).



<br>


## `` accurate.py``
### ✅ Use it for:
- Breaking Changes: (e.g., SQLAlchemy 1.x vs 2.0). Forces the AI to use the docs, not its old training data.
- Complex Logic: Distinguishing between similar methods (like .contents vs .descendants).
- Zero Hallucination: When you need the exact syntax to avoid breaking your database.

### ❌ Skip it if:
- You need an answer in under 2 seconds (Use fast.py).
- The site is just one giant page (The ranking engine will have nothing to "choose").