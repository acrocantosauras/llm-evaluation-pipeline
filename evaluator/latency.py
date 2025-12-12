import time

def measure_latency(fn, runs=3):
    durations = []
    for _ in range(runs):
        start = time.time()
        fn()
        durations.append((time.time() - start) * 1000)
    return round(sum(durations)/len(durations), 3)
