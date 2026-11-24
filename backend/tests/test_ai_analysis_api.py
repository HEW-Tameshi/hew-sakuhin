"""
AI分析機能（Gemini API）テストモジュール（tests/test_ai_analysis_api.py）

【このファイルの役割】
- Gemini API 呼び出し（generate_json_with_gemini）をモックし、以下を検証する：
  1. レターリスク分析API（POST /api/ai/letters/{letter_code}/analyze）による t_ai_analysis 保存
  2. レターAI分析履歴取得API（GET /api/ai/letters/{letter_code}）
  3. 会話AIまとめ＆コミュニケーション分析API（POST /api/ai/matchings/{matching_code}/analyze）
  4. 第三者の会話分析拒否（403）、GEMINI_API_KEY 未設定時（503）、Gemini通信エラー時（502）
"""

import uuid
from unittest.mock import patch

from sqlalchemy import select

from app.ai_analysis.models import AiAnalysis
from app.core.gemini_client import GeminiAPIError, GeminiConfigError
from app.post.models import EmotionCategory


def _setup_chat_scenario(client, test_session_factory):
    """出品者・購入者・第三者を登録し、出品→購入→チャット作成→メッセージ送信まで準備する。"""
    suffix = uuid.uuid4().hex
    password = "Test1234"
    users = {}

    for role, nickname in (
        ("seller", "AIテスト出品者"),
        ("buyer", "AIテスト購入者"),
        ("third", "AIテスト第三者"),
    ):
        email = f"ai_{role}_{suffix}@example.com"
        reg = client.post(
            "/api/users/register",
            json={"email": email, "password": password, "nickname": nickname},
        )
        assert reg.status_code == 201
        login = client.post(
            "/api/users/login",
            json={"email": email, "password": password},
        )
        token = login.json()["access_token"]
        users[role] = {
            "user_code": reg.json()["user_code"],
            "headers": {"Authorization": f"Bearer {token}"},
        }

    with test_session_factory() as db:
        cat = db.scalar(
            select(EmotionCategory).where(EmotionCategory.category_code == "E01")
        )
        if cat is None:
            db.add(EmotionCategory(category_code="E01", category_name="喜"))
            db.commit()

    post_res = client.post(
        "/api/posts",
        headers=users["seller"]["headers"],
        json={
            "title": "仕事の悩みを聞いてほしい",
            "content": "最近少し気持ちが落ち込んでいて、誰かに話を聞いてほしいです。",
            "category": "愚痴・ストレス",
            "time": 25,
            "point": 135,
            "emotion": "joy",
            "call": "yes",
            "express": "no",
        },
    )
    letter_code = post_res.json()["letter_code"]

    # 購入前にポイントをチャージ
    assert client.post(
        "/api/points/charge",
        headers=users["buyer"]["headers"],
        json={"points": 500},
    ).status_code == 201

    buy_res = client.post(
        "/api/purchases",
        headers=users["buyer"]["headers"],
        json={"letter_code": letter_code},
    )
    matching_code = buy_res.json()["matching_code"]

    chat_res = client.post(
        "/api/chats",
        headers=users["buyer"]["headers"],
        json={"matching_code": matching_code},
    )
    chat_code = chat_res.json()["chat_code"]

    client.post(
        f"/api/chats/{chat_code}/messages",
        headers=users["seller"]["headers"],
        json={"message": "最近、会社でうまくいっていなくて落ち込んでいます。"},
    )
    client.post(
        f"/api/chats/{chat_code}/messages",
        headers=users["buyer"]["headers"],
        json={"message": "それは大変でしたね。ゆっくりで大丈夫なので教えてください。"},
    )

    return users, letter_code, matching_code


def test_letter_risk_analysis_and_history(client, test_session_factory):
    """Geminiによるレターリスク分析が t_ai_analysis へ保存され、履歴取得できること"""
    users, letter_code, _ = _setup_chat_scenario(client, test_session_factory)

    mock_risk_json = {
        "risk_level": 1,
        "risk_reason": "一般的な悩み相談であり、不適切な表現や個人情報の露出はありません。",
    }

    with patch(
        "app.ai_analysis.service.generate_json_with_gemini",
        return_value=mock_risk_json,
    ):
        res = client.post(
            f"/api/ai/letters/{letter_code}/analyze",
            headers=users["seller"]["headers"],
        )
        assert res.status_code == 201
        data = res.json()
        assert data["ai_analysis_code"].startswith("AI")
        assert len(data["ai_analysis_code"]) == 10
        assert data["letter_code"] == letter_code
        assert data["risk_level"] == 1
        assert "不適切な表現" in data["risk_reason"]

    # DB（t_ai_analysis）に保存されていることを確認
    with test_session_factory() as db:
        saved = db.scalar(
            select(AiAnalysis).where(
                AiAnalysis.ai_analysis_code == data["ai_analysis_code"]
            )
        )
        assert saved is not None
        assert saved.risk_level == 1

    # 分析履歴一覧取得API（GET /api/ai/letters/{letter_code}）
    history_res = client.get(
        f"/api/ai/letters/{letter_code}",
        headers=users["seller"]["headers"],
    )
    assert history_res.status_code == 200
    assert len(history_res.json()) == 1
    assert history_res.json()[0]["ai_analysis_code"] == data["ai_analysis_code"]


