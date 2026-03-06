from __future__ import annotations

from pathlib import Path
from typing import Any

import google.auth
import requests
from google.auth.transport.requests import Request as GoogleAuthRequest


class NotebookLMClientError(RuntimeError):
    pass


class NotebookLMClient:
    def __init__(self, project: str, location: str, base_url: str) -> None:
        if not project:
            raise NotebookLMClientError(
                "NOTEBOOKLM_PROJECT is required for NotebookLM API calls."
            )

        self.project = project
        self.location = location
        self.base_url = base_url.rstrip("/")
        self._credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self._auth_request = GoogleAuthRequest()

    def _auth_header(self) -> dict[str, str]:
        if not self._credentials.valid:
            self._credentials.refresh(self._auth_request)
        token = self._credentials.token
        if not token:
            raise NotebookLMClientError("Failed to obtain Google Cloud access token.")
        return {"Authorization": f"Bearer {token}"}

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout_sec: int = 180,
    ) -> dict[str, Any]:
        headers = self._auth_header()
        headers["Content-Type"] = "application/json"

        response = requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=headers,
            json=payload,
            timeout=timeout_sec,
        )
        if response.status_code >= 400:
            raise NotebookLMClientError(
                f"NotebookLM API error {response.status_code}: {response.text}"
            )
        if not response.text:
            return {}
        return response.json()

    def create_notebook(self, title: str) -> dict[str, Any]:
        path = f"/v1alpha/projects/{self.project}/locations/{self.location}/notebooks"
        return self._request_json("POST", path, payload={"title": title})

    def add_text_source(
        self,
        notebook_name: str,
        source_name: str,
        text_content: str,
    ) -> dict[str, Any]:
        resource_name = notebook_name
        if resource_name.startswith("/"):
            resource_name = resource_name[1:]

        path = f"/v1alpha/{resource_name}/sources:batchCreate"
        payload = {
            "userContents": [
                {
                    "textContent": {
                        "sourceName": source_name,
                        "content": text_content,
                    }
                }
            ]
        }
        return self._request_json("POST", path, payload=payload)

    def create_podcast(
        self,
        context_text: str,
        title: str,
        focus: str,
        language_code: str,
        description: str = "",
    ) -> str:
        path = f"/v1/projects/{self.project}/locations/global/podcasts"
        payload = {
            "displayName": title[:128],
            "description": description[:1024],
            "podcastConfig": {
                "focus": focus,
                "languageCode": language_code,
                "tone": "FORMAL",
                "length": "SHORT",
                "dialogueStyle": "CONVERSATIONAL",
            },
            "contexts": [{"text": context_text}],
        }
        response = self._request_json("POST", path, payload=payload)
        operation_name = response.get("name")
        if not operation_name:
            raise NotebookLMClientError(f"Unexpected podcast response: {response}")
        return operation_name

    def wait_for_operation(
        self, operation_name: str, timeout_sec: int = 900, poll_interval_sec: int = 6
    ) -> dict[str, Any]:
        import time

        end_time = time.time() + timeout_sec
        while time.time() < end_time:
            response = self._request_json("GET", f"/v1/{operation_name}")
            if response.get("done") is True:
                if "error" in response:
                    raise NotebookLMClientError(
                        f"Operation failed: {response.get('error')}"
                    )
                return response
            time.sleep(poll_interval_sec)
        raise NotebookLMClientError(
            f"Timed out waiting for operation {operation_name} after {timeout_sec}s"
        )

    def download_operation_media(self, operation_name: str, output_path: Path) -> None:
        headers = self._auth_header()
        url = f"{self.base_url}/v1/{operation_name}:download?alt=media"
        response = requests.get(url, headers=headers, timeout=300)
        if response.status_code >= 400:
            raise NotebookLMClientError(
                f"Download failed {response.status_code}: {response.text}"
            )
        output_path.write_bytes(response.content)
