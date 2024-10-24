import subprocess
import json
import shutil


class GPUMonitor:
    def get_stats(self):
        # Check if nvidia-smi is available
        if not shutil.which('nvidia-smi'):
            return {
                "status": "no_gpu",
                "gpu_utilization": 0,
                "memory_used": 0,
                "memory_total": 0,
                "temperature": 0,
                "message": "No NVIDIA GPU detected"
            }

        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5  # Add timeout to prevent hanging
            )
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "gpu_utilization": 0,
                    "memory_used": 0,
                    "memory_total": 0,
                    "temperature": 0,
                    "message": "Failed to get GPU stats"
                }

            stats = result.stdout.strip().split(',')
            return {
                "status": "available",
                "gpu_utilization": float(stats[0]),
                "memory_used": float(stats[1]),
                "memory_total": float(stats[2]),
                "temperature": float(stats[3])
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "gpu_utilization": 0,
                "memory_used": 0,
                "memory_total": 0,
                "temperature": 0,
                "message": "GPU stats collection timed out"
            }
        except Exception as e:
            return {
                "status": "error",
                "gpu_utilization": 0,
                "memory_used": 0,
                "memory_total": 0,
                "temperature": 0,
                "message": str(e)
            }
