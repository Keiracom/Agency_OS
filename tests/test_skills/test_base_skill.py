"""
FILE: tests/test_skills/test_base_skill.py
TASK: ICP-018
PHASE: 11 (ICP Discovery System)
PURPOSE: Unit tests for BaseSkill and SkillRegistry
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from src.agents.skills.base_skill import (
    BaseSkill,
    SkillRegistry,
    SkillResult,
    SkillError,
)


# ============================================
# Test SkillResult
# ============================================


class TestSkillResult:
    """Tests for SkillResult class."""

    def test_skill_result_ok(self):
        """Test creating a successful result."""
        result = SkillResult.ok(
            data={"key": "value"},
            confidence=0.9,
            tokens_used=100,
            cost_aud=0.01,
        )

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.confidence == 0.9
        assert result.tokens_used == 100
        assert result.cost_aud == 0.01
        assert result.error is None

    def test_skill_result_fail(self):
        """Test creating a failed result."""
        result = SkillResult.fail(
            error="Something went wrong",
            metadata={"context": "test"},
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.metadata == {"context": "test"}
        assert result.data is None

    def test_skill_result_default_values(self):
        """Test default values for SkillResult."""
        result = SkillResult(success=True, data="test")

        assert result.confidence == 0.0
        assert result.tokens_used == 0
        assert result.cost_aud == 0.0
        assert result.metadata == {}
        assert result.executed_at is not None


# ============================================
# Test SkillError
# ============================================


class TestSkillError:
    """Tests for SkillError exception."""

    def test_skill_error_creation(self):
        """Test creating a SkillError."""
        error = SkillError(
            skill_name="test_skill",
            message="Test error message",
            details={"key": "value"},
        )

        assert error.skill_name == "test_skill"
        assert str(error) == "Test error message"
        assert error.details == {"key": "value"}

    def test_skill_error_default_details(self):
        """Test SkillError with default details."""
        error = SkillError(
            skill_name="test_skill",
            message="Error",
        )

        assert error.details == {}


# ============================================
# Test SkillRegistry
# ============================================


class TestSkillRegistry:
    """Tests for SkillRegistry class."""

    def setup_method(self):
        """Clear registry before each test."""
        SkillRegistry.clear()

    def test_register_skill(self):
        """Test registering a skill."""
        # Create a mock skill
        mock_skill = MagicMock()
        mock_skill.name = "test_skill"

        SkillRegistry.register(mock_skill)

        assert "test_skill" in SkillRegistry.names()
        assert SkillRegistry.get("test_skill") == mock_skill

    def test_get_nonexistent_skill(self):
        """Test getting a skill that doesn't exist."""
        result = SkillRegistry.get("nonexistent")
        assert result is None

    def test_get_or_raise_nonexistent(self):
        """Test get_or_raise with nonexistent skill."""
        with pytest.raises(SkillError) as exc_info:
            SkillRegistry.get_or_raise("nonexistent")

        assert "not found" in str(exc_info.value)

    def test_all_skills(self):
        """Test getting all registered skills."""
        mock_skill1 = MagicMock()
        mock_skill1.name = "skill1"
        mock_skill2 = MagicMock()
        mock_skill2.name = "skill2"

        SkillRegistry.register(mock_skill1)
        SkillRegistry.register(mock_skill2)

        all_skills = SkillRegistry.all()
        assert len(all_skills) == 2

    def test_names(self):
        """Test getting all skill names."""
        mock_skill = MagicMock()
        mock_skill.name = "test_skill"

        SkillRegistry.register(mock_skill)

        names = SkillRegistry.names()
        assert "test_skill" in names

    def test_clear(self):
        """Test clearing all skills."""
        mock_skill = MagicMock()
        mock_skill.name = "test_skill"

        SkillRegistry.register(mock_skill)
        assert len(SkillRegistry.all()) == 1

        SkillRegistry.clear()
        assert len(SkillRegistry.all()) == 0


