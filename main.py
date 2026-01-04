import asyncio
from urllib.parse import urljoin
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

class FastLocalAgent:
    def __init__(self, model_name="gemma3:4b"):
        # Temperature 0 keeps it focused; streaming enabled for speed
        self.llm = ChatOllama(model=model_name, temperature=0)
        self.available_links = [] 
        self.base_url = ""
        self.current_context = "" 

    async def map_site(self, url):
        self.base_url = url
        print(f"\n🔍 Mapping site structure: {url}")
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            links = result.links.get("internal", [])
            self.available_links = []
            for l in links:
                link_url = l.get('url') or l.get('href')
                if link_url:
                    # Fix relative links (e.g., /tutorial -> https://site.com/tutorial)
                    full_url = urljoin(self.base_url, link_url)
                    self.available_links.append(full_url)
            
            self.available_links = list(set(self.available_links))
            print(f"📍 Map Complete: {len(self.available_links)} potential pages found.")

    async def decide_and_crawl(self, question):
        """Phase 1: Decision & Fast Multi-page Crawl"""
        print(f"\n🎯 Planning targeted crawl for: '{question}'")
        
        pick_prompt = f"""
        User Question: {question}
        Sitemap: {self.available_links[:50]}
        
        TASK: Pick the 2 most relevant URLs.
        RULE: Return ONLY the URLs separated by a comma.
        """
        pick_res = self.llm.invoke([HumanMessage(content=pick_prompt)])
        
        # Clean the output from Gemma
        raw = pick_res.content.replace("```", "").strip()
        targets = [u.strip() for u in raw.split(",") if "http" in u][:2] # Limited to 2 for speed

        if not targets:
            targets = [self.base_url]

        print(f"🕷️ Fetching: {targets}")
        self.current_context = "" 
        
        # Optimized config: only_text=True makes the 'Thinking' part MUCH faster
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, 
            stream=True,
            only_text=True, 
            word_count_threshold=10
        )
        
        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun_many(urls=targets, config=config)
            async for r in results:
                if r.success: 
                    # Clean the markdown slightly to save tokens
                    content = r.markdown[:8000] # Limit per-page characters
                    self.current_context += f"\n--- SOURCE: {r.url} ---\n{content}\n"
                    print(f"✔ Downloaded: {r.url}")
        
        print(f"✅ Context ready.")

    def chat_with_data(self, question):
        """Phase 2: Streaming Inference (Immediate Visual Feedback)"""
        print("\n🤖 RESPONSE:")
        ans_prompt = f"""
        Context:
        {self.current_context}
        
        Question: {question}
        
        Answer based on the context. List sources at the end.
        """
        
        full_response = ""
        # Use .stream to avoid the long 'Thinking' wait
        for chunk in self.llm.stream([HumanMessage(content=ans_prompt)]):
            print(chunk.content, end="", flush=True)
            full_response += chunk.content
        
        print("\n" + "-"*30)
        return full_response

async def main():
    agent = FastLocalAgent(model_name="gemma3:4b") 
    
    while True:
        print("\n" + "═"*40)
        print("1. Set Base URL (Map Site)")
        print("2. Exit")
        choice = input("Select: ")

        if choice == "1":
            url = input("Enter Documentation URL: ").strip()
            await agent.map_site(url)
            
            while True:
                q = input("\n💬 NEW QUERY (Crawls Fresh Data): ")
                await agent.decide_and_crawl(q)
                agent.chat_with_data(q)

                while True:
                    print("\nOPTIONS:")
                    print("a. Follow-up (Use same data)")
                    print("b. New Query (Crawl new pages)")
                    print("c. Menu (Change URL)")
                    sub = input("Choice: ").lower()

                    if sub == 'a':
                        follow_up = input("\n💬 FOLLOW-UP: ")
                        agent.chat_with_data(follow_up)
                    elif sub == 'b':
                        break 
                    elif sub == 'c':
                        break
                    
                if sub == 'c':
                    break
        elif choice == "2":
            break

if __name__ == "__main__":
    asyncio.run(main())