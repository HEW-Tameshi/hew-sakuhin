import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.ai_analysis.models import AiAnalysis
from app.ai_analysis.rate_limit import ai_rate_limiter
from app.calls.models import Call
from app.chats.models import Chat, Message
from app.core.database import get_db
from app.core.database_test import TestSessionLocal, engine, verify_test_database
from app.notifications.models import Notification
from app.points.models import Payment, PointHistory, Subscription
from app.post.models import EmotionCategory, EmotionLetter
from app.purchases.models import LetterPurchase, Matching
from app.reviews.models import Review, Tip
from app.users.models import Base, MemberRank, Profile, RevokedToken, User
from main import app


@pytest.fixture(scope="session")
def test_engine():
    """Test DB only: verify the target before any test can use it."""
    verify_test_database()
    # テスト専用DB（kokoro_mail_test）に未作成のトランザクションテーブルのみ作成する
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Subscription.__table__,
            Payment.__table__,
            Chat.__table__,
            Message.__table__,
            Call.__table__,
            Review.__table__,
            Tip.__table__,
            AiAnalysis.__table__,
            PointHistory.__table__,
            Notification.__table__,
        ],
        checkfirst=True,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    return TestSessionLocal


@pytest.fixture(autouse=True)
def cleanup_test_data(test_session_factory):
    """Remove only rows created by the current test, even when it fails.

    The test database must not be shared with another running test process.
    """
    tracked_models = (
        (Notification, Notification.notification_id),
        (PointHistory, PointHistory.point_history_id),
        (Payment, Payment.payment_id),
        (Subscription, Subscription.subscription_id),
        (Message, Message.message_id),
        (Chat, Chat.chat_id),
        (Call, Call.call_id),
        (Review, Review.review_id),
        (Tip, Tip.tip_id),
        (AiAnalysis, AiAnalysis.ai_analysis_id),
        (Matching, Matching.matching_id),
        (LetterPurchase, LetterPurchase.purchase_id),
        (EmotionLetter, EmotionLetter.letter_id),
        (RevokedToken, RevokedToken.revoked_token_id),
        (Profile, Profile.profile_id),
        (User, User.user_id),
        (EmotionCategory, EmotionCategory.category_id),
        (MemberRank, MemberRank.rank_id),
    )

    with test_session_factory() as db:
        existing_ids = {
            model: set(db.scalars(select(primary_key)).all())
            for model, primary_key in tracked_models
        }

    try:
        ai_rate_limiter.reset()
        yield
    finally:
        ai_rate_limiter.reset()
        # Delete in foreign-key dependency order, retaining every pre-test row.
        with test_session_factory() as db:
            for model, primary_key in tracked_models:
                db.execute(
                    delete(model).where(primary_key.not_in(existing_ids[model]))
                )
            db.commit()


@pytest.fixture
def client(test_session_factory):
    def override_get_db():
        with test_session_factory() as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
