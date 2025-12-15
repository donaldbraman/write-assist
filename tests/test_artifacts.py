"""
Tests for artifact storage.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from write_assist.agents.models import (
    AgentMetadata,
    Citation,
    ComparativeAnalysis,
    DetailedScore,
    DetailedScores,
    Draft,
    DrafterInput,
    DraftResult,
    EditResult,
    IntegratedDraft,
    IntegrationNotes,
    JudgeResult,
    QualityAssessment,
    RankingEntry,
    Rankings,
    Recommendations,
    ResearchNotes,
    ScoreExplanation,
)
from write_assist.artifacts import (
    ALIASES,
    PROVIDERS,
    ArtifactStore,
    ProviderMapping,
    format_datetime,
    obfuscate_provider_in_text,
    reveal_provider_in_text,
    slugify,
)


class TestSlugify:
    """Tests for slugify function."""

    def test_basic_text(self) -> None:
        """Test basic text conversion."""
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self) -> None:
        """Test special character removal."""
        assert slugify("Test: with! special@chars") == "test-with-specialchars"

    def test_max_length(self) -> None:
        """Test max length enforcement."""
        result = slugify("This is a very long topic that exceeds the limit", max_length=20)
        assert len(result) <= 20
        assert not result.endswith("-")

    def test_empty_string(self) -> None:
        """Test empty string handling."""
        assert slugify("") == ""


class TestFormatDatetime:
    """Tests for datetime formatting."""

    def test_format(self) -> None:
        """Test datetime format."""
        dt = datetime(2024, 3, 15, 14, 30)
        assert format_datetime(dt) == "24-03-15-14-30"


class TestProviderMapping:
    """Tests for ProviderMapping."""

    def test_create_random(self) -> None:
        """Test random mapping creation."""
        mapping = ProviderMapping.create_random()

        # All providers should be assigned
        assigned = {mapping.aleph, mapping.bet, mapping.gimel}
        assert assigned == set(PROVIDERS)

    def test_get_alias(self) -> None:
        """Test getting alias for provider."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")

        assert mapping.get_alias("claude") == "aleph"
        assert mapping.get_alias("gemini") == "bet"
        assert mapping.get_alias("chatgpt") == "gimel"

    def test_get_provider(self) -> None:
        """Test getting provider for alias."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")

        assert mapping.get_provider("aleph") == "claude"
        assert mapping.get_provider("bet") == "gemini"
        assert mapping.get_provider("gimel") == "chatgpt"

    def test_to_dict(self) -> None:
        """Test export to dict."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        d = mapping.to_dict()

        assert d["aleph"] == "claude"
        assert d["bet"] == "gemini"
        assert d["gimel"] == "chatgpt"

    def test_from_dict(self) -> None:
        """Test restore from dict."""
        d = {"aleph": "gemini", "bet": "chatgpt", "gimel": "claude"}
        mapping = ProviderMapping.from_dict(d)

        assert mapping.aleph == "gemini"
        assert mapping.bet == "chatgpt"
        assert mapping.gimel == "claude"

    def test_bidirectional(self) -> None:
        """Test bidirectional lookup consistency."""
        mapping = ProviderMapping.create_random()

        for alias in ALIASES:
            provider = mapping.get_provider(alias)
            assert mapping.get_alias(provider) == alias


