# Spark Memory Error Runbook

## Purpose
Investigate Spark jobs that fail because of memory pressure or executor failures.

## Symptoms
- OutOfMemoryError
- Java heap space
- Spark executor lost or unexpectedly terminated
- Frequent garbage collection or failed Spark tasks

## Investigation
1. Inspect Spark UI stages, failed tasks, executor logs, and memory metrics.
2. Check whether data volume increased or partitions became unusually large.
3. Investigate data skew, large joins, and excessive caching.
4. Review recent code, configuration, and input-data changes.
5. Determine whether the failure is isolated to one executor or affects the whole job.

## Remediation
1. Reduce unnecessary columns and filter data early.
2. Review partition sizing and investigate skewed keys.
3. Consider a broadcast join only when the smaller dataset safely fits in memory.
4. Unpersist cached data when it is no longer needed.
5. Adjust executor memory only after identifying the bottleneck and checking available resources.

## Validation
Rerun a safe test or controlled workload. Verify successful completion, executor stability, runtime, and memory usage.

## Safety
Do not blindly increase memory or repeatedly rerun an expensive job. Preserve logs and involve the service owner before high-impact changes.
