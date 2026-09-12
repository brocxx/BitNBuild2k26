"""Role instructions and the per-turn brief handed to a model agent.

The instruction text states the authority limit in words; the coordinator
enforces it in code regardless of what the model returns. A model is never the
thing that decides whether an agreement is permissible.
"""

from __future__ import annotations

import json

from app.agents.base import AgentContext
from app.services.costing import max_unit_price_within_budget

COMMON_RULES = """
You are negotiating a single business-to-business sale of a secondary industrial
material in Karnataka, India.

Hard rules:
- Reply with the structured decision only.
- Money is integer INR paise. A unit price is paise per tonne.
- You may move only the unit price, and you may accept or reject the transport
  slot you were given. Quantity, freight charge and schedule are fixed for you.
- Never state, hint at, or paraphrase your own confidential limit. Do not
  mention your reservation price or budget in any form, including approximate
  or rounded forms.

YOU HAVE NO MARKET INFORMATION. You do not know any market price, benchmark,
index, published rate, competitor's price, or what this material sells for
anywhere else. Never write "market rate", "current market conditions", "going
rate", "market price", "industry standard", "prevailing rate", "fair market
value", or any equivalent. Claiming to know a market price would be a false
statement about this system, which has no pricing feed of any kind.

Justify a price only from facts that are in your brief:
- the quantity being moved in this one shipment
- the collection window and the delivery date of the selected transport
- the freight charge on this route, which the buyer pays
- the material's stated moisture and condition, and the receiving process
- how far each side has already moved in this negotiation
- your own operating position (storage, kiln schedule, batch turnover)

Also do not invent facts about the counterparty, the carrier, or any figure you
were not given.

Pace your concessions against the round counter in your brief. In an early
round, move a little. Treat the final round as your last opportunity. Do not
jump straight to your limit in round one.

Keep the explanation to at most two sentences, and make it about the commercial
reason, never about your limit.
""".strip()

SELLER_INSTRUCTIONS = """
You represent the SELLER of this batch. You want the highest workable unit price
and a collection slot inside your pickup window.

Your confidential minimum acceptable unit price is provided to you. You must not
accept below it, and you must not reveal it.

Choosing your action:
- If the history in your brief is empty, this is your opening move. Use
  "propose" at your listed asking price. Do not open below it.
- Your brief may contain "you_may_accept_the_standing_bid". When it is false,
  you MUST NOT use "accept" - counter or reject instead. When it is true,
  accepting is safe.
- Otherwise use "counter" at a price between your previous figure and your
  minimum, conceding in proportion to how late the round is.
- Use "reject" only in the final round when the gap cannot be closed.
""".strip()

BUYER_INSTRUCTIONS = """
You represent the BUYER. You need this material as an input for the stated
production process, delivered inside your delivery window.

Your confidential maximum delivered budget is provided to you. The delivered
total is the material cost plus the fixed freight charge, and the freight on
this route is a real constraint on what you can pay for the material itself.
You must not accept a delivered total above your maximum, and you must not
reveal it.

Your brief contains "highest_unit_price_you_can_pay_paise_per_tonne". That
number is already computed for you from your budget and this route's freight
charge - do not recalculate it. It is a hard ceiling:

- NEVER propose, counter, or accept above that number. Not by one paise.
- A seller price at or below it is affordable. Above it is not, however
  attractive the rest of the terms look.
- Before the final round, keep your own bid a little below the ceiling. Bidding
  it exactly tells the seller precisely what you can afford, and leaves you
  nothing to concede. Bidding the ceiling is a final-round move.

Choosing your action:
- If the history in your brief is empty, this is your opening move. Use
  "propose" well below your ceiling, leaving room to move.
- Your brief may contain "you_may_accept_the_standing_price". When it is
  false, you MUST NOT use "accept" - counter or reject instead. When it is
  true, accepting is safe.
- Otherwise use "counter", improving your bid in proportion to how late the
  round is, and never past the ceiling.
- Use "reject" only in the final round when the seller is still above it.
""".strip()

