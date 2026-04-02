#!/usr/bin/env python3
"""
Skill Evaluation Runner

Chạy evaluation cho các skills với test cases được định nghĩa trong test_cases/
"""

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


# Cấu hình
SKILL_EVAL_DIR = Path(__file__).parent
TEST_CASES_DIR = SKILL_EVAL_DIR / "test_cases"
LOGS_DIR = SKILL_EVAL_DIR / "logs"
SCRIPTS_DIR = SKILL_EVAL_DIR / "scripts"

# Model mặc định
DEFAULT_MODEL = "haiku"


def load_test_cases(skill_name: str) -> Dict[str, Any]:
    """Load test cases từ file JSON"""
    test_file = TEST_CASES_DIR / f"{skill_name}.json"
    if not test_file.exists():
        raise FileNotFoundError(f"Test case file not found: {test_file}")

    with open(test_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_skills() -> List[str]:
    """Lấy danh sách tất cả skills có test cases"""
    skills = []
    for f in TEST_CASES_DIR.glob("*.json"):
        skills.append(f.stem)
    return sorted(skills)


def create_log_directory(skill_name: str) -> Path:
    """Tạo thư mục log cho skill"""
    log_dir = LOGS_DIR / skill_name
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def write_metadata_header(
    log_file: Path, skill: str, test_id: str, prompt: str, model: str
) -> None:
    """Ghi metadata vào header của file log"""
    metadata = {
        "skill": skill,
        "test_id": test_id,
        "prompt": prompt,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "exit_code": None,  # Sẽ được cập nhật sau khi chạy
    }

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")


def update_metadata_exit_code(log_file: Path, exit_code: int, duration: float) -> None:
    """Cập nhật exit_code trong metadata"""
    # Đọc metadata từ dòng đầu tiên
    with open(log_file, "r", encoding="utf-8") as f:
        first_line = f.readline()
        metadata = json.loads(first_line)

    # Cập nhật
    metadata["exit_code"] = exit_code
    metadata["duration_seconds"] = duration

    # Ghi lại toàn bộ file (giữ nguyên các dòng log)
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        f.writelines(lines[1:])


def run_claude_command(prompt: str, model: str, log_file: Path) -> int:
    """Chạy lệnh claude với prompt và ghi log"""
    # Tạo lệnh claude
    cmd = [
        "claude",
        "--model",
        model,
        "-p",
        "--dangerously-skip-permissions",
        "--verbose",
        "--output-format",
        "stream-json",
        prompt,
    ]

    # Mở file log để ghi
    with open(log_file, "a", encoding="utf-8") as log_file_handle:
        result = subprocess.run(
            cmd, stdout=log_file_handle, stderr=subprocess.PIPE, text=True
        )

    return result.returncode


def run_single_test(
    skill: str, test_case: Dict[str, str], model: str, log_dir: Path
) -> Dict[str, Any]:
    """Chạy một test case"""
    test_id = test_case["id"]
    prompt = test_case["prompt"]
    name = test_case["name"]

    log_file = log_dir / f"{test_id}.jsonl"

    print(f"    [{test_id}] {name}")

    # Ghi metadata header
    write_metadata_header(log_file, skill, test_id, prompt, model)

    # Chạy lệnh
    start_time = time.time()
    exit_code = run_claude_command(prompt, model, log_file)
    duration = time.time() - start_time

    # Cập nhật metadata với exit_code
    update_metadata_exit_code(log_file, exit_code, duration)

    status = "✅" if exit_code == 0 else "❌"
    print(f"      {status} Exit code: {exit_code} ({duration:.1f}s)")

    return {
        "test_id": test_id,
        "name": name,
        "exit_code": exit_code,
        "duration": duration,
        "passed": exit_code == 0,
    }


def run_skill_evaluation(
    skill: str, model: str, verbose: bool = False
) -> Dict[str, Any]:
    """Chạy evaluation cho một skill"""
    print(f"\n📂 Skill: {skill}")

    # Load test cases
    data = load_test_cases(skill)
    test_cases = [tc for tc in data["test_cases"] if "id" in tc]

    print(f"   {len(test_cases)} test cases")

    # Tạo log directory
    log_dir = create_log_directory(skill)

    # Chạy từng test case
    results = []
    for i, test_case in enumerate(test_cases, 1):
        if verbose:
            print(f"\n  [{i}/{len(test_cases)}]")

        result = run_single_test(skill, test_case, model, log_dir)
        results.append(result)

    # Tổng kết
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    print(f"\n   📊 Kết quả: {passed}/{len(results)} passed, {failed} failed")

    return {
        "skill": skill,
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


def generate_index(evaluation_results: List[Dict[str, Any]]) -> None:
    """Tạo file index.json chứa tất cả log paths và metadata"""
    index = {"generated_at": datetime.now().isoformat(), "evaluations": []}

    for eval_result in evaluation_results:
        skill = eval_result["skill"]

        # Lấy tất cả log files trong thư mục
        log_dir = LOGS_DIR / skill
        test_logs = []

        if log_dir.exists():
            for log_file in sorted(log_dir.glob("*.jsonl")):
                # Đọc metadata từ dòng đầu tiên
                with open(log_file, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                    metadata = json.loads(first_line)
                    test_logs.append(
                        {
                            "file": str(log_file.relative_to(LOGS_DIR)),
                            "test_id": metadata.get("test_id"),
                            "exit_code": metadata.get("exit_code"),
                            "timestamp": metadata.get("timestamp"),
                        }
                    )

        index["evaluations"].append(
            {
                "skill": skill,
                "total": eval_result["total"],
                "passed": eval_result["passed"],
                "failed": eval_result["failed"],
                "test_logs": test_logs,
            }
        )

    # Ghi index.json
    index_file = LOGS_DIR / "index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n📋 Index file created: {index_file}")


def main():
    parser = argparse.ArgumentParser(description="Skill Evaluation Runner")
    parser.add_argument(
        "--skill",
        type=str,
        help="Chạy evaluation cho skill cụ thể (để trống = chạy tất cả)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Model để sử dụng (mặc định: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Hiển thị chi tiết từng bước"
    )
    parser.add_argument(
        "--list", action="store_true", help="Liệt kê tất cả skills có sẵn"
    )

    args = parser.parse_args()

    # Liệt kê skills
    if args.list:
        skills = get_all_skills()
        print("📚 Skills có sẵn:")
        for skill in skills:
            print(f"  - {skill}")
        return

    # Xác định skills cần chạy
    if args.skill:
        skills = [args.skill]
    else:
        skills = get_all_skills()

    print("🎯 Skill Evaluation Runner")
    print(f"   Model: {args.model}")
    print(f"   Skills: {len(skills)}")

    # Tạo thư mục logs
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Chạy evaluation
    evaluation_results = []
    total_tests = 0
    total_passed = 0

    for i, skill in enumerate(skills, 1):
        print(f"\n{'='*50}")
        print(f"[{i}/{len(skills)}] ", end="")

        try:
            result = run_skill_evaluation(skill, args.model, args.verbose)
            evaluation_results.append(result)
            total_tests += result["total"]
            total_passed += result["passed"]
        except Exception as e:
            print(f"\n❌ Error running {skill}: {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()

    # Tạo index file
    generate_index(evaluation_results)

    # Tổng kết cuối cùng
    print(f"\n{'='*50}")
    print("🎉 Evaluation hoàn tất!")
    print(f"   Tổng tests: {total_tests}")
    print(f"   Passed: {total_passed}")
    print(f"   Failed: {total_tests - total_passed}")
    print(f"   Pass rate: {total_passed/total_tests*100:.1f}%")
    print(f"\n📁 Logs saved to: {LOGS_DIR}")


if __name__ == "__main__":
    main()
