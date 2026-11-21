from ai_automation_agents.fakes import FakeEmbedder
from ai_automation_agents.recipes.doc_qa import DocQAAgent
from ai_automation_agents.retrieval import Document

DOCS = [
    Document(
        id="pricing",
        title="Pricing and first pack",
        text=(
            "The first lead pack costs $50 and includes 5 leads built to the buyer's "
            "criteria. Regular packs cost $149. A monthly pipeline costs $450 for 25 leads."
        ),
    ),
    Document(
        id="delivery",
        title="Delivery and turnaround",
        text=(
            "Lead packs are delivered by email within two business days. Every lead "
            "includes the owner's contact phone number."
        ),
    ),
]


def test_answer_comes_with_citation() -> None:
    agent = DocQAAgent(DOCS)
    answer = agent.answer("How much does the first lead pack cost?")
    assert answer.found is True
    assert answer.escalate is False
    assert answer.sources == ["pricing"]
    assert "$50" in answer.text
    assert "[pricing]" in answer.text


def test_unknown_question_escalates_instead_of_inventing() -> None:
    agent = DocQAAgent(DOCS)
    answer = agent.answer("What is the capital of France?")
    assert answer.found is False
    assert answer.escalate is True
    assert answer.sources == []


def test_high_threshold_forces_escalation() -> None:
    # Keyword scores are unbounded (weighted overlap, length-normalized);
    # a threshold above any plausible score must force escalation.
    agent = DocQAAgent(DOCS, threshold=2.0)
    answer = agent.answer("How much does the first lead pack cost?")
    assert answer.found is False
    assert answer.escalate is True


def test_empty_document_set_escalates() -> None:
    agent = DocQAAgent([])
    answer = agent.answer("Anything at all?")
    assert answer.found is False
    assert answer.escalate is True


def test_embedder_path_ranks_by_similarity() -> None:
    docs = [
        Document(id="zebra", title="Zebra notes", text="Zebra quantum bananas are striped fruit."),
        Document(id="billing", title="Billing", text="Invoice billing payments are due monthly."),
    ]
    agent = DocQAAgent(docs, embedder=FakeEmbedder())
    answer = agent.answer("zebra quantum")
    assert answer.found is True
    assert answer.sources == ["zebra"]
