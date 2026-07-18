import json
from pathlib import Path
from uuid import UUID, uuid4

from core.observability.logging import get_logger
from core.storage.database import Database

logger = get_logger(__name__)

class DependencyReader:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def read_manifests(self, repo_id: UUID, commit_sha: str, dir_path: Path) -> int:
        """Reads package.json and saves dependencies."""
        package_json_path = dir_path / "package.json"
        if not package_json_path.exists():
            return 0
        
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("failed to parse package.json", error=str(e))
            return 0

        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        
        all_deps = {**deps, **dev_deps}
        
        # Read package-lock.json if it exists to get resolved versions
        lock_path = dir_path / "package-lock.json"
        resolved_versions = {}
        if lock_path.exists():
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    lock_data = json.load(f)
                    packages = lock_data.get("packages", {})
                    for key, val in packages.items():
                        if key.startswith("node_modules/"):
                            pkg_name = key.replace("node_modules/", "")
                            # simplistic fallback for workspace/monorepo lockfiles
                            if "version" in val:
                                resolved_versions[pkg_name] = val["version"]
                    
                    # For older v1 package-lock
                    deps_lock = lock_data.get("dependencies", {})
                    for pkg_name, val in deps_lock.items():
                        if "version" in val and pkg_name not in resolved_versions:
                            resolved_versions[pkg_name] = val["version"]
                            
            except Exception as e:
                logger.error("failed to parse package-lock.json", error=str(e))

        inserted_count = 0
        for pkg_name, declared_version in all_deps.items():
            resolved = resolved_versions.get(pkg_name, declared_version)
            
            await self.db.execute(
                """
                INSERT INTO repo_dependencies (id, repo_id, commit_sha, package_name, declared_version, resolved_version)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid4(),
                repo_id,
                commit_sha,
                pkg_name,
                declared_version,
                resolved
            )
            inserted_count += 1
            
        return inserted_count
