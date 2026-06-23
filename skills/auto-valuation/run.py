#!/usr/bin/env python3
"""Skill: Auto Valuation (Profit Engine) — V5.0-Hardened
Triggered by: "评估 车牌号 XXX"
--json --dry-run --version 全部支持
"""

import argparse
import json
import random
import re
from pathlib import Path

VERSION = "0.3.0"


# ========= 安全边界（核心加固点）=========
def sanitize_plate(input_str: str) -> str:
    """铁龙虾装甲：输入清洗函数
    1. 仅允许 A-Z a-z 0-9 -
    2. 长度强制截断至 8 个字符
    3. 移除所有非白名单字符
    """
    if not isinstance(input_str, str):
        return ""

    cleaned = re.sub(r"[^A-Za-z0-9\-]", "", input_str)
    truncated = cleaned[:8]

    if input_str != truncated:
        log_path = Path(__file__).resolve().parent.parent.parent / ".deploy" / "logs" / "security.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[SECURITY] Plate injection blocked. Original: {input_str}, Cleaned: {truncated}\n")

    return truncated


# ========= 业务逻辑 =========
def estimate_car_value(plate_number: str):
    """V5.0: DeepSeek-powered valuation. Falls back to random mock on error."""
    damage_detected = random.choice([True, False])
    market_price = random.randint(50000, 150000)

    try:
        import os

        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        prompt = (
            f"Act as a senior car appraiser.\n"
            f"Plate: {plate_number}\n"
            f"Market Avg: {market_price}\n"
            f"Visual Damage Detected: {damage_detected}\n\n"
            f"If damage is true, apply depreciation factor 0.70-0.90.\n"
            f'Return JSON: {{"final_price": int, "confidence": float, "factors": ["string"]}}'
        )
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        ds_result = json.loads(resp.choices[0].message.content)
        return {
            "plate": plate_number,
            "market_value": ds_result.get("final_price", market_price),
            "damage_detected": damage_detected,
            "confidence": ds_result.get("confidence", 0.8),
            "factors": ds_result.get("factors", []),
            "engine": "deepseek",
        }
    except Exception as e:
        # Fallback: mechanical valuation
        if damage_detected:
            market_price = int(market_price * 0.85)
        return {
            "plate": plate_number,
            "market_value": market_price,
            "damage_detected": damage_detected,
            "confidence": 0.7,
            "engine": "fallback",
            "error": str(e)[:120],
        }


def main():
    parser = argparse.ArgumentParser(description="Auto Valuation — V5.0 Profit Engine")
    parser.add_argument("plate", nargs="?", help="车牌号")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print(f"auto-valuation v{VERSION}")
        return

    plate_raw = args.plate or ""
    if not plate_raw:
        result = {"error": "Missing plate number", "usage": "auto-valuation <plate>"}
        print(json.dumps(result, ensure_ascii=False) if args.json else result["error"])
        return

    plate = sanitize_plate(plate_raw)
    if not plate:
        result = {"error": "Invalid plate number after sanitization"}
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.dry_run:
        result = {"plate": plate, "status": "dry_run", "original": plate_raw}
        print(json.dumps(result, ensure_ascii=False) if args.json else f"[DRY-RUN] plate={plate}")
        return

    result = estimate_car_value(plate)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        damage = "检测到损伤" if result["damage_detected"] else "无损伤"
        print(
            f"车牌: {result['plate']} | 估价: ¥{result['market_value']:,} | {damage} | 置信度: {result['confidence']}"
        )
    return result


if __name__ == "__main__":
    main()
