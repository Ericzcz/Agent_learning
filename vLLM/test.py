from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
)

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-1.5B-Instruct",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant. Answer accurately and briefly.",
        },
        {
            "role": "user",
            "content": "What is the capital of France?",
        },
    ],
    temperature=0,
    max_tokens=100,
)

print(response.choices[0].message.content)