#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志查看工具
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

def list_log_files(log_dir="logs"):
    """列出所有日志文件"""
    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        return []
    
    log_files = []
    for file in os.listdir(log_dir):
        if file.endswith('.log'):
            file_path = os.path.join(log_dir, file)
            stat = os.stat(file_path)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            log_files.append({
                'name': file,
                'path': file_path,
                'size': size,
                'mtime': mtime
            })
    
    # 按修改时间排序
    log_files.sort(key=lambda x: x['mtime'], reverse=True)
    return log_files

def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"

def view_log_file(file_path, lines=50, follow=False, filter_level=None, filter_module=None):
    """查看日志文件"""
    if not os.path.exists(file_path):
        print(f"❌ 日志文件不存在: {file_path}")
        return
    
    print(f"📄 查看日志文件: {file_path}")
    print(f"📊 文件大小: {format_size(os.path.getsize(file_path))}")
    print("=" * 80)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
            # 应用过滤器
            filtered_lines = []
            for line in all_lines:
                if filter_level and filter_level.upper() not in line:
                    continue
                if filter_module and filter_module not in line:
                    continue
                filtered_lines.append(line)
            
            # 显示最后N行
            if lines > 0:
                display_lines = filtered_lines[-lines:]
            else:
                display_lines = filtered_lines
            
            for line in display_lines:
                print(line.rstrip())
            
            if follow:
                print("\n🔄 实时监控模式 (Ctrl+C 退出)")
                import time
                try:
                    while True:
                        time.sleep(1)
                        # 检查文件是否有新内容
                        current_size = os.path.getsize(file_path)
                        if current_size > len(''.join(all_lines)):
                            # 文件有新内容，重新读取
                            with open(file_path, 'r', encoding='utf-8') as f:
                                new_lines = f.readlines()
                                for line in new_lines[len(all_lines):]:
                                    if filter_level and filter_level.upper() not in line:
                                        continue
                                    if filter_module and filter_module not in line:
                                        continue
                                    print(line.rstrip())
                                all_lines = new_lines
                except KeyboardInterrupt:
                    print("\n👋 退出监控模式")
                    
    except Exception as e:
        print(f"❌ 读取日志文件失败: {e}")

def search_logs(log_dir="logs", pattern="", days=7):
    """搜索日志"""
    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        return
    
    print(f"🔍 搜索日志: {pattern}")
    print(f"📅 时间范围: 最近 {days} 天")
    print("=" * 80)
    
    cutoff_date = datetime.now() - timedelta(days=days)
    found_count = 0
    
    for file in os.listdir(log_dir):
        if file.endswith('.log'):
            file_path = os.path.join(log_dir, file)
            stat = os.stat(file_path)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            
            if mtime < cutoff_date:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.lower() in line.lower():
                            print(f"{file}:{line_num} - {line.rstrip()}")
                            found_count += 1
            except Exception as e:
                print(f"❌ 读取文件失败 {file}: {e}")
    
    print(f"\n✅ 找到 {found_count} 条匹配记录")

def main():
    parser = argparse.ArgumentParser(description="日志查看工具")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有日志文件")
    parser.add_argument("--view", "-v", help="查看指定日志文件")
    parser.add_argument("--lines", "-n", type=int, default=50, help="显示行数 (默认50)")
    parser.add_argument("--follow", "-f", action="store_true", help="实时监控")
    parser.add_argument("--level", help="过滤日志级别 (INFO, WARNING, ERROR)")
    parser.add_argument("--module", help="过滤模块名称")
    parser.add_argument("--search", "-s", help="搜索关键词")
    parser.add_argument("--days", type=int, default=7, help="搜索天数范围 (默认7天)")
    parser.add_argument("--dir", default="logs", help="日志目录 (默认logs)")
    
    args = parser.parse_args()
    
    if args.list:
        log_files = list_log_files(args.dir)
        if log_files:
            print("📁 日志文件列表:")
            print(f"{'文件名':<30} {'大小':<10} {'修改时间':<20}")
            print("-" * 60)
            for log_file in log_files:
                print(f"{log_file['name']:<30} {format_size(log_file['size']):<10} {log_file['mtime'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("❌ 没有找到日志文件")
    
    elif args.view:
        view_log_file(args.view, args.lines, args.follow, args.level, args.module)
    
    elif args.search:
        search_logs(args.dir, args.search, args.days)
    
    else:
        # 默认显示最新的日志文件
        log_files = list_log_files(args.dir)
        if log_files:
            latest_file = log_files[0]['path']
            view_log_file(latest_file, args.lines, args.follow, args.level, args.module)
        else:
            print("❌ 没有找到日志文件")

if __name__ == "__main__":
    main()
