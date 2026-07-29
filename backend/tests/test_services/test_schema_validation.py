import pytest
from pydantic import ValidationError

from backend.app.schemas.strategy import PromoCodeCreate, StrategyCreate
from backend.app.schemas.subscription import SubscriptionPurchaseRequest


def _valid_strategy_kwargs(**overrides):
    kwargs = dict(
        map_id=1, title="Test Strategy", side="T_side", plant="A", speed="fast",
        difficulty_stars=3, success_rate=80,
    )
    kwargs.update(overrides)
    return kwargs


def test_strategy_create_rejects_difficulty_out_of_range():
    with pytest.raises(ValidationError):
        StrategyCreate(**_valid_strategy_kwargs(difficulty_stars=0))
    with pytest.raises(ValidationError):
        StrategyCreate(**_valid_strategy_kwargs(difficulty_stars=6))


def test_strategy_create_rejects_success_rate_out_of_range():
    with pytest.raises(ValidationError):
        StrategyCreate(**_valid_strategy_kwargs(success_rate=0))
    with pytest.raises(ValidationError):
        StrategyCreate(**_valid_strategy_kwargs(success_rate=101))


def test_strategy_create_rejects_unknown_buy_type_or_side():
    with pytest.raises(ValidationError):
        StrategyCreate(**_valid_strategy_kwargs(side="Random_side"))


def test_strategy_create_accepts_valid_payload():
    strategy = StrategyCreate(**_valid_strategy_kwargs())
    assert strategy.title == "Test Strategy"


def test_promo_code_rejects_negative_or_zero_coin_reward():
    with pytest.raises(ValidationError):
        PromoCodeCreate(coin_reward=-10, activations_limit=100)
    with pytest.raises(ValidationError):
        PromoCodeCreate(coin_reward=0, activations_limit=100)


def test_subscription_purchase_rejects_invalid_duration():
    with pytest.raises(ValidationError):
        SubscriptionPurchaseRequest(plan="premium", months=2)


def test_subscription_purchase_rejects_unknown_plan():
    with pytest.raises(ValidationError):
        SubscriptionPurchaseRequest(plan="yearly", months=1)
