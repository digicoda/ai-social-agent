# Phase 6C — LinkedIn Media Publishing

Phase 6C adds the first media capability: one image attached to an approved LinkedIn draft.

Flow:

1. Draft is generated and explicitly approved.
2. Application atomically claims the draft for publishing.
3. Image bytes are uploaded to LinkedIn's image endpoint.
4. The returned LinkedIn image URN is attached to the post payload.
5. The post is created through the existing provider flow.
6. Publishing attempts and the final remote post ID are audited.

API:

`POST /publish/{draft_id}/image`

JSON body:

```json
{"provider":"linkedin","image_path":"/absolute/path/to/image.png"}
```

This phase intentionally supports one image only. Multi-image, documents, and videos remain future extensions.
