from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    image_url: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class CategoryList(BaseModel):
    items: List[CategoryRead]
    total: int