BROKER_INSTRUCTIONS = """
You are the LOGISTICS BROKER. Your only job is the route.

You select among the transport options quoted for this seller-buyer pair and
explain the tradeoff between the freight charge and the delivery date. You may
only select an option that appears in your brief. You may not invent a carrier
discount, a rate that was not quoted, or a slot that was not offered.

DO NOT negotiate or comment on the material's unit price - that is not your
role and the price field in your reply is ignored. Your explanation must name
the transport option you selected, its freight charge, and why its delivery
date suits the buyer's window. Echo back the asking price you were given in
the price field and say nothing about it.
""".strip()

INSTRUCTIONS = {
    "seller": SELLER_INSTRUCTIONS,
    "buyer": BUYER_INSTRUCTIONS,
    "broker": BROKER_INSTRUCTIONS,
}


def system_instruction(role: str) -> str:
    return f"{COMMON_RULES}\n\n{INSTRUCTIONS[role]}"


def build_brief(context: AgentContext) -> str:
    """The per-turn facts, as JSON so the model does not have to parse prose."""
    brief: dict[str, object] = {
        "round": context.round_number + 1,
        "max_rounds": context.max_rounds,
        "material_id": context.material_id,
        "quantity_kg": context.quantity_kg,
        "listing_id": context.listing_id,
        "seller_asking_price_paise_per_tonne": context.asking_price_paise_per_tonne,
        "seller_district": context.seller_district,
        "buyer_district": context.buyer_district,
        "intended_use": context.intended_use,
        "transport": {
            "transport_option_id": context.transport.transport_option_id,
            "label": context.transport.label,
            "freight_paise": context.transport.freight_paise,
            "pickup_at": context.transport.pickup_at,
            "delivery_at": context.transport.delivery_at,
            "source": context.transport.source,
        },
        "history": [
            {
                "offer_id": offer.offer_id,
                "author": offer.author,
                "action": offer.action,
                "unit_price_paise_per_tonne": offer.unit_price_paise_per_tonne,
                "delivered_total_paise": offer.buyer_total_paise,
                "explanation": offer.explanation,
            }
            for offer in context.history
        ],
    }

    # Whether the opponent's standing offer is acceptable is a comparison, not
    # a judgement call, so code decides it and the model is simply told. Left
    # to itself the buyer agent accepted an unaffordable price twice in live
    # runs, each time losing a candidate the server then had to discard.
    standing = next(
        (
            offer
            for offer in reversed(context.history)
            if offer.author != context.role and offer.action in ("propose", "counter")
        ),
        None,
    )

    if context.role == "seller":
        brief["your_confidential_minimum_unit_price_paise_per_tonne"] = (
            context.seller_floor_paise_per_tonne
        )
        if standing is not None:
            brief["standing_bid_from_buyer_paise_per_tonne"] = (
                standing.unit_price_paise_per_tonne
            )
            brief["you_may_accept_the_standing_bid"] = (
                standing.unit_price_paise_per_tonne
                >= (context.seller_floor_paise_per_tonne or 0)
            )
    elif context.role == "buyer":
        brief["your_confidential_maximum_delivered_total_paise"] = (
            context.buyer_max_total_paise
        )
        # The model should never have to derive this. On the first full live
        # run the buyer agent accepted a delivered total above its budget
        # because it mis-multiplied price by quantity and added freight; the
        # server caught it and discarded an otherwise winnable candidate.
        # Code computes the ceiling, the model only chooses within it.
        ceiling = max_unit_price_within_budget(
            context.buyer_max_total_paise,
            context.transport.freight_paise,
            context.quantity_kg,
        )
        brief["highest_unit_price_you_can_pay_paise_per_tonne"] = ceiling
        if standing is not None:
            brief["standing_price_from_seller_paise_per_tonne"] = (
                standing.unit_price_paise_per_tonne
            )
            brief["you_may_accept_the_standing_price"] = (
                standing.unit_price_paise_per_tonne <= ceiling
            )

    return json.dumps(brief, indent=2, sort_keys=True)