# ============================================
# Test BaseSkill (via concrete implementation)
# ============================================


class DummyInput(BaseModel):
    """Dummy input model for testing."""
    text: str


class DummyOutput(BaseModel):
    """Dummy output model for testing."""
    result: str
    confidence: float


class DummySkill(BaseSkill[DummyInput, DummyOutput]):
    """Concrete skill implementation for testing."""

    name = "dummy_skill"
    description = "A dummy skill for testing"

    Input = DummyInput
    Output = DummyOutput

    system_prompt = "You are a test assistant."

    async def execute(self, input_data, anthropic):
        """Dummy execute implementation."""
        return SkillResult.ok(
            data=self.Output(
                result=f"Processed: {input_data.text}",
                confidence=0.95,
            ),
            confidence=0.95,
        )


class TestBaseSkill:
    """Tests for BaseSkill abstract class."""

    def test_skill_init_defaults(self):
        """Test skill initialization with defaults."""
        skill = DummySkill()

        assert skill.model == skill.default_model
        assert skill.max_tokens == skill.default_max_tokens
        assert skill.temperature == skill.default_temperature

    def test_skill_init_custom(self):
        """Test skill initialization with custom values."""
        skill = DummySkill(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            temperature=0.5,
        )

        assert skill.model == "claude-3-opus-20240229"
        assert skill.max_tokens == 2000
        assert skill.temperature == 0.5

    def test_validate_input_valid(self):
        """Test input validation with valid data."""
        skill = DummySkill()
        input_data = skill.validate_input({"text": "hello"})

        assert isinstance(input_data, DummyInput)
        assert input_data.text == "hello"

    def test_validate_input_invalid(self):
        """Test input validation with invalid data."""
        skill = DummySkill()

        with pytest.raises(SkillError) as exc_info:
            skill.validate_input({"wrong_field": "hello"})

        assert "Input validation failed" in str(exc_info.value)

    def test_parse_json_response_plain(self):
        """Test parsing plain JSON response."""
        skill = DummySkill()
        result = skill.parse_json_response('{"key": "value"}')

        assert result == {"key": "value"}

    def test_parse_json_response_markdown(self):
        """Test parsing JSON in markdown code block."""
        skill = DummySkill()
        content = '```json\n{"key": "value"}\n```'
        result = skill.parse_json_response(content)

        assert result == {"key": "value"}

    def test_parse_json_response_invalid(self):
        """Test parsing invalid JSON."""
        skill = DummySkill()

        with pytest.raises(SkillError) as exc_info:
            skill.parse_json_response("not json")

        assert "Failed to parse JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_with_dict(self):
        """Test running skill with dict input."""
        skill = DummySkill()
        mock_anthropic = MagicMock()

        result = await skill.run({"text": "test"}, mock_anthropic)

        assert result.success is True
        assert result.data.result == "Processed: test"

    @pytest.mark.asyncio
    async def test_run_with_model(self):
        """Test running skill with model input."""
        skill = DummySkill()
        mock_anthropic = MagicMock()
        input_data = DummyInput(text="test")

        result = await skill.run(input_data, mock_anthropic)

        assert result.success is True
        assert result.data.result == "Processed: test"

    @pytest.mark.asyncio
    async def test_run_with_invalid_input(self):
        """Test running skill with invalid input."""
        skill = DummySkill()
        mock_anthropic = MagicMock()

        result = await skill.run({"invalid": "data"}, mock_anthropic)

        assert result.success is False
        assert result.error is not None


"""
VERIFICATION CHECKLIST:
- [x] Tests for SkillResult (ok, fail, defaults)
- [x] Tests for SkillError (creation, defaults)
- [x] Tests for SkillRegistry (register, get, all, names, clear)
- [x] Tests for BaseSkill (init, validation, JSON parsing, run)
- [x] Async tests with pytest.mark.asyncio
- [x] Mock Anthropic client for testing
"""
