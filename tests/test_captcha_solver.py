import pytest
from unittest.mock import MagicMock, patch
import base64
from src.agents.captcha_solver import CaptchaSolverAgent

@pytest.fixture
def mock_ollama_llm():
    """Fixture providing a mocked Ollama LLM."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = {"content": "CAPTCHA123"}
    return mock_llm

def test_captcha_solver_initialization():
    """Test that the CaptchaSolverAgent initializes correctly."""
    mock_llm = MagicMock()
    solver = CaptchaSolverAgent(llm=mock_llm)
    assert solver.llm == mock_llm
    assert solver.name == "captcha_solver"

def test_solve_image_captcha(mock_ollama_llm):
    """Test that the agent can solve image-based CAPTCHAs."""
    # Create a simple base64 test image
    test_image_base64 = base64.b64encode(b"fake image data").decode('utf-8')
    test_image_data_uri = f"data:image/png;base64,{test_image_base64}"
    
    solver = CaptchaSolverAgent(llm=mock_ollama_llm)
    result = solver.solve_captcha(test_image_data_uri)
    
    # Assertions
    assert result == "CAPTCHA123"
    mock_ollama_llm.invoke.assert_called_once()
    
    # Check that the image was properly passed to the LLM
    call_args = mock_ollama_llm.invoke.call_args[0][0]
    assert test_image_data_uri in str(call_args)
    assert "What text do you see in this CAPTCHA image?" in str(call_args)

def test_solve_captcha_with_context(mock_ollama_llm):
    """Test that the agent can use contextual information to solve CAPTCHAs."""
    test_image_base64 = base64.b64encode(b"fake image data").decode('utf-8')
    test_image_data_uri = f"data:image/png;base64,{test_image_base64}"
    context = "This CAPTCHA asks for a simple math equation: 2+2=?"
    
    solver = CaptchaSolverAgent(llm=mock_ollama_llm)
    solver.solve_captcha(test_image_data_uri, context=context)
    
    # Check that context was passed to the LLM
    call_args = mock_ollama_llm.invoke.call_args[0][0]
    assert context in str(call_args)

def test_error_handling():
    """Test error handling when LLM fails to interpret the CAPTCHA."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("LLM error")
    
    solver = CaptchaSolverAgent(llm=mock_llm)
    
    with pytest.raises(Exception) as exc_info:
        solver.solve_captcha("data:image/png;base64,ABCD")
    
    assert "LLM error" in str(exc_info.value)

def test_handle_non_image_captcha(mock_ollama_llm):
    """Test that the agent can handle text-based CAPTCHAs."""
    text_challenge = "What is 2+2?"
    
    solver = CaptchaSolverAgent(llm=mock_ollama_llm)
    result = solver.solve_text_captcha(text_challenge)
    
    assert result == "CAPTCHA123"
    call_args = mock_ollama_llm.invoke.call_args[0][0]
    assert text_challenge in str(call_args) 