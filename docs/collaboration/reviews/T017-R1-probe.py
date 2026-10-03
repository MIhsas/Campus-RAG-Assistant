"""Offline regression probe. Run from step2_code/backend with project Python."""
from campus_assistant.comparison.service import compare_documents


def document(doc_id, texts):
    return {
        "document_id": doc_id,
        "metadata": {"policy_group_id": "same"},
        "blocks": [
            {"block_id": str(i), "kind": "paragraph", "ordinal": i, "text": text}
            for i, text in enumerate(texts)
        ],
    }


left = document("v1", ["申请材料须交所在学院审核。"])
right = document("v2", ["这是一段完全不同的新公告。", "申请材料须交所在学院审核，并签字。"])
forward = compare_documents(left, right)
backward = compare_documents(right, left)
print("forward:", forward["counts"])
print("backward:", backward["counts"])
assert forward["counts"] == {"added": 1, "deleted": 0, "modified": 1, "unchanged": 0}
assert backward["counts"] == {"added": 0, "deleted": 1, "modified": 1, "unchanged": 0}
