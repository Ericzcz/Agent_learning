from prometheus_client import start_http_server, disable_created_metrics
from prometheus_client import Summary, Counter, Histogram, Info
import random
import time

# FastAPI
# from fastapi import FastAPI
# from prometheus_fastapi_instrumentator import Instrumentator
# app = FastAPI()
# Instrumentator().instrument(app).expose(app)

disable_created_metrics()


# Counter
API_REQUESTS = Counter(
    "api_requests_total",
    "Total number of API requests",
    labelnames=["endpoint", "status"],
    namespace="myapp"
)

# Gauge 相对 Counter 可以减 可以设定成特定值
# gauge.set_to_current_time() 把值设成当前 Unix 时间戳，常用来记录“上次成功执行时间”。

# Summary
# 1. REQUEST_TIME.observe(0.8) 手动记录一次
# 2. 也可以像下面的 自动计时
REQUEST_TIME = Summary(
    "request_processing_seconds",
    "Time spent processing request"
)

# Histogram
# 记录的是 小于等于某个bucket的值 buckets最后自动加上"+Inf"
# 用法在下面
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    labelnames=["endpoint", "method"],
    buckets=[1, 2, 5, 10, 20, 30, 60],
)

BUILD_INFO = Info(
    'build',
    'Application build information',
    namespace='myapp',
)
BUILD_INFO.info({
    'version': '1.4.2',
    'revision': 'abc123def456',
    'branch': 'main',
    'build_date': '2024-01-15',
})


# 还可以计算p95
# 注意：下面是 PromQL，不是 Python 代码
# 需要放在 Prometheus Web UI 或 Grafana 的查询框中
#
# histogram_quantile(
#   0.95,
#   sum by (le) (
#     rate(request_latency_seconds_bucket[5m])
#   )
# )
#
# histogram_quantile(
#   0.95,
#   sum by (le, endpoint) (
#     rate(request_latency_seconds_bucket[5m])
#   )
# )


# Decorate function with metric.
@REQUEST_TIME.time()
def process_request(t):
    """A dummy function that takes some time."""
    
    if t > 5:
        API_REQUESTS.labels(
            endpoint="demo",
            status="larger_than_5"
        ).inc()
    else:
        API_REQUESTS.labels(
            endpoint="demo",
            status="less_than_or_equal_to_5"
        ).inc()

    with REQUEST_LATENCY.labels(
        endpoint="/local_query",
        method="POST",
    ).time():
        # run your function here
        print("abcdefg")
        time.sleep(t)


if __name__ == "__main__":
    # Start up the server to expose the metrics.
    start_http_server(8000)

    # Generate some requests.
    while True:
        process_request(random.uniform(0, 10))