class TestObfuscation:
    """Tests for text obfuscation."""

    def test_obfuscate_lowercase(self) -> None:
        """Test lowercase provider name replacement."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        text = "The claude draft was better than gemini."
        result = obfuscate_provider_in_text(text, mapping)

        assert "claude" not in result
        assert "aleph" in result
        assert "bet" in result

    def test_obfuscate_titlecase(self) -> None:
        """Test titlecase provider name replacement."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        text = "Claude produced the best draft."
        result = obfuscate_provider_in_text(text, mapping)

        assert "Claude" not in result
        assert "Aleph" in result

    def test_reveal(self) -> None:
        """Test revealing obfuscated text."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        text = "The aleph draft was superior to bet."
        result = reveal_provider_in_text(text, mapping)

        assert "aleph" not in result
        assert "claude" in result
        assert "gemini" in result


class TestArtifactStore:
    """Tests for ArtifactStore."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    @pytest.fixture
    def sample_drafter_input(self) -> DrafterInput:
        """Create sample drafter input."""
        return DrafterInput(
            topic="Contract law consideration",
            document_type="article",
            section_outline="1. Introduction\n2. History\n3. Conclusion",
            target_length=2000,
            audience="Legal academics",
        )

    @pytest.fixture
    def sample_draft_result(self) -> DraftResult:
        """Create sample draft result."""
        return DraftResult(
            draft=Draft(
                title="Contract Law Consideration",
                content="This is the draft content...",
                word_count=500,
                citations_used=[
                    Citation(id="1", full_citation="Smith v. Jones", source="cite-assist")
                ],
            ),
            research_notes=ResearchNotes(
                sources_consulted=["Restatement"],
                key_authorities=["Smith v. Jones"],
                gaps_identified=["No recent cases"],
            ),
            metadata=AgentMetadata(model="claude-3-opus", provider="claude"),
        )

    @pytest.fixture
    def sample_edit_result(self) -> EditResult:
        """Create sample edit result."""
        return EditResult(
            integrated_draft=IntegratedDraft(
                title="Integrated Draft Title",
                content="Integrated content...",
                word_count=600,
            ),
            integration_notes=IntegrationNotes(
                elements_from_claude=["Strong argument structure"],
                elements_from_gemini=["Good citations"],
                elements_from_chatgpt=["Clear prose"],
                original_additions=["New section"],
                elements_rejected=["Weak point"],
            ),
            quality_assessment=QualityAssessment(
                argument_strength="Strong",
                citation_accuracy="Good",
                prose_quality="Excellent",
                structural_coherence="Well-organized",
                remaining_weaknesses=["Minor gaps"],
            ),
            metadata=AgentMetadata(model="claude-3-opus", provider="claude"),
        )

    @pytest.fixture
    def sample_judge_result(self) -> JudgeResult:
        """Create sample judge result."""

        def make_score(s: float, e: str) -> ScoreExplanation:
            return ScoreExplanation(score=s, explanation=e)

        def make_detailed_score() -> DetailedScore:
            return DetailedScore(
                argument_strength=make_score(8.5, "Strong"),
                citation_quality=make_score(8.0, "Good"),
                prose_clarity=make_score(9.0, "Excellent"),
                structural_coherence=make_score(8.5, "Well-organized"),
                academic_rigor=make_score(8.0, "Solid"),
                originality=make_score(7.5, "Adequate"),
            )

        return JudgeResult(
            rankings=Rankings(
                first_place=RankingEntry(
                    draft_source="claude", overall_score=8.5, summary="Best overall"
                ),
                second_place=RankingEntry(
                    draft_source="gemini", overall_score=8.0, summary="Strong contender"
                ),
                third_place=RankingEntry(
                    draft_source="chatgpt", overall_score=7.5, summary="Good effort"
                ),
            ),
            detailed_scores=DetailedScores(
                claude_edit=make_detailed_score(),
                gemini_edit=make_detailed_score(),
                chatgpt_edit=make_detailed_score(),
            ),
            comparative_analysis=ComparativeAnalysis(
                strongest_arguments="Claude had the strongest arguments",
                best_citations="Gemini had comprehensive citations",
                clearest_prose="ChatGPT was clearest",
                most_original="Claude was most original",
            ),
            recommendations=Recommendations(
                for_human_review=["Check citation accuracy"],
                potential_improvements=["Add more examples"],
                citation_concerns=["Verify case citations"],
            ),
            metadata=AgentMetadata(model="claude-3-opus", provider="claude"),
        )

    def test_initialize_creates_directories(
        self, temp_dir: Path, sample_drafter_input: DrafterInput
    ) -> None:
        """Test that initialize creates all required directories."""
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
        ).initialize()

        assert (store.run_dir / "input" / "sources").exists()
        assert (store.run_dir / "drafts").exists()
        assert (store.run_dir / "edits").exists()
        assert (store.run_dir / "judgments").exists()
        assert (store.run_dir / "final").exists()

    def test_run_id_format(self, temp_dir: Path) -> None:
        """Test run ID format includes datetime and topic slug."""
        dt = datetime(2024, 3, 15, 14, 30)
        store = ArtifactStore(
            output_dir=temp_dir,
            topic="Contract Law Basics",
            started_at=dt,
        )

        assert store.run_id == "24-03-15-14-30_contract-law-basics"

    def test_save_input(self, temp_dir: Path, sample_drafter_input: DrafterInput) -> None:
        """Test saving input artifacts."""
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
        ).initialize()

        store.save_input(sample_drafter_input)

        # Check files exist
        assert (store.run_dir / "input" / "topic.md").exists()
        assert (store.run_dir / "input" / "outline.md").exists()

        # Check content
        topic_content = (store.run_dir / "input" / "topic.md").read_text()
        assert sample_drafter_input.topic in topic_content

    def test_save_drafts_obfuscated(
        self,
        temp_dir: Path,
        sample_drafter_input: DrafterInput,
        sample_draft_result: DraftResult,
    ) -> None:
        """Test draft saving with obfuscated names."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
            mapping=mapping,
        ).initialize()

        drafts = {"claude": sample_draft_result}
        store.save_drafts(drafts)

        # Check file exists with alias name
        assert (store.run_dir / "drafts" / "aleph-draft.md").exists()

        # Check research notes
        assert (store.run_dir / "drafts" / "research-notes.json").exists()
        notes = json.loads((store.run_dir / "drafts" / "research-notes.json").read_text())
        assert "aleph" in notes

    def test_save_edits_obfuscated(
        self,
        temp_dir: Path,
        sample_drafter_input: DrafterInput,
        sample_edit_result: EditResult,
    ) -> None:
        """Test edit saving with obfuscated names."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
            mapping=mapping,
        ).initialize()

        edits = {"claude": sample_edit_result}
        store.save_edits(edits)

        # Check file exists with alias name
        assert (store.run_dir / "edits" / "aleph-edit.md").exists()

        # Check integration notes use aliases
        notes_path = store.run_dir / "edits" / "integration-notes.json"
        assert notes_path.exists()
        notes = json.loads(notes_path.read_text())
        assert "aleph" in notes
        # Should use aliases for element sources
        assert "aleph" in notes["aleph"]["elements_from"]

    def test_save_judgments_obfuscated(
        self,
        temp_dir: Path,
        sample_drafter_input: DrafterInput,
        sample_judge_result: JudgeResult,
    ) -> None:
        """Test judgment saving with obfuscated names."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
            mapping=mapping,
        ).initialize()

        judgments = {"claude": sample_judge_result}
        consensus = ["claude", "gemini", "chatgpt"]
        store.save_judgments(judgments, consensus)

        # Check judgment file exists with alias name
        assert (store.run_dir / "judgments" / "aleph-judgment.json").exists()

        # Check consensus file exists
        assert (store.run_dir / "judgments" / "consensus.md").exists()

        # Consensus should use aliases
        consensus_content = (store.run_dir / "judgments" / "consensus.md").read_text()
        assert "Aleph" in consensus_content

    def test_save_final_with_reveal(
        self,
        temp_dir: Path,
        sample_drafter_input: DrafterInput,
        sample_edit_result: EditResult,
    ) -> None:
        """Test final output saving with provider reveal."""
        mapping = ProviderMapping(aleph="claude", bet="gemini", gimel="chatgpt")
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
            mapping=mapping,
        ).initialize()

        consensus = ["claude", "gemini", "chatgpt"]
        store.save_final(sample_edit_result, consensus)

        # Check recommended draft exists
        assert (store.run_dir / "final" / "recommended.md").exists()

        # Check reveal document exists
        reveal_path = store.run_dir / "final" / "provider-reveal.md"
        assert reveal_path.exists()

        # Reveal should contain real provider names
        reveal_content = reveal_path.read_text()
        assert "Claude" in reveal_content
        assert "Gemini" in reveal_content
        assert "Chatgpt" in reveal_content

    def test_finalize_writes_manifest(
        self, temp_dir: Path, sample_drafter_input: DrafterInput
    ) -> None:
        """Test finalize writes manifest.json."""
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
        ).initialize()

        result_path = store.finalize(execution_time_ms=1234.5)

        # Check manifest exists
        manifest_path = store.run_dir / "manifest.json"
        assert manifest_path.exists()

        # Check manifest content
        manifest = json.loads(manifest_path.read_text())
        assert manifest["run_id"] == store.run_id
        assert manifest["execution_time_ms"] == 1234.5
        assert "provider_mapping" in manifest

        # Check return value
        assert result_path == store.run_dir

    def test_delete_removes_directory(
        self, temp_dir: Path, sample_drafter_input: DrafterInput
    ) -> None:
        """Test delete removes the run directory."""
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
        ).initialize()

        run_dir = store.run_dir
        assert run_dir.exists()

        store.delete()
        assert not run_dir.exists()

    def test_path_property(self, temp_dir: Path, sample_drafter_input: DrafterInput) -> None:
        """Test path property returns run directory."""
        store = ArtifactStore(
            output_dir=temp_dir,
            topic=sample_drafter_input.topic,
        )

        assert store.path == store.run_dir
