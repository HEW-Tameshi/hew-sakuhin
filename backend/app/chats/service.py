"""
チャット機能 ビジネスロジック（サービス層）モジュール（app/chats/service.py）

【このファイルの役割】
- マッチング（t_matching）に紐づくチャットルーム（t_chat）の作成・取得・一覧取得を行う。
- チャットメッセージ（t_message）の送信（DB保存）および履歴一覧取得を行う。
- 当事者（出品者・購入者）以外のアクセス拒否や、終了済み取引への送信禁止を制御する。
"""

import secrets
import string

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.chats.models import Chat, Message
from app.notifications.service import add_notification_record
from app.post.models import EmotionLetter
from app.purchases.models import LetterPurchase, Matching
from app.users.models import Profile, User


def generate_chat_code() -> str:
    """t_chat.chat_code 用の10文字の一意コード（'C' + 英大文字・数字9文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "C" + "".join(secrets.choice(characters) for _ in range(9))


def generate_message_code() -> str:
    """t_message.message_code 用の12文字の一意コード（'MSG' + 英大文字・数字9文字）を生成する。"""
    characters = string.ascii_uppercase + string.digits
    return "MSG" + "".join(secrets.choice(characters) for _ in range(9))


class ChatClosedError(ValueError):
    """完了またはキャンセルされた取引のチャットへ送信しようとした場合の例外"""
    pass


def _build_chat_room_query():
    """チャットルームと関連情報（マッチング・レター・出品者・購入者）を結合する共通クエリを返す。"""
    SellerUser = aliased(User)
    SellerProfile = aliased(Profile)
    BuyerUser = aliased(User)
    BuyerProfile = aliased(Profile)

    stmt = (
        select(
            Chat,
            Matching,
            EmotionLetter,
            SellerUser,
            SellerProfile,
            BuyerUser,
            BuyerProfile,
        )
        .join(Matching, Chat.matching_id == Matching.matching_id)
        .join(LetterPurchase, Matching.purchase_id == LetterPurchase.purchase_id)
        .join(EmotionLetter, LetterPurchase.letter_id == EmotionLetter.letter_id)
        .join(SellerUser, Matching.seller_id == SellerUser.user_id)
        .join(SellerProfile, SellerUser.user_id == SellerProfile.user_id)
        .join(BuyerUser, Matching.buyer_id == BuyerUser.user_id)
        .join(BuyerProfile, BuyerUser.user_id == BuyerProfile.user_id)
    )
    return stmt


def get_or_create_chat_room(
    db: Session,
    matching_code: str,
    current_user: User,
) -> tuple[tuple, bool] | None:
    """
    指定されたマッチング（matching_code）のチャットルームを取得する。未作成の場合は新規作成する。

    【処理の実行順序】
    1. matching_code で t_matching を検索する（未存在なら None）。
    2. ログイン中ユーザーが当事者（seller_id または buyer_id）か確認する（第三者なら PermissionError）。
    3. 既に t_chat が存在する場合はそのまま詳細情報を取得して (row, False) を返す。
    4. 未作成の場合、取引が進行中（status in [1, 2, 3]）か確認し、chat_code を採番して t_chat へ登録・確定する。
    5. 作成したチャットルーム詳細を (row, True) で返す。
    """
    try:
        matching = db.scalar(
            select(Matching).where(Matching.matching_code == matching_code)
        )
        if matching is None:
            return None

        if current_user.user_id not in (matching.seller_id, matching.buyer_id):
            raise PermissionError("この取引の当事者ではないためチャットを利用できません")

        existing_chat = db.scalar(
            select(Chat).where(Chat.matching_id == matching.matching_id)
        )

        created = False
        if existing_chat is None:
            if matching.status not in (1, 2, 3):
                raise ChatClosedError("終了またはキャンセルされた取引ではチャットを開始できません")

            chat_code = generate_chat_code()
            if db.scalar(select(Chat.chat_id).where(Chat.chat_code == chat_code)):
                chat_code = generate_chat_code()

            existing_chat = Chat(
                chat_code=chat_code,
                matching_id=matching.matching_id,
            )
            db.add(existing_chat)
            db.commit()
            db.refresh(existing_chat)
            created = True

        row = db.execute(
            _build_chat_room_query().where(Chat.chat_id == existing_chat.chat_id)
        ).first()
        if row is None:
            return None

        return tuple(row), created

    except Exception:
        db.rollback()
        raise


def list_user_chats(
    db: Session,
    current_user: User,
) -> list[tuple]:
    """ログイン中ユーザーが当事者となっているチャットルーム一覧を新しい順で取得する。"""
    stmt = (
        _build_chat_room_query()
        .where(
            or_(
                Matching.seller_id == current_user.user_id,
                Matching.buyer_id == current_user.user_id,
            )
        )
        .order_by(Chat.chat_id.desc())
    )
    return [tuple(r) for r in db.execute(stmt).all()]


def get_chat_room_by_code(
    db: Session,
    chat_code: str,
    current_user: User,
) -> tuple | None:
    """
    指定された chat_code のチャットルーム詳細を取得する。
    ※当事者（出品者または購入者）以外は PermissionError を送出する。
    """
    row = db.execute(
        _build_chat_room_query().where(Chat.chat_code == chat_code)
    ).first()

    if row is None:
        return None

    chat, matching, *_ = row
    if current_user.user_id not in (matching.seller_id, matching.buyer_id):
        raise PermissionError("このチャットルームへアクセスする権限がありません")

    return tuple(row)


def list_chat_messages(
    db: Session,
    chat_code: str,
    current_user: User,
) -> list[tuple[Message, User, Profile]] | None:
    """
    指定されたチャットルームのメッセージ履歴を送信順（古い順）で全件取得する。
    """
    room = get_chat_room_by_code(
        db=db,
        chat_code=chat_code,
        current_user=current_user,
    )
    if room is None:
        return None

    chat = room[0]

    stmt = (
        select(Message, User, Profile)
        .join(User, Message.sender_id == User.user_id)
        .join(Profile, User.user_id == Profile.user_id)
        .where(Message.chat_id == chat.chat_id)
        .order_by(Message.sent_at.asc(), Message.message_id.asc())
    )
    return [tuple(r) for r in db.execute(stmt).all()]


def send_chat_message(
    db: Session,
    chat_code: str,
    current_user: User,
    message_text: str,
) -> tuple[Message, User, Profile] | None:
    """
    指定されたチャットルームへメッセージを送信し、t_message テーブルへ登録する。

    【処理の実行順序】
    1. chat_code でチャットルームと紐づくマッチングを取得し、当事者確認を行う（未存在は None、第三者は PermissionError）。
    2. マッチングが進行中（status in [1, 2, 3]）か確認する（完了・キャンセル済みは ChatClosedError）。
    3. マッチング状態が 1 または 2 の場合は、対話開始として自動的に status = 3（対話中）へ更新する。
    4. message_code（MSG + 9文字）を採番して t_message へ追加し、db.commit() で確定する。
    5. 送信したメッセージと送信者情報を返す。
    """
    try:
        row = db.execute(
            select(Chat, Matching)
            .join(Matching, Chat.matching_id == Matching.matching_id)
            .where(Chat.chat_code == chat_code)
        ).first()

        if row is None:
            return None

        chat, matching = row

        # 当事者確認
        if current_user.user_id not in (matching.seller_id, matching.buyer_id):
            raise PermissionError("このチャットルームへメッセージを送信する権限がありません")

        # 終了済み取引への送信を禁止
        if matching.status not in (1, 2, 3):
            raise ChatClosedError("完了またはキャンセルされた取引ではメッセージを送信できません")

        # 最初のやり取りで取引ステータスを「3（対話中）」へ自動遷移
        if matching.status in (1, 2):
            matching.status = 3

        # メッセージコード採番（衝突時は1回再生成）
        message_code = generate_message_code()
        if db.scalar(
            select(Message.message_id).where(Message.message_code == message_code)
        ):
            message_code = generate_message_code()

        msg = Message(
            message_code=message_code,
            chat_id=chat.chat_id,
            sender_id=current_user.user_id,
            message=message_text,
        )
        db.add(msg)

        # 相手ユーザーへメッセージ受信通知を作成
        recipient_id = (
            matching.buyer_id
            if current_user.user_id == matching.seller_id
            else matching.seller_id
        )
        add_notification_record(
            db=db,
            user_id=recipient_id,
            notification_type=2,  # 2: チャットメッセージ受信
            title="新しいメッセージが届きました",
            message=message_text[:100],
        )

        db.commit()
        db.refresh(msg)

        profile = db.scalar(
            select(Profile).where(Profile.user_id == current_user.user_id)
        )
        if profile is None:
            raise ValueError("送信者のプロフィールが見つかりません")

        return msg, current_user, profile

    except Exception:
        db.rollback()
        raise
