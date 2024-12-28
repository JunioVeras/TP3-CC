import os
import redis
import streamlit as st
import json
import time
import matplotlib.pyplot as plt
import pandas as pd
from collections import deque

redis_key = os.getenv("REDIS_OUTPUT_KEY", "default-key")
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

st.title("Monitoring Dashboard")

st.sidebar.header("Settings")
refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 1, 60, 5)
history_length = st.sidebar.slider("History length (seconds)", 10, 300, 60)

time_history = deque(maxlen=history_length)
cpu_history = {f'cpu{i}': deque(maxlen=history_length) for i in range(8)}
network_history = deque(maxlen=history_length)
memory_cache_history = deque(maxlen=history_length)

def plot_cpu_usage():
    plt.figure(figsize=(10, 5))
    for i in range(8):
        plt.plot(time_history, cpu_history[f'cpu{i}'], label=f'CPU {i}')
    plt.xlabel('Time')
    plt.ylabel('CPU Usage (%)')
    plt.title('Average CPU Usage per Core (60 seconds)')
    plt.legend(loc='upper left')
    st.pyplot(plt)

def plot_network_usage():
    plt.figure(figsize=(10, 5))
    plt.plot(time_history, network_history, label='Network Egress', color='lightgreen')
    plt.xlabel('Time')
    plt.ylabel('Percent (%)')
    plt.title('Network Egress Usage')
    plt.legend(loc='upper left')
    st.pyplot(plt)

def plot_memory_cache():
    plt.figure(figsize=(10, 5))
    plt.plot(time_history, memory_cache_history, label='Memory Cache', color='lightcoral')
    plt.xlabel('Time')
    plt.ylabel('Percent (%)')
    plt.title('Memory Cache Usage')
    plt.legend(loc='upper left')
    st.pyplot(plt)

def main():
    placeholder = st.empty()

    while True:
        try:
            data = r.get(redis_key)
            data = json.loads(data)
            timestamp = time.strftime('%H:%M:%S')

            time_history.append(timestamp)
            for i in range(8):
                cpu_history[f'cpu{i}'].append(data[f'avg-util-cpu{i}-60sec'])
            network_history.append(data['percent-network-egress'])
            memory_cache_history.append(data['percent-memory-cache'])

            data_dict = {
                "Timestamp": [timestamp],
                "Network Egress (%)": [data['percent-network-egress']],
                "Memory Cache (%)": [data['percent-memory-cache']],
            }
            for i in range(8):
                data_dict[f"CPU {i} Usage (%)"] = [data[f'avg-util-cpu{i}-60sec']]

            df = pd.DataFrame(data_dict)

            with placeholder.container():
                st.write(f"Atualização em tempo real: {timestamp}")
                
                st.dataframe(df)

                plot_cpu_usage()
                plot_network_usage()
                plot_memory_cache()

        except Exception as e:
            st.error(f"{str(e)}")

        time.sleep(refresh_rate)

if __name__ == "__main__":
    main()
