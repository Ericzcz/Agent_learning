import asyncio
import time
from statistics import mean

from openai import AsyncOpenAI

MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

CONCURRENCY_LEVELS = [1, 5, 10]
ROUNDS = 3

client = AsyncOpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
)


async def send_request(index: int) -> tuple[float, int]:
    start = time.perf_counter()

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Request {index}: Explain machine learning "
                    "in about 100 words."
                ),
            }
        ],
        temperature=0,
        max_tokens=128,
    )

    latency = time.perf_counter() - start

    output_tokens = 0
    if response.usage is not None:
        output_tokens = response.usage.completion_tokens or 0

    return latency, output_tokens


async def warm_up() -> None:
    print("Running warm-up request...")

    latency, output_tokens = await send_request(0)

    print(
        f"Warm-up finished: "
        f"latency={latency:.3f}s, "
        f"output_tokens={output_tokens}"
    )


async def run_one_round(
    num_requests: int,
    round_number: int,
) -> dict[str, float]:
    print(
        f"\n===== Concurrency {num_requests}, "
        f"Round {round_number} ====="
    )

    wall_start = time.perf_counter()

    tasks = [
        send_request(index)
        for index in range(1, num_requests + 1)
    ]

    results = await asyncio.gather(*tasks)

    wall_time = time.perf_counter() - wall_start

    latencies = [latency for latency, _ in results]
    total_output_tokens = sum(
        output_tokens
        for _, output_tokens in results
    )

    average_latency = mean(latencies)
    maximum_latency = max(latencies)
    request_throughput = num_requests / wall_time
    output_throughput = total_output_tokens / wall_time

    print(f"Requests: {num_requests}")
    print(f"Average latency: {average_latency:.3f}s")
    print(f"Maximum latency: {maximum_latency:.3f}s")
    print(f"Wall time: {wall_time:.3f}s")
    print(
        f"Request throughput: "
        f"{request_throughput:.3f} requests/s"
    )
    print(
        f"Output throughput: "
        f"{output_throughput:.3f} tokens/s"
    )
    print(f"Total output tokens: {total_output_tokens}")

    return {
        "average_latency": average_latency,
        "maximum_latency": maximum_latency,
        "wall_time": wall_time,
        "request_throughput": request_throughput,
        "output_throughput": output_throughput,
    }


async def benchmark_concurrency(
    num_requests: int,
) -> dict[str, float]:
    round_results = []

    for round_number in range(1, ROUNDS + 1):
        result = await run_one_round(
            num_requests=num_requests,
            round_number=round_number,
        )
        round_results.append(result)

    averaged_result = {
        "average_latency": mean(
            result["average_latency"]
            for result in round_results
        ),
        "maximum_latency": mean(
            result["maximum_latency"]
            for result in round_results
        ),
        "wall_time": mean(
            result["wall_time"]
            for result in round_results
        ),
        "request_throughput": mean(
            result["request_throughput"]
            for result in round_results
        ),
        "output_throughput": mean(
            result["output_throughput"]
            for result in round_results
        ),
    }

    return averaged_result


async def main() -> None:
    await warm_up()

    final_results = {}

    for concurrency in CONCURRENCY_LEVELS:
        result = await benchmark_concurrency(concurrency)
        final_results[concurrency] = result

    print("\n\n========== FINAL AVERAGE RESULTS ==========")

    print(
        f"{'Concurrency':<12}"
        f"{'Avg Latency':<15}"
        f"{'Max Latency':<15}"
        f"{'Wall Time':<15}"
        f"{'Req/s':<12}"
        f"{'Output Tok/s':<15}"
    )

    for concurrency, result in final_results.items():
        print(
            f"{concurrency:<12}"
            f"{result['average_latency']:<15.3f}"
            f"{result['maximum_latency']:<15.3f}"
            f"{result['wall_time']:<15.3f}"
            f"{result['request_throughput']:<12.3f}"
            f"{result['output_throughput']:<15.3f}"
        )


if __name__ == "__main__":
    asyncio.run(main())