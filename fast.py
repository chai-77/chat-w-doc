import asyncio
from urllib.parse import urljoin
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


KEYWORDS = [
    "select", "insert", "update", "delete",
    "query", "orm", "session", "execute", "scalars"
]

BAD_PAGES = ["further_reading", "glossary", "index"]


class DetailedSearchAgent:
    def __init__(self, model_name="gemma3:4b"):
        self.llm = ChatOllama(model=model_name, temperature=0)
        self.available_links = []
        self.base_url = ""
        self.current_context = ""
        self.last_targets = []

    # --------------------------------------------------
    # MAP SITE (FAST, ONCE)
    # --------------------------------------------------
    async def map_site(self, url):
        self.base_url = url
        print(f"\n🔍 Mapping site structure: {url}")

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
            )

            links = result.links.get("internal", [])
            self.available_links = list(set(
                urljoin(self.base_url, (l.get("url") or l.get("href")))
                for l in links if l
            ))

        print(f"📍 Map Complete: {len(self.available_links)} pages found.")

    # --------------------------------------------------
    # FAST ROUTING (NO LLM)
    # --------------------------------------------------
    def _rank_links(self, question):
        q = question.lower().split()

        def score(url):
            u = url.lower()
            s = 0

            s += sum(2 for k in KEYWORDS if k in u)
            s += sum(1 for t in q if t in u)

            if any(b in u for b in BAD_PAGES):
                s -= 5

            return s

        ranked = sorted(self.available_links, key=score, reverse=True)
        return ranked[:2]

    # --------------------------------------------------
    # TARGETED CRAWL
    # --------------------------------------------------
    async def decide_and_crawl(self, question):
        print(f"\n🎯 Selecting pages for: {question}")

        self.last_targets = self._rank_links(question)
        if not self.last_targets:
            self.last_targets = [self.base_url]

        print(f"🕷️ Fetching: {self.last_targets}")
        self.current_context = ""

        config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            only_text=True,
            word_count_threshold=10,
            remove_overlay_elements=True,
            process_iframes=False,
            page_timeout=12000
        )

        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun_many(
                urls=self.last_targets,
                config=config
            )

            # IMPORTANT: arun_many returns LIST
            for r in results:
                if r.success:
                    self.current_context += (
                        f"\n--- SOURCE: {r.url} ---\n"
                        f"{r.markdown[:3500]}\n"
                    )
                    print(f"✔ Downloaded: {r.url}")

        print("✅ Context ready.")

    # --------------------------------------------------
    # CHAT (MINIMAL BY DEFAULT)
    # --------------------------------------------------
    def chat_with_data(self, question):
        wants_code = any(k in question.lower() for k in ["code", "example", "syntax"])

        ans_prompt = f"""
DOCUMENTATION CONTEXT:
{self.current_context}

QUESTION:
{question}

RULES:
- If score < threshold → refuse to answer, suggest pages to check instead
- Be concise and factual
- Explain conceptually unless code is explicitly requested
- Do NOT invent APIs
- If answer is missing, say so
"""

        if wants_code:
            ans_prompt += "\n- If code exists, show ONLY the relevant snippet\n"

        print("\n🤖 RESPONSE:\n")
        for chunk in self.llm.stream([HumanMessage(content=ans_prompt)]):
            print(chunk.content, end="", flush=True)

        print("\n\n🔗 Sources used:")
        for s in self.last_targets:
            print(f"- {s}")
        print("-" * 40)

    # --------------------------------------------------
    # MENU LOOP
    # --------------------------------------------------
async def main():
    agent = DetailedSearchAgent()

    while True:
        print("\n" + "═" * 40)
        print("1. Set Base URL (Map Site)")
        print("2. Exit")
        choice = input("Select: ").strip()

        if choice == "1":
            url = input("Enter Documentation URL: ").strip()
            await agent.map_site(url)

            while True:
                q = input("\n💬 QUERY: ").strip()
                if not q:
                    break

                await agent.decide_and_crawl(q)
                agent.chat_with_data(q)

                while True:
                    print("\nOPTIONS: (a) Follow-up | (b) New Query | (c) Change Site")
                    sub = input("Choice: ").lower()

                    if sub == "a":
                        f = input("\n💬 FOLLOW-UP: ")
                        agent.chat_with_data(f)
                    elif sub in ("b", "c"):
                        break

                if sub == "c":
                    break

        elif choice == "2":
            break


if __name__ == "__main__":
    asyncio.run(main())
