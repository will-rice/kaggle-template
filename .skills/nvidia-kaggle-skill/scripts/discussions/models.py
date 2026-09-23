# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: MIT
"""Domain models for Kaggle discussion metadata."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class CompetitionInfo(BaseModel):
    """Cached metadata about a Kaggle competition."""

    competition_id: str
    title: str = ""
    description: str = ""
    evaluation_metric: str = ""
    url: str = ""
    deadline: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DiscussionRecord(BaseModel):
    """Metadata for a single Kaggle discussion thread."""

    competition_id: str
    discussion_id: int
    title: str
    author: str
    author_username: str = ""
    author_tier: str = ""
    votes: int = 0
    comment_count: int = 0
    body_markdown: str = ""
    url: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    last_fetched_at: str | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DiscussionComment(BaseModel):
    """A single comment on a discussion thread."""

    id: int | None = None
    discussion_id: int
    competition_id: str
    author: str = ""
    author_username: str = ""
    author_tier: str = ""
    votes: int = 0
    body_markdown: str = ""
    created_at: str | None = None


class CompetitionSummary(BaseModel):
    """Aggregate statistics for a competition's discussions in the database."""

    competition_id: str
    discussion_count: int = 0
    top_authors: list[tuple[str, int]] = Field(default_factory=list)
    vote_stats: dict[str, float] = Field(default_factory=dict)
    date_range: tuple[str, str] | None = None
    competition_info: CompetitionInfo | None = None
