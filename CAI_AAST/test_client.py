import asyncio
import subprocess
import time
from typing import Any, Dict

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
API_URL = "http://localhost:8001/chat"

# --- Test Suite Configuration ---
TEST_CASES = [
    {
        "name": "Direct Match (MSc Docs)",
        "payload": {
            "question": "What documents do I need to submit for MSc admission?", 
            "user_type": "msc"
        },
        "expected_source": "MSc Admission Checklist",
        "is_out_of_bounds": False
    },
    {
        "name": "Ambiguous Query (No Intent)",
        "payload": {
            "question": "Tell me about the general AI structure and specializations.", 
            "user_type": None
        },
        "expected_source": "Academic Structure & Specializations", 
        "is_out_of_bounds": False
    },
    {
        "name": "Out-of-Bounds (Hallucination Check)",
        "payload": {
            "question": "What are the rules for adopting a pet capybara?", 
            "user_type": "msc"
        },
        "expected_source": None,
        "is_out_of_bounds": True # System Prompt MUST mandate linking clearly to cai@aast.edu 
    }
]

async def check_vram_usage() -> str:
    """
    Subprocess call to nvidia-smi checking RTX 4050 VRAM load.
    Flags heavily critical load limits on 6GB VRAM.
    """
    try:
        # Queries exactly Memory Used vs Total in CSV format
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            capture_output=True, text=True
        )
        output = result.stdout.strip().split('\n')
        
        if output and len(output[0].split(',')) == 2:
            used_str, total_str = output[0].split(',')
            used = int(used_str.strip())
            total = int(total_str.strip())
            
            # Since RTX 4050 has ~6144 MB limit, we flag at 5800 MB
            if used > 5800:
                return f"[bold red]CRITICAL: {used}MB / {total}MB Used[/bold red]"
            elif used > 5000:
                return f"[yellow]HIGH: {used}MB / {total}MB Used[/yellow]"
            else:
                return f"[green]{used}MB / {total}MB Used[/green]"
        return "Unknown parsing output"
    except Exception:
        return "[dim]nvidia-smi not available[/dim]"

async def run_scenario(client: httpx.AsyncClient, case: Dict[str, Any]) -> Dict[str, Any]:
    """Runs an individual scenario hitting the API and tracks hardware/response mechanics."""
    start_time = time.time()
    
    try:
        response = await client.post(API_URL, json=case["payload"], timeout=180.0)
        end_time = time.time()
        
        latency = end_time - start_time
        
        if response.status_code != 200:
            return {
                "name": case["name"],
                "status": "FAIL (HTTP Error)",
                "latency": latency,
                "error": f"HTTP {response.status_code} - {response.text}"
            }
            
        data = response.json()
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        
        # Calculate Token Throughput (TPS) 
        # Approximate: ~1.3 tokens per English word 
        approx_tokens = len(answer.split()) * 1.3
        tps = approx_tokens / latency if latency > 0 else 0
        
        vram_status = await check_vram_usage()
        
        # --- Strict Validation Logic ---
        status = "PASS"
        if case["is_out_of_bounds"]:
            if "cai@aast.edu" not in answer.lower():
                status = "FAIL (No Fallback Email)"
                
        if case["expected_source"]:
            # Assert source extraction correctly routed
            found = any(case["expected_source"].lower() in str(s).lower() for s in sources)
            if not found:
                status = "FAIL (Missing Target Source)"
                
        return {
            "name": case["name"],
            "status": status,
            "latency": latency,
            "tps": tps,
            "sources": sources,
            "answer_snippet": answer[:120].replace('\n', ' ') + "...",
            "vram": vram_status
        }
            
    except Exception as e:
        return {
            "name": case["name"],
            "status": "FAIL (Exception)",
            "latency": time.time() - start_time,
            "error": str(e)
        }

async def execute_benchmarks():
    console.print(Panel.fit("[bold blue]RAG System Hardware Benchmarking & Pipeline Validation[/bold blue]"))
    results = []
    
    # 1. Pipeline Integrity Validation (Sequential)
    console.print("\n[bold cyan]--- Phase 1: Functional Logic Validation (Sequential) ---[/bold cyan]")
    async with httpx.AsyncClient() as client:
        for case in TEST_CASES:
            console.print(f"Triggering Routine:  [dim]{case['name']}[/dim] ...")
            res = await run_scenario(client, case)
            results.append(res)
            
    # 2. Concurrency Stress Testing
    console.print("\n[bold cyan]--- Phase 2: Hardware Concurrency Analysis (3x Async Queue) ---[/bold cyan]")
    console.print("[dim]Evaluating Ollama locking behavior and 6GB VRAM spike endurance...[/dim]")
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(1, 4):
            case = {
                "name": f"Stress Test Worker #{i}",
                "payload": {"question": "Provide a comprehensive summary of all graduation criteria.", "user_type": "msc"},
                "expected_source": None,
                "is_out_of_bounds": False
            }
            tasks.append(run_scenario(client, case))
            
        concurrent_results = await asyncio.gather(*tasks)
        results.extend(concurrent_results)
        
    # --- Performance Dashboard Rendering ---
    table = Table(title="Validation & Performance Results Dashboard", show_header=True, header_style="bold magenta")
    table.add_column("Routine", style="dim", width=22)
    table.add_column("Status", justify="center")
    table.add_column("Latency(s)", justify="right")
    table.add_column("Avg TPS", justify="right")
    table.add_column("VRAM Usage", justify="center")
    table.add_column("Log Snippet", width=40)

    total_time = 0
    successes = 0
    
    for r in results:
        is_pass = "PASS" in r.get("status", "")
        status_color = "bold green" if is_pass else "bold red"
        
        if is_pass:
            successes += 1
            
        lat = r.get("latency", 0)
        total_time += lat
        
        table.add_row(
            r.get("name", "Unknown"),
            f"[{status_color}]{r.get('status', 'ERROR')}[/{status_color}]",
            f"{lat:.1f}s",
            f"{r.get('tps', 0):.1f}/s",
            r.get("vram", "N/A"),
            r.get("answer_snippet", r.get("error", "No output generated"))
        )
        
    console.print()
    console.print(table)
    
    # --- Final Executive Summary ---
    total_exec = len(results)
    success_rate = (successes / total_exec) * 100
    mean_latency = total_time / total_exec if total_exec > 0 else 0
    
    summary = (
        f"Total Routines Run:    [bold]{total_exec}[/bold]\n"
        f"System Success Rate:   [bold green]{success_rate:.1f}%[/bold green]\n"
        f"Mean Generation Time:  [bold]{mean_latency:.2f}s[/bold]\n"
    )
    console.print(Panel(summary, title="[bold]Summary Report[/bold]", expand=False))

if __name__ == "__main__":
    asyncio.run(execute_benchmarks())
