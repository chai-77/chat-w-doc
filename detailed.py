import asyncio
from urllib.parse import urljoin
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

class DetailedSearchAgent:
    def __init__(self, model_name="gemma3:4b"):
        self.llm = ChatOllama(model=model_name, temperature=0)
        self.available_links = [] 
        self.base_url = ""
        self.current_context = "" 
        self.last_targets = []

    async def map_site(self, url):
        self.base_url = url
        print(f"\n🔍 Mapping site structure: {url}")
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            links = result.links.get("internal", [])
            self.available_links = [urljoin(self.base_url, (l.get('url') or l.get('href'))) for l in links]
            self.available_links = list(set([l for l in self.available_links if l]))
            print(f"📍 Map Complete: {len(self.available_links)} potential pages found.")

    async def decide_and_crawl(self, question):
        print(f"\n🎯 Planning targeted crawl for: '{question}'")
        
        # We ask for 2 pages to get a more elaborate context
        pick_prompt = f"""
        User Question: {question}
        Sitemap: {self.available_links[:60]}
        
        TASK: Pick the 2 most relevant URLs that contain technical setup, metadata, or definitions.
        RULE: Return ONLY the URLs separated by a comma. No conversation.
        """
        pick_res = self.llm.invoke([HumanMessage(content=pick_prompt)])
        
        raw = pick_res.content.replace("```", "").strip()
        self.last_targets = [u.strip() for u in raw.split(",") if "http" in u][:2]

        if not self.last_targets:
            self.last_targets = [self.base_url]

        print(f"🕷️ Fetching: {self.last_targets}")
        self.current_context = "" 
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, 
            stream=True,
            only_text=True, 
            word_count_threshold=10,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun_many(urls=self.last_targets, config=config)
            async for r in results:
                if r.success: 
                    # 5000 chars per page provides more detail for the "elaborate" response
                    content = r.markdown[:8000] 
                    self.current_context += f"\n--- SOURCE: {r.url} ---\n{content}\n"
                    print(f"✔ Downloaded: {r.url}")
        
        print(f"✅ Context ready.")

    def chat_with_data(self, question):
        print("\n🤖 RESPONSE:")
        # Stricter prompt to stop hallucinations while being detailed
        ans_prompt = f"""
        CONTEXT: {self.current_context}
        QUESTION: {question}

        TASK: Provide an exhaustive guide. 
        1. Explain the theory.
        2. Provide a full, runnable code example.
        3. List edge cases mentioned in the docs.

        RULES:
        1. Answer the question step-by-step using the context above.
        2. Use EXACT code syntax from the context. Do not invent methods.
        3. If the answer is not in the context, say "The current pages do not contain the specific answer." 
        4. Then suggest 2-3 other URLs from this sitemap that might help: {self.available_links[:15]}
        """
        
        full_response = ""
        for chunk in self.llm.stream([HumanMessage(content=ans_prompt)]):
            print(chunk.content, end="", flush=True)
            full_response += chunk.content
        
        print(f"\n\n🔗 Sources used: {', '.join(self.last_targets)}")
        print("-" * 30)
        return full_response

async def main():
    agent = DetailedSearchAgent(model_name="gemma3:4b") 
    
    while True:
        print("\n" + "═"*40)
        print("1. Set Base URL (Map Site)")
        print("2. Exit")
        choice = input("Select: ")

        if choice == "1":
            url = input("Enter Documentation URL: ").strip()
            await agent.map_site(url)
            
            while True:
                q = input("\n💬 QUERY: ")
                await agent.decide_and_crawl(q)
                agent.chat_with_data(q)

                while True:
                    print("\nOPTIONS: (a) Follow-up | (b) New Query | (c) Change Site")
                    sub = input("Choice: ").lower()
                    if sub == 'a':
                        f_up = input("\n💬 FOLLOW-UP: ")
                        agent.chat_with_data(f_up)
                    elif sub in ['b', 'c']:
                        break
                if sub == 'c':
                    break
        elif choice == "2":
            break

if __name__ == "__main__":
    asyncio.run(main())