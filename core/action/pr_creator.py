from core.orchestration.state import AgentState

class PRCreator:
    """Formats pull request bodies safely, avoiding raw advisory text to prevent injection."""
    
    @staticmethod
    def format_pr(state: AgentState) -> dict[str, str]:
        package_name = state.get("package_name", "unknown")
        advisory_id = state.get("advisory_id", "unknown")
        reasoning = state.get("reachability_reasoning", "No detailed reasoning provided.")
        
        # Link to advisory instead of including its text
        advisory_url = f"https://osv.dev/vulnerability/{advisory_id}"
        
        title = f"Security: Bump `{package_name}` to fix {advisory_id}"
        
        body = (
            f"## Security Advisory: {advisory_id}\n\n"
            f"The dependency `{package_name}` is exposed to a known vulnerability.\n"
            f"[View Advisory Details on OSV]({advisory_url})\n\n"
            f"### Reachability Analysis\n"
            f"Our AI reasoning engine has determined that the vulnerable code paths are reachable from this repository:\n\n"
            f"> {reasoning}\n\n"
            f"---\n"
            f"*Generated automatically by notsudo Dependency Advisor*"
        )
        
        return {
            "title": title,
            "body": body
        }
