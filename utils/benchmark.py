import time
import json
import psutil
import threading
from datetime import datetime


class ModelBenchmark:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.active_benchmarks = {}
        self.benchmark_results = {}
        
    def _measure_system_metrics(self):
        """Measure system metrics during benchmark"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'timestamp': datetime.now().isoformat()
        }
    
    def start_benchmark(self, model_name, prompt="Tell me a short story about a robot."):
        """Start a benchmark for a specific model"""
        if model_name in self.active_benchmarks:
            return {"error": f"Benchmark already running for model {model_name}"}
            
        try:
            # Initialize benchmark data
            benchmark_data = {
                'start_time': time.time(),
                'model': model_name,
                'prompt': prompt,
                'metrics': [],
                'status': 'running',
                'result': None
            }
            
            # Store benchmark data
            self.active_benchmarks[model_name] = benchmark_data
            
            # Start monitoring thread
            def monitor_metrics():
                while model_name in self.active_benchmarks:
                    if self.active_benchmarks[model_name]['status'] != 'running':
                        break
                    metrics = self._measure_system_metrics()
                    self.active_benchmarks[model_name]['metrics'].append(metrics)
                    time.sleep(1)
            
            monitor_thread = threading.Thread(target=monitor_metrics)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Make the actual API call
            response = self.ollama_client._make_request(
                "POST",
                "/api/generate",
                json={"model": model_name, "prompt": prompt}
            )
            
            end_time = time.time()
            elapsed_time = end_time - benchmark_data['start_time']
            
            # Process results
            result = {
                'model': model_name,
                'elapsed_time': elapsed_time,
                'metrics': benchmark_data['metrics'],
                'success': 'error' not in response,
                'error': response.get('error'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Store results and cleanup
            self.benchmark_results[model_name] = result
            del self.active_benchmarks[model_name]
            
            return result
            
        except Exception as e:
            if model_name in self.active_benchmarks:
                del self.active_benchmarks[model_name]
            return {"error": str(e)}
    
    def get_benchmark_status(self, model_name):
        """Get current benchmark status for a model"""
        if model_name in self.active_benchmarks:
            return {
                "status": "running",
                "model": model_name,
                "start_time": self.active_benchmarks[model_name]['start_time']
            }
        elif model_name in self.benchmark_results:
            return {
                "status": "completed",
                "result": self.benchmark_results[model_name]
            }
        return {"error": f"No benchmark data found for model {model_name}"}
    
    def get_all_results(self):
        """Get all completed benchmark results"""
        return {
            "results": list(self.benchmark_results.values()),
            "active_benchmarks": list(self.active_benchmarks.keys())
        }
