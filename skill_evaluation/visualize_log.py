#!/usr/bin/env python3
"""
Log Visualizer CLI

Đọc file .jsonl và hiển thị nội dung log trong terminal.
Hỗ trợ stream-json format từ Claude Code.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


# Thử import rich, nếu không có thì dùng plain text
try:
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("Warning: 'rich' library not found. Using plain text mode.")
    print("Install rich for better experience: pip install rich\n")


console = Console() if HAS_RICH else None


def load_jsonl(filepath: Path) -> List[Dict[str, Any]]:
    """Load JSONL file"""
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line", file=sys.stderr)
    return entries


def get_metadata(entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Lấy metadata từ dòng đầu tiên"""
    if entries:
        first = entries[0]
        # Kiểm tra xem có phải metadata không (không có 'type' field)
        if 'type' not in first and 'skill' in first:
            return first
    return None


def print_plain(text: str, indent: int = 0):
    """In text với indent"""
    prefix = "  " * indent
    for line in text.split('\n'):
        print(f"{prefix}{line}")


def format_json(content: Any) -> str:
    """Format JSON với màu sắc cho terminal"""
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except:
            pass
    
    if isinstance(content, dict):
        return json.dumps(content, indent=2, ensure_ascii=False)
    elif isinstance(content, list):
        return json.dumps(content, indent=2, ensure_ascii=False)
    return str(content)


def print_entry(entry: Dict[str, Any], use_rich: bool = True, show_thinking: bool = True):
    """In một entry đơn lẻ"""
    entry_type = entry.get('type', 'unknown')
    
    # System entry (init)
    if entry_type == 'system':
        subtype = entry.get('subtype', '')
        if subtype == 'init':
            if use_rich and HAS_RICH:
                console.print(Panel(
                    f"Model: {entry.get('model', 'N/A')}\n"
                    f"Session: {entry.get('session_id', 'N/A')[:8]}...\n"
                    f"Tools: {', '.join(entry.get('tools', [])[:5])}...",
                    title="⚙️ System Init",
                    border_style="dim"
                ))
            else:
                print("\n⚙️ SYSTEM INIT:")
                print(f"  Model: {entry.get('model', 'N/A')}")
                print(f"  Session: {entry.get('session_id', 'N/A')[:8]}...")
    
    # Assistant entry
    elif entry_type == 'assistant':
        message = entry.get('message', {})
        content = message.get('content', [])
        
        for item in content:
            item_type = item.get('type', '')
            
            if item_type == 'thinking':
                if show_thinking:
                    thinking = item.get('thinking', '')
                    # Rút gọn nếu quá dài
                    if len(thinking) > 2000:
                        thinking = thinking[:2000] + f"\n... [{len(thinking) - 2000} more chars]"
                    
                    if use_rich and HAS_RICH:
                        console.print(Panel(
                            thinking,
                            title="🤔 Thinking",
                            border_style="dim",
                            padding=(0, 1)
                        ))
                    else:
                        print_plain("🤔 THINKING:", indent=1)
                        print_plain(thinking, indent=2)
            
            elif item_type == 'text':
                text = item.get('text', '')
                if use_rich and HAS_RICH:
                    console.print(Panel(
                        text,
                        title="💬 Response",
                        border_style="green",
                        padding=(1, 2)
                    ))
                else:
                    print_plain("\n💬 RESPONSE:", indent=1)
                    print_plain(text, indent=2)
            
            elif item_type == 'tool_use':
                tool_name = item.get('name', 'unknown')
                tool_input = item.get('input', {})
                tool_id = item.get('id', '')
                
                if use_rich and HAS_RICH:
                    console.print(f"\n🔧 [bold cyan]Tool:[/bold cyan] {tool_name}")
                    if tool_input:
                        syntax = Syntax(
                            json.dumps(tool_input, indent=2, ensure_ascii=False)[:3000],
                            "json",
                            theme="monokai",
                            line_numbers=False
                        )
                        console.print(syntax)
                else:
                    print_plain(f"\n🔧 TOOL: {tool_name}", indent=1)
                    if tool_input:
                        print_plain(json.dumps(tool_input, indent=2, ensure_ascii=False)[:3000], indent=2)
    
    # User entry (tool result)
    elif entry_type == 'user':
        message = entry.get('message', {})
        content = message.get('content', [])
        
        for item in content:
            tool_use_id = item.get('tool_use_id', '')
            result_content = item.get('content', '')
            
            if use_rich and HAS_RICH:
                console.print(f"\n   [green]✓ Tool Result:[/green]")
                # Rút gọn nếu quá dài
                if len(result_content) > 2000:
                    result_content = result_content[:2000] + f"\n... [{len(result_content) - 2000} more chars]"
                
                try:
                    parsed = json.loads(result_content)
                    syntax = Syntax(
                        json.dumps(parsed, indent=2, ensure_ascii=False)[:3000],
                        "json",
                        theme="monokai",
                        line_numbers=False
                    )
                    console.print(syntax)
                except:
                    console.print(f"   {result_content[:1000]}")
            else:
                print_plain(f"\n   ✓ TOOL RESULT:", indent=1)
                if len(result_content) > 2000:
                    result_content = result_content[:2000] + f"\n... [{len(result_content) - 2000} more chars]"
                print_plain(result_content[:3000], indent=2)
    
    # Rate limit event
    elif entry_type == 'rate_limit_event':
        info = entry.get('rate_limit_info', {})
        status = info.get('status', 'unknown')
        
        if use_rich and HAS_RICH:
            color = "green" if status == "allowed" else "red"
            console.print(f"\n⚡ [bold {color}]Rate Limit:[/bold {color}] {status}")
        else:
            print_plain(f"\n⚡ RATE LIMIT: {status}", indent=1)
    
    # Result entry
    elif entry_type == 'result':
        subtype = entry.get('subtype', '')
        is_error = entry.get('is_error', False)
        duration = entry.get('duration_ms', 0)
        total_cost = entry.get('total_cost_usd', 0)
        
        if subtype == 'success':
            if use_rich and HAS_RICH:
                console.print(Panel(
                    f"Duration: {duration}ms\n"
                    f"Cost: ${total_cost:.6f}\n"
                    f"Error: {is_error}",
                    title="✅ Result - Success",
                    border_style="green",
                    padding=(1, 2)
                ))
            else:
                print_plain("\n✅ RESULT - SUCCESS:", indent=1)
                print_plain(f"Duration: {duration}ms", indent=2)
                print_plain(f"Cost: ${total_cost:.6f}", indent=2)
        else:
            result_text = entry.get('result', '')
            if use_rich and HAS_RICH:
                console.print(Panel(
                    f"Error: {is_error}\n"
                    f"Result: {result_text[:500]}",
                    title="❌ Result - Error",
                    border_style="red",
                    padding=(1, 2)
                ))
            else:
                print_plain("\n❌ RESULT - ERROR:", indent=1)
                print_plain(f"Error: {is_error}", indent=2)
                print_plain(f"Result: {result_text[:500]}", indent=2)


