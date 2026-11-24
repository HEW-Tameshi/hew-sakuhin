"""
Gemini API クライアントモジュール（app/core/gemini_client.py）

【このファイルの役割】
- Google の最新 Gemini Interactions API（POST /v1/interactions）を
  モデル `gemini-4-hydrogen`（settings.gemini_model）で呼び出し、JSON形式で構造化された分析結果を取得する。
- インストール済みの httpx を使用するため追加ライブラリ不要で動作する。
- プライバシー配慮のため `store: False` を指定し、相談内容の不要なサーバー保存を抑止する。
- .env に GEMINI_API_KEY が未設定の場合は GeminiConfigError を、通信失敗や応答不正時は GeminiAPIError を送出する。
"""

import json

import httpx

from app.core.config import settings

# Gemini Interactions API（安定版 v1）エンドポイント
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1/interactions"


class GeminiConfigError(RuntimeError):
    """サーバー側に GEMINI_API_KEY が設定されていない場合の例外"""
    pass


class GeminiAPIError(RuntimeError):
    """Gemini API の呼び出しやJSONレスポンスの解析に失敗した場合の例外"""
    pass


def _extract_output_text(body: dict) -> str:
    """
    Interactions API のレスポンス（steps 配列）から、
    末尾の model_output ステップに含まれるテキスト出力を結合して取り出す。
    """
    steps = body.get("steps")
    if not isinstance(steps, list):
        raise ValueError("stepsフィールドが存在しません")

    model_texts: list[str] = []
    for step in reversed(steps):
        if not isinstance(step, dict):
            continue
        if step.get("type") != "model_output":
            if model_texts:
                break
            continue

        content_list = step.get("content") or []
        step_parts: list[str] = []
        for part in content_list:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    step_parts.append(text)
        if step_parts:
            model_texts.append("".join(step_parts))

    if not model_texts:
        raise ValueError("model_outputのテキスト出力が見つかりません")

    model_texts.reverse()
    return "".join(model_texts)


def generate_json_with_gemini(
    prompt: str,
    system_instruction: str | None = None,
    json_schema: dict | None = None,
    timeout_seconds: float = 30.0,
) -> dict:
    """
    Gemini Interactions API（デフォルトモデル: gemini-4-hydrogen）へプロンプトを送信し、
    JSONオブジェクト（dict）として分析結果を受け取る。

    【処理の実行順序】
    1. settings.gemini_api_key が設定されているか確認する（未設定時は GeminiConfigError）。
    2. Interactions API 用のリクエストボディを構築する。
       - model: settings.gemini_model（デフォルトは "gemini-4-hydrogen"）
       - store: False（相談内容のサーバー保存を無効化）
       - response_format: {"type": "text", "mime_type": "application/json", ...}
    3. httpx.post で Gemini API へ送信し、HTTPステータスを確認する。
    4. steps 配列の model_output から生成テキストを取り出し、json.loads() で辞書に変換して返す。
    """
    if not settings.gemini_api_key:
        raise GeminiConfigError(
            "Gemini APIキー（GEMINI_API_KEY）が設定されていません。.envファイルを確認してください。"
        )

    response_format: dict = {
        "type": "text",
        "mime_type": "application/json",
    }
    if json_schema is not None:
        response_format["schema"] = json_schema

    payload: dict = {
        "model": settings.gemini_model,
        "input": prompt,
        "store": False,
        "response_format": response_format,
    }

    if system_instruction:
        payload["system_instruction"] = system_instruction

    try:
        response = httpx.post(
            GEMINI_INTERACTIONS_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": settings.gemini_api_key,
            },
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPError as exc:
        raise GeminiAPIError("Gemini APIとの通信に失敗しました") from exc
    except ValueError as exc:
        raise GeminiAPIError("Gemini APIのレスポンスJSON解析に失敗しました") from exc

    try:
        text_output = _extract_output_text(body)
        parsed = json.loads(text_output)
        if not isinstance(parsed, dict):
            raise ValueError("JSONオブジェクトではありません")
        return parsed
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise GeminiAPIError("Gemini APIの出力形式が想定と異なります") from exc
