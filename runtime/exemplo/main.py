from typing import Any
import re
from datetime import datetime, timedelta

def handler(input: dict, context: object) -> dict[str, float]:
    bytes_sent = input["net_io_counters_eth0-bytes_sent"]
    bytes_recv = input["net_io_counters_eth0-bytes_recv"]
    if bytes_sent + bytes_recv > 0:
        percent_network_egress = (bytes_sent / (bytes_sent + bytes_recv)) * 100
    else:
        percent_network_egress = 0.0

    memory_cached = input["virtual_memory-cached"]
    memory_buffers = input["virtual_memory-buffers"]
    memory_total = input["virtual_memory-total"]
    if memory_total > 0:
        percent_memory_cache = ((memory_cached + memory_buffers) / memory_total) * 100
    else:
        percent_memory_cache = 0.0

    cpu_utilization = [input[key] for key in input if key.startswith("cpu_percent-")]
    
    if "cpu_history" not in context.env:
        context.env["cpu_history"] = {i: [] for i in range(len(cpu_utilization))}
    
    avg_cpu_utilization = {}
    date_format = "%Y-%m-%d %H:%M:%S.%f"
    curTime = datetime.strptime(input["timestamp"], date_format)

    for i, utilization in enumerate(cpu_utilization):
        context.env["cpu_history"][i].append({"time": curTime, "value": utilization})
        
        while len(context.env["cpu_history"][i]) > 1:
            if abs(context.env["cpu_history"][i][-1]["time"] - context.env["cpu_history"][i][0]["time"]) > timedelta(minutes=1):
                context.env["cpu_history"][i].pop(0)
            else:
                break

        avg_cpu_utilization[f"avg-util-cpu{i}-1min"] = sum(
            entry["value"] for entry in context.env["cpu_history"][i]
        ) / len(context.env["cpu_history"][i])

    return {
        "percent-network-egress": percent_network_egress,
        "percent-memory-cache": percent_memory_cache,
        **avg_cpu_utilization
    }
