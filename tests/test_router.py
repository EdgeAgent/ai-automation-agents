from ai_automation_agents.demo import RUNNERS
from ai_automation_agents.fakes import FakeChatProvider
from ai_automation_agents.router import RECIPES, Router, keyword_route


def test_registry_has_twelve_recipes_in_build_order() -> None:
    assert len(RECIPES) == 12
    assert [recipe.number for recipe in RECIPES] == list(range(1, 13))


def test_every_registered_recipe_has_a_demo_runner() -> None:
    assert {recipe.name for recipe in RECIPES} == set(RUNNERS)


def test_keyword_routing_picks_the_cleaner_for_csv_tasks() -> None:
    decision = keyword_route("Please clean and dedupe this CSV of leads")
    assert decision.recipe == "lead-list-cleaner"
    assert decision.method == "keywords"
    assert decision.confidence > 0


def test_keyword_routing_picks_lead_responder_for_follow_ups() -> None:
    decision = keyword_route("Draft a follow-up for this new lead")
    assert decision.recipe == "lead-responder"


def test_keyword_routing_picks_code_review_for_diffs() -> None:
    decision = keyword_route("Review this diff for bugs before we merge")
    assert decision.recipe == "code-review"


def test_keyword_routing_picks_social_drafter_for_posts() -> None:
    decision = keyword_route("Write a social post for LinkedIn about our launch")
    assert decision.recipe == "social-drafter"


def test_unmatched_task_routes_nowhere() -> None:
    decision = keyword_route("blorp zanzibar quantum")
    assert decision.recipe == ""
    assert decision.confidence == 0.0


def test_provider_routing_uses_the_registry() -> None:
    provider = FakeChatProvider(rules=[("pick the single best recipe", "meeting-notes")])
    decision = Router(provider).route("Summarize yesterday's call")
    assert decision.recipe == "meeting-notes"
    assert decision.method == "provider"


def test_provider_garbage_falls_back_to_keywords() -> None:
    provider = FakeChatProvider(default="banana")
    decision = Router(provider).route("Please clean and dedupe this CSV of leads")
    assert decision.recipe == "lead-list-cleaner"
    assert decision.method == "keywords"
    assert "fallback" in decision.reason
