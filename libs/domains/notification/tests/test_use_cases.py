from __future__ import annotations

from revold_notification.application.use_cases import NotifyLowStock, NotifyNewCheckout


async def test_notify_new_checkout_sends_message_with_cart_id(fake_channel) -> None:
    await NotifyNewCheckout(fake_channel).execute(cart_id="c1", summary_text="2x Camiseta M")
    assert len(fake_channel.sent) == 1
    notification = fake_channel.sent[0]
    assert notification.event_type == "new_checkout"
    assert "c1" in notification.message
    assert "2x Camiseta M" in notification.message


async def test_notify_low_stock_sends_message_with_sku_and_quantities(fake_channel) -> None:
    await NotifyLowStock(fake_channel).execute(sku="TSHIRT-M-BLACK", quantity_available=2, threshold=5)
    assert len(fake_channel.sent) == 1
    notification = fake_channel.sent[0]
    assert notification.event_type == "low_stock"
    assert "TSHIRT-M-BLACK" in notification.message
    assert "2" in notification.message
    assert "5" in notification.message
