import subprocess
import json

class GPUMonitor:
    def get_stats(self):
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return {"error": "Failed to get GPU stats"}

            stats = result.stdout.strip().split(',')
            return {
                "gpu_utilization": float(stats[0]),
                "memory_used": float(stats[1]),
                "memory_total": float(stats[2]),
                "temperature": float(stats[3])
            }
        except Exception as e:
            return {"error": str(e)}