def print_summary(metadata: Dict[str, Any], entries: List[Dict[str, Any]], use_rich: bool = True):
    """Hiển thị tổng kết"""
    # Đếm các loại entries
    thinking_count = 0
    tool_use_count = 0
    tool_result_count = 0
    text_count = 0
    
    for entry in entries:
        entry_type = entry.get('type', '')
        
        if entry_type == 'assistant':
            message = entry.get('message', {})
            content = message.get('content', [])
            for item in content:
                item_type = item.get('type', '')
                if item_type == 'thinking':
                    thinking_count += 1
                elif item_type == 'text':
                    text_count += 1
                elif item_type == 'tool_use':
                    tool_use_count += 1
        
        elif entry_type == 'user':
            tool_result_count += 1
    
    duration = metadata.get('duration_seconds', 0)
    timestamp = metadata.get('timestamp', 'N/A')
    skill = metadata.get('skill', 'N/A')
    test_id = metadata.get('test_id', 'N/A')
    prompt = metadata.get('prompt', 'N/A')
    model = metadata.get('model', 'N/A')
    exit_code = metadata.get('exit_code', 'N/A')
    
    # Rút gọn prompt
    if len(prompt) > 100:
        prompt = prompt[:100] + "..."
    
    if use_rich and HAS_RICH:
        summary = f"""
[bold]Skill:[/bold] {skill}
[bold]Test ID:[/bold] {test_id}
[bold]Model:[/bold] {model}
[bold]Timestamp:[/bold] {timestamp}
[bold]Exit Code:[/bold] {'✅ 0 (Success)' if exit_code == 0 else f'❌ {exit_code}'}
[bold]Duration:[/bold] {duration:.2f}s

[bold]Prompt:[/bold] {prompt}

[bold]Statistics:[/bold]
  - Thinking blocks: {thinking_count}
  - Tool calls: {tool_use_count}
  - Tool results: {tool_result_count}
  - Text blocks: {text_count}
  - Total entries: {len(entries) - 1}
"""
        console.print(Panel(
            summary.strip(),
            title="📊 Summary",
            border_style="blue",
            padding=(1, 2)
        ))
    else:
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        print(f"Skill: {skill}")
        print(f"Test ID: {test_id}")
        print(f"Model: {model}")
        print(f"Timestamp: {timestamp}")
        print(f"Exit Code: {exit_code}")
        print(f"Duration: {duration:.2f}s")
        print(f"\nPrompt: {prompt}")
        print(f"\nStatistics:")
        print(f"  - Thinking blocks: {thinking_count}")
        print(f"  - Tool calls: {tool_use_count}")
        print(f"  - Tool results: {tool_result_count}")
        print(f"  - Text blocks: {text_count}")
        print(f"  - Total entries: {len(entries) - 1}")


def visualize_log(filepath: Path, use_rich: bool = True, show_thinking: bool = True):
    """Visualize một file log"""
    entries = load_jsonl(filepath)
    
    if not entries:
        print("❌ Log file is empty")
        return
    
    # Metadata từ dòng đầu tiên
    metadata = get_metadata(entries)
    
    if not metadata:
        print("❌ Invalid log format - no metadata found")
        return
    
    print(f"\n{'='*60}")
    print(f"📄 Log: {filepath.name}")
    print(f"{'='*60}\n")
    
    # Hiển thị summary trước
    print_summary(metadata, entries, use_rich)
    
    # Hiển thị chi tiết từng entry
    if use_rich and HAS_RICH:
        console.print("\n[bold]📝 Detailed Log:[/bold]\n")
    else:
        print("\n📝 DETAILED LOG:\n")
    
    # Bắt đầu từ entry thứ 2 (bỏ qua metadata)
    for entry in entries[1:]:
        print_entry(entry, use_rich, show_thinking)


def main():
    parser = argparse.ArgumentParser(
        description="Log Visualizer - Đọc và hiển thị file .jsonl log (Claude Code stream-json format)"
    )
    parser.add_argument(
        "log_file",
        type=str,
        help="Đường dẫn đến file .jsonl"
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Không hiển thị thinking blocks"
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Sử dụng plain text mode (không dùng rich)"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Chỉ hiển thị summary, không chi tiết"
    )
    
    args = parser.parse_args()
    
    filepath = Path(args.log_file)
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    use_rich = HAS_RICH and not args.plain
    
    visualize_log(
        filepath, 
        use_rich=use_rich, 
        show_thinking=not args.no_thinking
    )


if __name__ == "__main__":
    main()
