# generated by datamodel-codegen:
#   filename:  create_auction.json

from __future__ import annotations

from pydantic import BaseModel


class CreateAuctionParameter(BaseModel):
    end_price: str
    end_time: str
    fa2: str
    objkt_id: str
    start_price: str
    start_time: str
