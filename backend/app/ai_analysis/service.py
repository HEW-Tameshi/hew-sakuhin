"""
AI分析機能 ビジネスロジック（サービス層）モジュール（app/ai_analysis/service.py）

【このファイルの役割】
1. 感情レターのリスク分析（analyze_letter_risk）:
   - Gemini API でレターの見出し・本文の安全性リスク（1〜3）と理由を分析し、t_ai_analysis テーブルに保存する。
2. レターAI分析履歴の取得（list_letter_analyses）:
   - 過去に t_ai_analysis に保存された分析結果を最新順で取得する。
3. 会話AIまとめ＆コミュニケーション分析（analyze_matching_conversation）:
   - マッチングに紐づくレター内容とチャットメッセージ履歴を Gemini API に送り、
     review1.html / review2.html 用の「AIまとめ」「総合評価」「包容力・共感力・論理性スコア」
     「タイプ」「肩書き」を構造化JSONで生成する。
"""

import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_analysis.models import AiAnalysis
from app.chats.models import Chat, Message
from app.core.gemini_client import generate_json_with_gemini
from app.post.models import EmotionLetter
from app.purchases.models import LetterPurchase, Matching
from app.users.models import User


def generate_ai_analysis_code() -> str:
    """t_ai_analysis.ai_analysis_code 用の10文字の一意コード（'AI' + 英大文字・数字8文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "AI" + "".join(secrets.choice(characters) for _ in range(8))


def _clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    """AIから返却された数値を指定範囲（minimum〜maximum）の整数に安全に収めるヘルパー関数。"""
    try:
        num = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, num))


def analyze_letter_risk(
    db: Session,
    letter_code: str,
) -> tuple[AiAnalysis, EmotionLetter] | None:
    """
    指定された感情レター（letter_code）を Gemini API でリスク分析し、t_ai_analysis テーブルへ保存する。

    【処理の実行順序】
    1. letter_code で t_emotion_letter を検索する（存在しなければ None）。
    2. 見出し・本文をプロンプトに組み立て、Gemini API（generate_json_with_gemini）へ送信する。
    3. 返却された risk_level（1〜3）と risk_reason を安全な範囲に正規化する。
    4. ai_analysis_code（AI + 8文字）を採番して t_ai_analysis へ登録・db.commit() で確定する。
    5. 登録した (AiAnalysis, EmotionLetter) を返す。
    """
    try:
        letter = db.scalar(
            select(EmotionLetter).where(EmotionLetter.letter_code == letter_code)
        )
        if letter is None:
            return None

        system_instruction = (
            "あなたは感情をテーマにしたCtoCプラットフォーム『こころのメェ～る便』の安全管理AIです。"
            "出品された手紙の内容を確認し、以下のJSON形式のみで回答してください：\n"
            '{"risk_level": 1〜3の整数, "risk_reason": "日本語での簡潔な分析理由"}'
        )
        prompt = (
            "次の出品レターについて、不適切な表現・誹謗中傷・個人情報の露出・深刻な医療/自傷リスクがないか分析してください。\n"
            "risk_level の基準:\n"
            "- 1: 低リスク（通常の相談・雑談・感情共有で安全）\n"
            "- 2: 中リスク（強いストレス表現や医療専門家ではない点への配慮が必要）\n"
            "- 3: 高リスク（誹謗中傷、個人情報、危険行為や緊急支援が必要な内容）\n\n"
            f"【見出し】\n{letter.title}\n\n"
            f"【内容】\n{letter.content}"
        )

        ai_result = generate_json_with_gemini(
            prompt=prompt,
            system_instruction=system_instruction,
        )

        risk_level = _clamp_int(ai_result.get("risk_level"), 1, 3, 1)
        risk_reason = str(
            ai_result.get("risk_reason") or "AIによる分析を完了しました。"
        ).strip()

        analysis_code = generate_ai_analysis_code()
        if db.scalar(
            select(AiAnalysis.ai_analysis_id).where(
                AiAnalysis.ai_analysis_code == analysis_code
            )
        ):
            analysis_code = generate_ai_analysis_code()

        analysis = AiAnalysis(
            ai_analysis_code=analysis_code,
            letter_id=letter.letter_id,
            risk_level=risk_level,
            risk_reason=risk_reason,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return analysis, letter

    except Exception:
        db.rollback()
        raise


def list_letter_analyses(
    db: Session,
    letter_code: str,
) -> tuple[list[AiAnalysis], EmotionLetter] | None:
    """指定されたレターのAI分析履歴一覧を新しい順で取得する。"""
    letter = db.scalar(
        select(EmotionLetter).where(EmotionLetter.letter_code == letter_code)
    )
    if letter is None:
        return None

    analyses = list(
        db.scalars(
            select(AiAnalysis)
            .where(AiAnalysis.letter_id == letter.letter_id)
            .order_by(AiAnalysis.ai_analysis_id.desc())
        ).all()
    )
    return analyses, letter


def analyze_matching_conversation(
    db: Session,
    matching_code: str,
    current_user: User,
) -> dict | None:
    """
    指定された取引（matching_code）のチャット会話履歴を Gemini API で分析し、
    review1.html（AIまとめ）および review2.html（コミュニケーション分析結果）用のJSONデータを返す。

    【処理の実行順序】
    1. matching_code から t_matching・t_letter_purchase・t_emotion_letter を取得する（未存在は None）。
    2. 当事者確認を行う（出品者または購入者以外は PermissionError）。
    3. 該当マッチングに紐づく t_chat と t_message を送信順に取得し、会話ログテキストを構築する。
    4. Gemini API を呼び出し、まとめ箇条書き・総合評価・3スコア（包容力/共感力/論理性）・タイプ・肩書きを取得する。
    5. 各項目を安全な型・範囲に正規化して辞書として返す。
    """
    row = db.execute(
        select(Matching, EmotionLetter)
        .join(LetterPurchase, Matching.purchase_id == LetterPurchase.purchase_id)
        .join(EmotionLetter, LetterPurchase.letter_id == EmotionLetter.letter_id)
        .where(Matching.matching_code == matching_code)
    ).first()

    if row is None:
        return None

    matching, letter = row

    if current_user.user_id not in (matching.seller_id, matching.buyer_id):
        raise PermissionError("この取引の当事者ではないためAI分析を実行できません")

    # チャットメッセージ履歴を取得（未作成やメッセージ0件でもレター内容から分析可能にする）
    chat = db.scalar(
        select(Chat).where(Chat.matching_id == matching.matching_id)
    )
    message_lines: list[str] = []
    if chat is not None:
        messages = db.scalars(
            select(Message)
            .where(Message.chat_id == chat.chat_id)
            .order_by(Message.sent_at.asc(), Message.message_id.asc())
        ).all()
        for msg in messages:
            speaker = "自分" if msg.sender_id == current_user.user_id else "相手"
            message_lines.append(f"{speaker}: {msg.message}")

    conversation_text = (
        "\n".join(message_lines)
        if message_lines
        else "（チャットメッセージはまだありません）"
    )

    system_instruction = (
        "あなたは感情CtoCプラットフォーム『こころのメェ～る便』のコミュニケーション分析AIです。"
        "会話内容をもとに、温かく前向きなフィードバックを以下のJSON形式のみで返してください：\n"
        "{\n"
        '  "summary_points": ["箇条書き1", "箇条書き2", "箇条書き3"],\n'
        '  "overall_evaluation": "とても良い",\n'
        '  "embrace_score": 0〜100の整数,\n'
        '  "empathy_score": 0〜100の整数,\n'
        '  "logic_score": 0〜100の整数,\n'
        '  "personality_type": "今日のあなたのタイプ（例：相手を安心させるタイプ）",\n'
        '  "personality_description": "タイプの説明文（1〜2文）",\n'
        '  "title_badge": "肩書き（例：共感マスター、言語化の神 など10文字以内）"\n'
        "}"
    )

    prompt = (
        f"【テーマ見出し】{letter.title}\n"
        f"【テーマ内容】{letter.content}\n\n"
        f"【チャット会話履歴】\n{conversation_text}\n\n"
        "上記のやり取りから、『自分』のコミュニケーション傾向を分析してください。"
    )

    ai_result = generate_json_with_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
    )

    raw_points = ai_result.get("summary_points")
    if isinstance(raw_points, list) and raw_points:
        summary_points = [str(p).strip() for p in raw_points if str(p).strip()][:5]
    else:
        summary_points = ["丁寧なコミュニケーションで会話を進めていました"]

    return {
        "matching_code": matching.matching_code,
        "summary_points": summary_points,
        "overall_evaluation": str(
            ai_result.get("overall_evaluation") or "良い"
        ).strip(),
        "embrace_score": _clamp_int(ai_result.get("embrace_score"), 0, 100, 80),
        "empathy_score": _clamp_int(ai_result.get("empathy_score"), 0, 100, 80),
        "logic_score": _clamp_int(ai_result.get("logic_score"), 0, 100, 75),
        "personality_type": str(
            ai_result.get("personality_type") or "相手を安心させるタイプ"
        ).strip(),
        "personality_description": str(
            ai_result.get("personality_description")
            or "相手の気持ちに寄り添いながら、丁寧に対話を進めることができます。"
        ).strip(),
        "title_badge": str(
            ai_result.get("title_badge") or "寄り添いの達人"
        ).strip(),
    }
