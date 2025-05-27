import aiohttp
import asyncio
import json

async def invoke_chute(prompt):
    api_token = "cpk_02eae620a5fb4ff0bdf2e65f5e613946.917e4dab6a7c504ca882cb76be6f8f33.haSvr6ZIhCtg3YEUxwDSxDkMED6nmT9E"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    body = {
        "model": "deepseek-ai/DeepSeek-V3-0324",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,  # Disable streaming for simplicity
        "max_tokens": 1024,
        "temperature": 0.7
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://llm.chutes.ai/v1/chat/completions",
            headers=headers,
            json=body
        ) as response:
            if response.status != 200:
                error = await response.text()
                return {"error": f"API request failed: {error}"}
            data = await response.json()
            return data["choices"][0]["message"]["content"]
        
# Run the function and print the response
async def main():
    prompt = "'does kruskal rely on greedy algo?'" +" this is a user prompt if its about kruskal algrothim return json response else don't respond give him an exuse"
        
    print(f"Prompt: {prompt}\nResponse:")
    response = await invoke_chute(prompt)
    print("\n\nFull Response:", response)  # Optional: Print the full response at the end

# Execute the async function
asyncio.run(main())
