import json
import os

import stripe
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse


from structure import structure

app = FastAPI()

STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
STRIPE_PRICE_ID = os.environ["STRIPE_PRICE_ID"]
RETURN_TO_URL = os.environ["RETURN_TO_URL"]


@app.get("/stripe-checkout")
def create_checkout_url() -> RedirectResponse:
    stripe.api_key = STRIPE_API_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {"price": STRIPE_PRICE_ID, "quantity": 1},
        ],
        success_url=RETURN_TO_URL,
        cancel_url=RETURN_TO_URL,
        customer_creation="always",
    )

    if session.url is not None:
        return RedirectResponse(session.url)
    else:
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@app.post("/stripe-events")
async def webhook_handler(request: Request, response: Response) -> None:
    payload = await request.body()
    body = json.loads(payload.decode("utf-8"))
    data = body["data"]
    email = data["object"]["email"]

    structure.run(email)
