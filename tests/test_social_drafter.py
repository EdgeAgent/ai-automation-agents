import pytest

from ai_automation_agents.demo_data import build_demo_provider
from ai_automation_agents.fakes import FakeChatProvider
from ai_automation_agents.recipes.social_drafter import SocialDrafterAgent


def test_demo_drafts_variants_with_hashtags() -> None:
    agent = SocialDrafterAgent(build_demo_provider())
    drafts = agent.draft("local-first AI agents", platform="x", variants=3)
    assert len(drafts) == 3
    assert "#AIagents" in drafts[0].hashtags
    assert all(draft.within_limit for draft in drafts)
    assert all(draft.platform == "x" for draft in drafts)


def test_over_limit_drafts_are_flagged_not_hidden() -> None:
    provider = FakeChatProvider(rules=[("draft social posts", "y" * 300 + "\nTAGS: #big")])
    agent = SocialDrafterAgent(provider)
    drafts = agent.draft("anything", platform="x", variants=1)
    assert len(drafts) == 1
    assert drafts[0].within_limit is False
    assert drafts[0].char_count > 280


def test_unknown_platform_raises() -> None:
    agent = SocialDrafterAgent(build_demo_provider())
    with pytest.raises(ValueError, match="Unknown platform"):
        agent.draft("anything", platform="myspace")


def test_variants_cap_is_respected() -> None:
    agent = SocialDrafterAgent(build_demo_provider())
    drafts = agent.draft("local-first AI agents", platform="linkedin", variants=2)
    assert len(drafts) == 2
