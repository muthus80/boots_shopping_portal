from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class CategoryList(BaseModel):
    items: List[CategoryRead]
    total: int