import re
from typing import Any, Dict, List

def prepare_output(raw: Any) -> Dict[str, Any]:
    answer = raw["result"] if isinstance(raw, dict) else getattr(raw, "result", "")
    docs = raw.get("source_documents", [])
    sources: List[str] = [getattr(d, "metadata", {}).get("source", "unknown") for d in docs]
    uml = re.findall(r"@startuml.*?@enduml", answer, flags=re.S)
    return {"text": answer, "uml": uml,"source_documents": docs,  "sources": sources}
