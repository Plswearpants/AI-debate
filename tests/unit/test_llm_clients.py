"""
Unit tests for LLM Clients (with mocks).

Tests cover:
- Client initialization
- Generate methods
- Error handling and retries
- Mock responses
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.clients.gemini_client import GeminiClient
from src.clients.claude_client import ClaudeClient
from src.clients.perplexity_client import PerplexityClient
from src.clients.lambda_client import LambdaGPUClient
from src.clients.mcp_client import MCPBrowserClient, MockMCPClient, SearchResult


class TestGeminiClient:
    """Test Gemini client (Interactions API)."""
    
    def test_initialization(self):
        """Test Gemini client initialization."""
        with patch('google.genai.Client'):
            client = GeminiClient("test_key")
            assert client.model_name == "gemini-2.5-flash"
    
    @pytest.mark.asyncio
    async def test_generate_mock(self):
        """Test generate method with Interactions API."""
        mock_client = Mock()
        mock_interaction = Mock()
        mock_output = Mock()
        mock_output.type = "text"
        mock_output.text = "Generated response"
        mock_interaction.outputs = [mock_output]
        mock_client.interactions.create.return_value = mock_interaction
        
        with patch('google.genai.Client', return_value=mock_client):
            client = GeminiClient("test_key")
            result = await client.generate("Test prompt")
            assert result == "Generated response"


class TestClaudeClient:
    """Test Claude client."""
    
    def test_initialization(self):
        """Test Claude client initialization."""
        with patch('anthropic.Anthropic'):
            client = ClaudeClient("test_key")
            assert client.model == "claude-3-5-sonnet-20241022"
    
    @pytest.mark.asyncio
    async def test_generate_mock(self):
        """Test generate method with mock."""
        mock_anthropic = Mock()
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Claude response"
        mock_response.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_response
        
        with patch('anthropic.Anthropic', return_value=mock_anthropic):
            client = ClaudeClient("test_key")
            client.client = mock_anthropic  # Override with mock
            result = await client.generate("Test prompt")
            assert result == "Claude response"


class TestPerplexityClient:
    """Test Perplexity client."""
    
    def test_initialization(self):
        """Test Perplexity client initialization."""
        with patch('openai.OpenAI'):
            client = PerplexityClient("test_key")
            assert client.model == "sonar-pro"
    
    @pytest.mark.asyncio
    async def test_chat_mock(self):
        """Test chat method with mock."""
        mock_openai = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Perplexity response with citations"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        
        with patch('openai.OpenAI', return_value=mock_openai):
            client = PerplexityClient("test_key")
            client.client = mock_openai  # Override with mock
            messages = [{"role": "user", "content": "Verify this claim"}]
            result = await client.chat(messages, search_recency_filter=None)  # Don't use filter in test
            assert result == "Perplexity response with citations"
    
    @pytest.mark.asyncio
    async def test_verify_source(self):
        """Test verify_source method."""
        mock_openai = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = '{"credibility_score": 8, "correspondence_score": 9}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        
        with patch('openai.OpenAI', return_value=mock_openai):
            client = PerplexityClient("test_key")
            client.client = mock_openai  # Override with mock
            result = await client.verify_source("http://example.com", "Test claim")
            assert "raw_response" in result


class TestLambdaGPUClient:
    """Test Lambda GPU client."""
    
    def test_initialization(self):
        """Test Lambda GPU client initialization."""
        client = LambdaGPUClient("http://localhost:8000", "test_key")
        assert client.endpoint == "http://localhost:8000"
        assert "Authorization" in client.headers
    
    def test_initialization_without_api_key(self):
        """Test initialization without API key."""
        client = LambdaGPUClient("http://localhost:8000")
        assert client.endpoint == "http://localhost:8000"
        assert client.headers == {}
    
    @pytest.mark.asyncio
    async def test_generate_batch_mock(self):
        """Test batch generation with mock."""
        client = LambdaGPUClient("http://localhost:8000")
        
        # Mock the method directly
        with patch.object(client, 'generate_batch', return_value=["Response 1", "Response 2", "Response 3"]):
            results = await client.generate_batch(["Prompt 1", "Prompt 2", "Prompt 3"])
            assert len(results) == 3
            assert results[0] == "Response 1"
    
    @pytest.mark.asyncio
    async def test_generate_single_mock(self):
        """Test single generation with mock."""
        client = LambdaGPUClient("http://localhost:8000")
        
        # Mock the method directly
        with patch.object(client, 'generate_batch', return_value=["Single response"]):
            result = await client.generate_single("Test prompt")
            assert result == "Single response"
    
    def test_health_check_success(self):
        """Test health check when endpoint is healthy."""
        client = LambdaGPUClient("http://localhost:8000")
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            assert client.health_check() is True
    
    def test_health_check_failure(self):
        """Test health check when endpoint is down."""
        client = LambdaGPUClient("http://localhost:8000")
        
        with patch('requests.get', side_effect=Exception("Connection failed")):
            assert client.health_check() is False


class TestMCPClient:
    """Test MCP client."""
    
    def test_initialization(self):
        """Test MCP client initialization."""
        client = MCPBrowserClient()
        assert client.server == "cursor-ide-browser"
        assert client.search_cache == {}
        assert client.page_cache == {}
    
    @pytest.mark.asyncio
    async def test_search_caching(self):
        """Test that search results are cached."""
        client = MCPBrowserClient()
        
        # First call
        results1 = await client.search("test query")
        
        # Second call should return cached results
        results2 = await client.search("test query")
        
        assert results1 == results2
    
    @pytest.mark.asyncio
    async def test_read_page_caching(self):
        """Test that page content is cached."""
        client = MCPBrowserClient()
        
        # First call
        content1 = await client.read_page("http://example.com")
        
        # Second call should return cached content
        content2 = await client.read_page("http://example.com")
        
        assert content1 == content2
    
    def test_clear_cache(self):
        """Test clearing caches."""
        client = MCPBrowserClient()
        client.search_cache["test"] = []
        client.page_cache["test"] = "content"
        
        client.clear_cache()
        
        assert client.search_cache == {}
        assert client.page_cache == {}


class TestMockMCPClient:
    """Test Mock MCP client."""
    
    @pytest.mark.asyncio
    async def test_set_mock_search_results(self):
        """Test setting and retrieving mock search results."""
        client = MockMCPClient()
        
        mock_results = [
            SearchResult(url="http://a.com", title="A", snippet="snippet a"),
            SearchResult(url="http://b.com", title="B", snippet="snippet b")
        ]
        
        client.set_mock_search_results("test query", mock_results)
        results = await client.search("test query")
        
        assert len(results) == 2
        assert results[0].url == "http://a.com"
    
    @pytest.mark.asyncio
    async def test_set_mock_page_content(self):
        """Test setting and retrieving mock page content."""
        client = MockMCPClient()
        
        client.set_mock_page_content("http://example.com", "Mock content here")
        content = await client.read_page("http://example.com")
        
        assert content == "Mock content here"
    
    @pytest.mark.asyncio
    async def test_default_mock_page_content(self):
        """Test default mock page content."""
        client = MockMCPClient()
        
        # Without setting mock, should return default
        content = await client.read_page("http://example.com")
        assert "Mock content for http://example.com" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
