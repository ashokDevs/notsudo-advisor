import pytest

from core.ingestion.chunker import Chunker

def test_chunk_javascript_functions() -> None:
    chunker = Chunker()
    content = """
    function sayHello(name) {
        console.log("Hello, " + name);
    }
    
    class Greeter {
        greet() {
            return "Hi";
        }
    }
    """
    
    chunks = chunker.chunk_file("test.js", content)
    
    assert len(chunks) == 2
    
    assert chunks[0]["symbol"] == "sayHello"
    assert "console.log" in chunks[0]["content"]
    assert chunks[0]["start_line"] == 2
    
    assert chunks[1]["symbol"] == "greet"
    assert "return" in chunks[1]["content"]

def test_ignore_unsupported_extensions() -> None:
    chunker = Chunker()
    chunks = chunker.chunk_file("test.py", "def foo(): pass")
    assert chunks == []
