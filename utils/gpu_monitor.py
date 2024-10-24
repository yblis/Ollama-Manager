import subprocess
import json
import shutil


class GPUMonitor:
    def get_stats(self):
        # Check if nvidia-smi is available
        if not shutil.which('nvidia-smi'):
            return {
                "error": "NVIDIA GPU monitoring not available - nvidia-smi not found",
                "status": "unavailable",
                "gpu_utilization": 0,
                "memory_used": 0,
                "memory_total": 0,
                "temperature": 0
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
                    "error": "Failed to get GPU stats - nvidia-smi command failed",
                    "status": "error",
                    "gpu_utilization": 0,
                    "memory_used": 0,
                    "memory_total": 0,
                    "temperature": 0
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
                "error": "GPU stats collection timed out",
                "status": "timeout",
                "gpu_utilization": 0,
                "memory_used": 0,
                "memory_total": 0,
                "temperature": 0
            }
        except Exception as e:
            return {
                "error": str(e),
                "status": "error",
                "gpu_utilization": 0,
                "memory_used": 0,
                "memory_total": 0,
                "temperature": 0
            }
