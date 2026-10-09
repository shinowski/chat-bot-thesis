"""Client for the image service in ../Image/thesis-backend."""

import json
import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ImageClassifierError(Exception):
    pass


class ImageClassifier:
    def __init__(self, url=None, timeout=90):
        self.url = url or os.environ.get(
            "IMAGE_CLASSIFIER_URL", "http://127.0.0.1:8000/api/predict"
        )
        self.timeout = timeout

    def predict(self, upload):
        boundary = uuid.uuid4().hex
        # Use a generated filename so user input cannot alter multipart headers.
        extension = (upload.filename or "").rsplit(".", 1)[-1].lower()
        if extension not in {"jpg", "jpeg", "png", "webp"}:
            return {"status": "rejected", "reason": "invalid_image"}
        data = upload.stream.read()
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
            f'filename="upload.{extension}"\r\n'
            'Content-Type: application/octet-stream\r\n\r\n'
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
        request = Request(
            self.url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            try:
                response = urlopen(request, timeout=self.timeout)
            except HTTPError as error:
                # The image API uses 400 for rejected images, which is a normal result.
                if error.code != 400:
                    raise ImageClassifierError("The image service returned an error.") from error
                response = error
            with response:
                result = json.load(response)
        except (URLError, TimeoutError, OSError) as error:
            raise ImageClassifierError("The image service is unavailable.") from error
        except (ValueError, UnicodeError) as error:
            raise ImageClassifierError("The image service returned an invalid response.") from error
        if not isinstance(result, dict) or result.get("status") not in {"ok", "rejected"}:
            raise ImageClassifierError("The image service returned an invalid response.")
        return result
