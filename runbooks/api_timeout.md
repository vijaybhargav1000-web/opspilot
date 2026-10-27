# API Timeout Runbook

## Purpose
Investigate API requests or dependencies that exceed their time limits.

## Symptoms
- Request timeout
- Read timed out
- Connection timed out
- Deadline exceeded
- Increased latency or HTTP 504 responses

## Investigation
1. Identify the endpoint, request ID, timestamp, and timeout layer.
2. Check API latency, error rate, CPU, memory, and connection-pool metrics.
3. Inspect downstream database and service latency.
4. Review recent deployments, traffic increases, and network changes.
5. Determine whether the timeout occurs before or after the operation changes data.

## Remediation
1. Address the slow dependency or resource bottleneck.
2. Optimize expensive queries or calls when evidence supports it.
3. Apply bounded retries with backoff only for transient failures and safe operations.
4. Adjust timeouts only after understanding the latency budget.
5. Use rate limiting or controlled load shedding when necessary and approved.

## Validation
Send a controlled test request. Compare latency and error rate with the baseline, and check downstream health.

## Safety
Do not increase timeouts indiscriminately or retry non-idempotent operations without safeguards.