def test_matching_conversation_analysis(client, test_session_factory):
    """Geminiによる会話AIまとめ＆コミュニケーション分析（review1/review2用）が返ること"""
    users, _, matching_code = _setup_chat_scenario(client, test_session_factory)

    mock_conv_json = {
        "summary_points": [
            "相談内容を最後まで丁寧に聞いていました",
            "相手の気持ちに共感する言葉が多く見られました",
            "落ち着いた雰囲気で会話を進めていました",
        ],
        "overall_evaluation": "とても良い",
        "embrace_score": 95,
        "empathy_score": 88,
        "logic_score": 72,
        "personality_type": "相手を安心させるタイプ",
        "personality_description": "相手の気持ちに寄り添い、安心感を与えることができるタイプです。",
        "title_badge": "言語化の神",
    }

    with patch(
        "app.ai_analysis.service.generate_json_with_gemini",
        return_value=mock_conv_json,
    ):
        # 当事者（購入者）が実行すると 200 OK で全項目が返る
        res = client.post(
            f"/api/ai/matchings/{matching_code}/analyze",
            headers=users["buyer"]["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["matching_code"] == matching_code
        assert len(data["summary_points"]) == 3
        assert data["overall_evaluation"] == "とても良い"
        assert data["embrace_score"] == 95
        assert data["empathy_score"] == 88
        assert data["logic_score"] == 72
        assert data["personality_type"] == "相手を安心させるタイプ"
        assert data["title_badge"] == "言語化の神"

        # 第三者が実行しようとすると HTTP 403 Forbidden
        forbidden_res = client.post(
            f"/api/ai/matchings/{matching_code}/analyze",
            headers=users["third"]["headers"],
        )
        assert forbidden_res.status_code == 403


def test_ai_analysis_config_and_api_errors(client, test_session_factory):
    """GEMINI_API_KEY未設定時は503、Gemini通信失敗時は502を返すこと"""
    users, letter_code, _ = _setup_chat_scenario(client, test_session_factory)

    with patch(
        "app.ai_analysis.service.generate_json_with_gemini",
        side_effect=GeminiConfigError("GEMINI_API_KEYが未設定です"),
    ):
        res_503 = client.post(
            f"/api/ai/letters/{letter_code}/analyze",
            headers=users["seller"]["headers"],
        )
        assert res_503.status_code == 503

    with patch(
        "app.ai_analysis.service.generate_json_with_gemini",
        side_effect=GeminiAPIError("Gemini APIとの通信に失敗しました"),
    ):
        res_502 = client.post(
            f"/api/ai/letters/{letter_code}/analyze",
            headers=users["seller"]["headers"],
        )
        assert res_502.status_code == 502


def test_gemini_client_uses_gemini_4_hydrogen_and_interactions_api():
    """既定モデルが gemini-4-hydrogen であり、Interactions API の応答形式を正しく解析できること"""
    from unittest.mock import MagicMock

    from app.core.config import settings
    from app.core.gemini_client import GEMINI_INTERACTIONS_URL, generate_json_with_gemini

    assert settings.gemini_model == "gemini-4-hydrogen"

    mock_http_response = MagicMock()
    mock_http_response.raise_for_status.return_value = None
    mock_http_response.json.return_value = {
        "id": "v1_test_interaction",
        "model": "gemini-4-hydrogen",
        "status": "completed",
        "steps": [
            {
                "type": "model_output",
                "content": [
                    {
                        "type": "text",
                        "text": '{"risk_level": 1, "risk_reason": "問題ありません"}',
                    }
                ],
            }
        ],
    }

    with (
        patch.object(settings, "gemini_api_key", "dummy-api-key"),
        patch("app.core.gemini_client.httpx.post", return_value=mock_http_response) as mock_post,
    ):
        result = generate_json_with_gemini(
            prompt="テストプロンプト",
            system_instruction="テスト指示",
        )

    assert result == {"risk_level": 1, "risk_reason": "問題ありません"}
    call_args = mock_post.call_args
    assert call_args.args[0] == GEMINI_INTERACTIONS_URL
    assert call_args.kwargs["json"]["model"] == "gemini-4-hydrogen"
    assert call_args.kwargs["json"]["store"] is False
    assert call_args.kwargs["json"]["response_format"]["mime_type"] == "application/json"
